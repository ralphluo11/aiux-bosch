/** 结构化板块 ↔ Skill 落盘 Markdown */
window.MarkdownBridge = {
  emptyFields(moduleId) {
    const schema = window.MODULE_SCHEMAS[moduleId];
    const fields = {};
    if (!schema) return fields;
    schema.sections.forEach((sec) => {
      sec.blocks.forEach((b) => {
        if (b.type === "list") fields[b.id] = Array(b.min || 3).fill("");
        else fields[b.id] = b.default || "";
      });
    });
    return fields;
  },

  listToMd(items) {
    return (items || []).filter(Boolean).map((t, i) => `${i + 1}. ${t.trim()}`).join("\n");
  },

  parseList(text) {
    if (!text) return [];
    return text
      .split("\n")
      .map((l) => l.replace(/^(\d+\.|[-*•])\s*/, "").trim())
      .filter((l) => l && !/^（.*）$/.test(l) && l !== "（条目）");
  },

  normalizeGeneratedContent(md) {
    if (!md) return "";
    let t = String(md).trim();
    const fenced = t.match(/^```(?:markdown|md)?\s*\n([\s\S]*?)```\s*$/im);
    if (fenced) t = fenced[1].trim();
    const inline = t.match(/```(?:markdown|md)?\s*\n([\s\S]*?)```/i);
    if (inline && t.indexOf("##") > t.indexOf("```")) {
      t = inline[1].trim();
    }
    const h = t.search(/^##\s/m);
    if (h > 0 && h < 400) t = t.slice(h);
    t = t.replace(/\*\*([^*]+)\*\*:/g, "**$1**：");
    return this.normalizePlainHeadings(t);
  },

  /** DeepSeek 常输出无 ## 的纯文本标题行，先规范再解析 */
  normalizePlainHeadings(t) {
    const sectionLines = [
      "多源信号",
      "洞察",
      "关键旅程",
      "重点机会",
      "素材分析",
      "用户画像",
      "概念发散",
      "收敛概念",
      "包装",
    ];
    sectionLines.forEach((s) => {
      t = t.replace(new RegExp(`^${s}\\s*$`, "gm"), `## ${s}`);
    });
    ["市场", "组织", "技术", "用户痛点"].forEach((label) => {
      t = t.replace(new RegExp(`^${label}[：:]`, "gm"), `**${label}**：`);
    });
    return t;
  },

  /** 按单独一行的标题切分正文（兼容无 ##） */
  sliceByLineTitle(text, startTitles, endTitles = []) {
    const lines = text.split("\n");
    const norm = (s) => s.trim().replace(/^#+\s*/, "");
    const isTitle = (line, titles) =>
      titles.some((t) => norm(line) === t || norm(line).startsWith(t));

    let start = -1;
    let end = lines.length;
    for (let i = 0; i < lines.length; i++) {
      if (start < 0 && isTitle(lines[i], startTitles)) {
        start = i + 1;
        continue;
      }
      if (start >= 0 && endTitles.length && isTitle(lines[i], endTitles)) {
        end = i;
        break;
      }
    }
    if (start < 0) return "";
    return lines.slice(start, end).join("\n").trim();
  },

  extractInlineLabel(block, label, nextLabels = []) {
    if (!block) return "";
    const esc = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const stopParts = (nextLabels.length ? nextLabels : ["__END__"]).map((l) => {
      if (l === "__END__") return "$";
      const e = l.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return `(?:\\n(?:${e}|\\*\\*${e}\\*\\*)[：:])`;
    });
    const stop = stopParts.join("|") || "$";
    const labelPat = `(?:\\*\\*${esc}\\*\\*|${esc})[：:]`;
    const re = new RegExp(`(?:^|\\n)${labelPat}\\s*([\\s\\S]*?)(?=${stop})`, "i");
    const m = block.match(re);
    return m && m[1] ? m[1].trim() : "";
  },

  parseSignalsBlock(block) {
    const result = { 市场: "", 组织: "", 技术: "", 用户痛点: "" };
    if (!block) return result;
    let current = null;
    const buf = [];
    const flush = () => {
      if (current && Object.prototype.hasOwnProperty.call(result, current)) {
        result[current] = buf.join("\n").trim();
      }
      buf.length = 0;
    };
    for (const line of block.split("\n")) {
      const m = line.match(/^(?:\*\*)?(市场|组织|技术|用户痛点)(?:\*\*)?[：:]\s*(.*)$/);
      if (m) {
        flush();
        current = m[1];
        if (m[2].trim()) buf.push(m[2].trim());
      } else if (current) {
        buf.push(line);
      }
    }
    flush();
    return result;
  },

  parseModule8Fields(text, base) {
    const f = base || this.emptyFields(8);
    const signalBlock =
      this.sliceByLineTitle(text, ["多源信号"], ["洞察"]) ||
      text.split(/\n(?=洞察\s*$|\n##\s*洞察)/m)[0] ||
      "";

    const sig = this.parseSignalsBlock(signalBlock);
    f.signal_market = sig.市场;
    f.signal_org = sig.组织;
    f.signal_tech = sig.技术;
    f.signal_user = sig.用户痛点;

    f.insights_md =
      this.sliceByLineTitle(text, ["洞察"], ["关键旅程"]) ||
      this.sectionBody(text, "洞察");
    f.journey_md =
      this.sliceByLineTitle(text, ["关键旅程"], ["重点机会"]) ||
      this.sectionBody(text, ["关键旅程", "关键旅程（5 阶段）"]);
    f.opportunities_md =
      this.sliceByLineTitle(text, ["重点机会", "重点机会点"], []) ||
      this.sectionBody(text, ["重点机会", "重点机会点"]);

    if (!f.insights_md) {
      const m = text.match(/(?:^|\n)洞察\s*\n([\s\S]*?)(?=\n关键旅程|\n##\s*关键|$)/i);
      if (m) f.insights_md = m[1].trim();
    }
    if (!f.journey_md) {
      const m = text.match(/(?:^|\n)关键旅程\s*\n([\s\S]*?)(?=\n重点机会|\n##\s*重点|$)/i);
      if (m) f.journey_md = m[1].trim();
    }
    if (!f.opportunities_md) {
      const m = text.match(/(?:^|\n)重点机会[^\n]*\n([\s\S]*?)$/i);
      if (m) f.opportunities_md = m[1].trim();
    }
    return f;
  },

  pickLabeled(text, label) {
    const esc = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const patterns = [
      new RegExp(`\\*\\*${esc}\\*\\*[：:]\\s*([\\s\\S]*?)(?=\\n\\s*\\*\\*|\\n## |\\n---|$)`, "i"),
      new RegExp(`(?:^|\\n)##\\s*${esc}\\s*\\n([\\s\\S]*?)(?=\\n## |\\n---|$)`, "im"),
      new RegExp(`(?:^|\\n)###\\s*${esc}\\s*\\n([\\s\\S]*?)(?=\\n### |\\n## |$)`, "im"),
    ];
    for (const re of patterns) {
      const m = text.match(re);
      if (m && m[1].trim()) return m[1].trim();
    }
    return "";
  },

  sectionBody(text, headings) {
    const names = Array.isArray(headings) ? headings : [headings];
    for (const h of names) {
      const esc = h.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      for (const lvl of ["###", "##"]) {
        const re = new RegExp(
          `(?:^|\\n)${lvl}\\s*${esc}\\s*\\n([\\s\\S]*?)(?=\\n### |\\n## |\\n---|$)`,
          "im"
        );
        const m = text.match(re);
        if (m && m[1].trim()) return m[1].trim();
      }
    }
    return "";
  },

  countFilledFields(moduleId, fields) {
    const schema = window.MODULE_SCHEMAS[moduleId];
    if (!schema) return { filled: 0, total: 0 };
    let total = 0;
    let filled = 0;
    schema.sections.forEach((sec) => {
      sec.blocks.forEach((b) => {
        total += 1;
        const v = fields[b.id];
        if (b.type === "list") {
          if ((v || []).some((x) => String(x).trim())) filled += 1;
        } else if (String(v || "").trim()) filled += 1;
      });
    });
    return { filled, total };
  },

  fieldsToMarkdown(moduleId, f) {
    switch (moduleId) {
      case 1:
        return `## Q1｜${f.q1_dir || "研究方向"}
**${f.q1_title || ""}**
研究说明：${f.q1_desc || ""}

## Q2｜${f.q2_dir || "研究方向"}
**${f.q2_title || ""}**
研究说明：${f.q2_desc || ""}

## Q3｜${f.q3_dir || "研究方向"}
**${f.q3_title || ""}**
研究说明：${f.q3_desc || ""}

---
## 为什么这些问题重要
${f.why_important || ""}

## 一句话阶段总结
${f.one_liner || ""}
`;
      case 2:
        return `## 桌面研究核心问题
${f.core_question || ""}

## 信息方向（适合填入画布格子）
${this.listToMd(f.directions)}

## 核心洞察
**洞察一｜${f.insight1_title || ""}**
${f.insight1_body || ""}

**洞察二｜${f.insight2_title || ""}**
${f.insight2_body || ""}

**洞察三｜${f.insight3_title || ""}**
${f.insight3_body || ""}
`;
      case 3:
        return `## 利益相关者类型
${f.roles_md || ""}

---
## Stakeholder Influence / Interest 分析
| 象限 | 角色 |
|------|------|
| KEY DECISION MAKERS | ${(f.quad_key || "").replace(/\n/g, "；")} |
| AGENTS / SUPPORTERS | ${(f.quad_agents || "").replace(/\n/g, "；")} |
| POTENTIAL INFLUENCERS | ${(f.quad_potential || "").replace(/\n/g, "；")} |
| MINIMAL IMPACT | ${(f.quad_minimal || "").replace(/\n/g, "；")} |

---
## 访谈重点（画布卡片）
${this.listToMd(f.interview_focus)}
`;
      case 4:
        return f.recruit_md || "";
      case 5:
        return f.guides_md || "";
      case 6:
        return `${f.mock_md || ""}`.trim().startsWith(">") ? f.mock_md : `> **SYNTHETIC** — 模拟素材\n\n${f.mock_md || ""}`;
      case 7:
        return `## 素材分析

### 用户需求
${this.listToMd(f.needs)}

### 典型行为
${this.listToMd(f.behaviors)}

### 核心痛点
${this.listToMd(f.pains)}

### 亮点
${this.listToMd(f.highlights)}

### 关键原话
${this.listToMd(f.quotes)}

---
## 用户画像

**客户基本信息**：${f.persona_basic || ""}

**行为特征**：${f.persona_behavior || ""}

**核心任务与目标**：${f.persona_goals || ""}

**当前做法与已有习惯**：${f.persona_habits || ""}

**动机 / 痛点 / 期待**：${f.persona_motivation || ""}

**消费或体验决策过程**：${f.persona_decision || ""}

**场景关注点**：${f.persona_scene || ""}

**概括一句话**：${f.persona_summary || ""}
`;
      case 8:
        return `## 多源信号

**市场**：${f.signal_market || ""}

**组织**：${f.signal_org || ""}

**技术**：${f.signal_tech || ""}

**用户痛点**：${f.signal_user || ""}

---
## 洞察
${f.insights_md || ""}

---
## 关键旅程
${f.journey_md || ""}

---
## 重点机会
${f.opportunities_md || ""}
`;
      case 9:
        return `## 概念发散
${this.listToMd(f.concepts_list)}

---
## 收敛概念

**名称**：${f.concept_name || ""}

**阐释**：${f.concept_desc || ""}

**创新点**：${f.concept_innovation || ""}

**评估**：${f.concept_eval || ""}

---
## 包装
${f.packaging || ""}
`;
      default:
        return "";
    }
  },

  markdownToFields(moduleId, md) {
    const f = this.emptyFields(moduleId);
    if (!md) return f;
    const text = this.normalizeGeneratedContent(md);

    if (moduleId === 1) {
      const q1 = text.match(/## Q1｜([^\n]+)\n\*\*([^*]+)\*\*\n研究说明：([\s\S]*?)(?=\n## Q2|$)/);
      const q2 = text.match(/## Q2｜([^\n]+)\n\*\*([^*]+)\*\*\n研究说明：([\s\S]*?)(?=\n## Q3|$)/);
      const q3 = text.match(/## Q3｜([^\n]+)\n\*\*([^*]+)\*\*\n研究说明：([\s\S]*?)(?=\n---|$)/);
      if (q1) {
        f.q1_dir = q1[1].trim();
        f.q1_title = q1[2].trim();
        f.q1_desc = q1[3].trim();
      }
      if (q2) {
        f.q2_dir = q2[1].trim();
        f.q2_title = q2[2].trim();
        f.q2_desc = q2[3].trim();
      }
      if (q3) {
        f.q3_dir = q3[1].trim();
        f.q3_title = q3[2].trim();
        f.q3_desc = q3[3].trim();
      }
      const why = text.match(/## 为什么这些问题重要\n([\s\S]*?)(?=\n## 一句话|$)/);
      const one = text.match(/## 一句话阶段总结\n([\s\S]*?)$/);
      if (why) f.why_important = why[1].trim();
      if (one) f.one_liner = one[1].trim();
      return f;
    }

    if (moduleId === 2) {
      const core = text.match(/## 桌面研究核心问题\n([\s\S]*?)(?=\n## 信息方向|$)/);
      if (core) f.core_question = core[1].trim();
      const dirs = text.match(/## 信息方向[^\n]*\n([\s\S]*?)(?=\n## 核心洞察|$)/);
      if (dirs) f.directions = this.parseList(dirs[1]);
      const labels = ["一", "二", "三"];
      labels.forEach((cn, idx) => {
        const ins = text.match(
          new RegExp(`\\*\\*洞察${cn}｜([^*]+)\\*\\*\\n([\\s\\S]*?)(?=\\n\\*\\*洞察|$)`)
        );
        if (ins) {
          f[`insight${idx + 1}_title`] = ins[1].trim();
          f[`insight${idx + 1}_body`] = ins[2].trim();
        }
      });
      return f;
    }

    if (moduleId === 3) {
      const roles = text.match(/## 利益相关者类型\n([\s\S]*?)(?=\n---\n## Stakeholder|$)/);
      if (roles) f.roles_md = roles[1].trim();
      const table = text.match(/\| KEY DECISION MAKERS \| ([^|]+)\|/);
      if (table) f.quad_key = table[1].trim().replace(/；/g, "\n");
      const a = text.match(/\| AGENTS \/ SUPPORTERS \| ([^|]+)\|/);
      if (a) f.quad_agents = a[1].trim().replace(/；/g, "\n");
      const p = text.match(/\| POTENTIAL INFLUENCERS \| ([^|]+)\|/);
      if (p) f.quad_potential = p[1].trim().replace(/；/g, "\n");
      const m = text.match(/\| MINIMAL IMPACT \| ([^|]+)\|/);
      if (m) f.quad_minimal = m[1].trim().replace(/；/g, "\n");
      const focus = text.match(/## 访谈重点[^\n]*\n([\s\S]*?)$/);
      if (focus) f.interview_focus = this.parseList(focus[1]);
      return f;
    }

    if (moduleId === 4) {
      f.recruit_md = text;
      return f;
    }
    if (moduleId === 5) {
      f.guides_md = text;
      return f;
    }
    if (moduleId === 6) {
      f.mock_md = text;
      return f;
    }
    if (moduleId === 7) {
      const secList = (name) => {
        const body = this.sectionBody(text, name);
        const items = this.parseList(body);
        if (items.length) return items;
        return body
          .split("\n")
          .map((l) => l.replace(/^[-*•\d.]+\s*/, "").trim())
          .filter(Boolean);
      };
      f.needs = secList("用户需求");
      f.behaviors = secList("典型行为");
      f.pains = secList("核心痛点");
      f.highlights = secList("亮点");
      f.quotes = secList("关键原话");
      f.persona_basic = this.pickLabeled(text, "客户基本信息");
      f.persona_behavior = this.pickLabeled(text, "行为特征");
      f.persona_goals = this.pickLabeled(text, "核心任务与目标");
      f.persona_habits = this.pickLabeled(text, "当前做法与已有习惯") || this.pickLabeled(text, "当前做法与习惯");
      f.persona_motivation = this.pickLabeled(text, "动机 / 痛点 / 期待") || this.pickLabeled(text, "动机/痛点/期待");
      f.persona_decision = this.pickLabeled(text, "消费或体验决策过程") || this.pickLabeled(text, "决策过程");
      f.persona_scene = this.pickLabeled(text, "场景关注点");
      f.persona_summary = this.pickLabeled(text, "概括一句话");
      return f;
    }
    if (moduleId === 8) {
      return this.parseModule8Fields(text, f);
    }
    if (moduleId === 9) {
      const divBody = this.sectionBody(text, "概念发散");
      f.concepts_list = this.parseList(divBody);
      if (f.concepts_list.length < 3) {
        const alt = text.match(/##\s*概念发散\s*\n([\s\S]*?)(?=\n---|$)/i);
        if (alt) f.concepts_list = this.parseList(alt[1]);
      }
      f.concept_name = this.pickLabeled(text, "名称");
      f.concept_desc = this.pickLabeled(text, "阐释");
      f.concept_innovation = this.pickLabeled(text, "创新点");
      f.concept_eval = this.pickLabeled(text, "评估");
      f.packaging = this.sectionBody(text, "包装");
      return f;
    }

    return f;
  },
};
