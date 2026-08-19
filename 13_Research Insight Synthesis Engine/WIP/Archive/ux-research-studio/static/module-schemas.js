/** 各模块画布板块定义 — 与 .cursor/skills/ux-research-planning/modules 对齐 */
window.MODULE_SCHEMAS = {
  1: {
    title: "关键研究目标",
    sections: [
      {
        id: "questions",
        label: "研究问题（Q1–Q3）",
        blocks: [
          { id: "q1_dir", label: "Q1 方向", type: "text", placeholder: "市场/业务/定位" },
          { id: "q1_title", label: "Q1 画布标题", type: "text" },
          { id: "q1_desc", label: "Q1 研究说明", type: "textarea", rows: 2 },
          { id: "q2_dir", label: "Q2 方向", type: "text", placeholder: "用户/JTBD/多角色" },
          { id: "q2_title", label: "Q2 画布标题", type: "text" },
          { id: "q2_desc", label: "Q2 研究说明", type: "textarea", rows: 2 },
          { id: "q3_dir", label: "Q3 方向", type: "text", placeholder: "接受度/体验/价值" },
          { id: "q3_title", label: "Q3 画布标题", type: "text" },
          { id: "q3_desc", label: "Q3 研究说明", type: "textarea", rows: 2 },
        ],
      },
      {
        id: "summary",
        label: "阶段总结",
        blocks: [
          { id: "why_important", label: "为什么这些问题重要", type: "textarea", rows: 3 },
          { id: "one_liner", label: "一句话阶段总结", type: "textarea", rows: 2 },
        ],
      },
    ],
  },
  2: {
    title: "桌面研究",
    sections: [
      {
        id: "desktop",
        label: "桌面研究规划",
        blocks: [
          { id: "core_question", label: "核心研究问题", type: "textarea", rows: 2 },
          { id: "directions", label: "信息方向（6–8 项，每行一条短标题）", type: "list", min: 6, max: 8 },
          { id: "insight1_title", label: "洞察一｜标题", type: "text" },
          { id: "insight1_body", label: "洞察一｜判断+原因", type: "textarea", rows: 2 },
          { id: "insight2_title", label: "洞察二｜标题", type: "text" },
          { id: "insight2_body", label: "洞察二｜判断+原因", type: "textarea", rows: 2 },
          { id: "insight3_title", label: "洞察三｜标题", type: "text" },
          { id: "insight3_body", label: "洞察三｜判断+原因", type: "textarea", rows: 2 },
        ],
      },
    ],
  },
  3: {
    title: "利益相关者",
    sections: [
      {
        id: "roles",
        label: "利益相关者类型（4–6 类）",
        blocks: [
          { id: "roles_md", label: "角色卡片（Markdown）", type: "textarea", rows: 8, hint: "### 角色名 + 为什么访谈 / 希望获得" },
        ],
      },
      {
        id: "matrix",
        label: "Influence / Interest 四象限",
        blocks: [
          { id: "quad_key", label: "KEY DECISION MAKERS", type: "textarea", rows: 2 },
          { id: "quad_agents", label: "AGENTS / SUPPORTERS", type: "textarea", rows: 2 },
          { id: "quad_potential", label: "POTENTIAL INFLUENCERS", type: "textarea", rows: 2 },
          { id: "quad_minimal", label: "MINIMAL IMPACT", type: "textarea", rows: 2 },
        ],
      },
      {
        id: "focus",
        label: "访谈重点（5 条短标题）",
        blocks: [{ id: "interview_focus", label: "访谈重点", type: "list", min: 5, max: 5 }],
      },
    ],
  },
  4: {
    title: "用户招募",
    sections: [
      {
        id: "recruit",
        label: "招募人群卡（每类人群一块）",
        blocks: [
          { id: "recruit_md", label: "招募设计全文", type: "textarea", rows: 12, hint: "## 人群 A｜… 含城市样本/条件/渠道" },
        ],
      },
    ],
  },
  5: {
    title: "访谈提纲",
    sections: [
      {
        id: "guides",
        label: "访纲（按人群）",
        blocks: [
          { id: "guides_md", label: "访纲全文", type: "textarea", rows: 12, hint: "研究目标/重点/4-5阶段框架/预期收获" },
        ],
      },
    ],
  },
  6: {
    title: "访谈素材",
    sections: [
      {
        id: "mock",
        label: "参考模拟（仅作访纲/问题设计参考，非真实访谈）",
        blocks: [
          { id: "mock_filename", label: "参考文件名", type: "text", default: "reference_01.md" },
          {
            id: "mock_md",
            label: "模拟逐字稿正文",
            type: "textarea",
            rows: 10,
            hint: "保存到 06_interviews/reference/；真实访谈请在左侧「上传访谈素材」",
          },
        ],
      },
    ],
  },
  7: {
    title: "素材与画像",
    sections: [
      {
        id: "analysis",
        label: "素材分析（左栏）",
        blocks: [
          { id: "needs", label: "用户需求", type: "list", min: 3, max: 4 },
          { id: "behaviors", label: "典型行为", type: "list", min: 3, max: 4 },
          { id: "pains", label: "核心痛点", type: "list", min: 3, max: 4 },
          { id: "highlights", label: "亮点", type: "list", min: 2, max: 3 },
          { id: "quotes", label: "关键原话", type: "list", min: 3, max: 4 },
        ],
      },
      {
        id: "persona",
        label: "用户画像（右栏）",
        blocks: [
          { id: "persona_basic", label: "基本信息（化名）", type: "textarea", rows: 2 },
          { id: "persona_behavior", label: "行为特征", type: "textarea", rows: 2 },
          { id: "persona_goals", label: "核心任务与目标", type: "textarea", rows: 2 },
          { id: "persona_habits", label: "当前做法与习惯", type: "textarea", rows: 2 },
          { id: "persona_motivation", label: "动机/痛点/期待", type: "textarea", rows: 2 },
          { id: "persona_decision", label: "决策过程", type: "textarea", rows: 2 },
          { id: "persona_scene", label: "场景关注点", type: "textarea", rows: 2 },
          { id: "persona_summary", label: "概括一句话", type: "text" },
        ],
      },
    ],
  },
  8: {
    title: "旅程与机会点",
    sections: [
      {
        id: "signals",
        label: "多源信号",
        blocks: [
          { id: "signal_market", label: "市场", type: "textarea", rows: 2 },
          { id: "signal_org", label: "组织", type: "textarea", rows: 2 },
          { id: "signal_tech", label: "技术", type: "textarea", rows: 2 },
          { id: "signal_user", label: "用户痛点", type: "textarea", rows: 2 },
        ],
      },
      {
        id: "insights",
        label: "洞察与旅程",
        blocks: [
          { id: "insights_md", label: "洞察（2–3 条）", type: "textarea", rows: 4 },
          { id: "journey_md", label: "五阶段旅程切片", type: "textarea", rows: 8 },
          { id: "opportunities_md", label: "重点机会点", type: "textarea", rows: 4 },
        ],
      },
    ],
  },
  9: {
    title: "概念发散收敛",
    sections: [
      {
        id: "diverge",
        label: "概念发散（6–8 方向）",
        blocks: [{ id: "concepts_list", label: "发散方向", type: "list", min: 6, max: 8 }],
      },
      {
        id: "converge",
        label: "收敛概念",
        blocks: [
          { id: "concept_name", label: "概念名称", type: "text" },
          { id: "concept_desc", label: "阐释", type: "textarea", rows: 3 },
          { id: "concept_innovation", label: "创新点", type: "textarea", rows: 2 },
          { id: "concept_eval", label: "评估（用户/商业/技术）", type: "textarea", rows: 3 },
          { id: "packaging", label: "包装文案 80–120 字", type: "textarea", rows: 3 },
        ],
      },
    ],
  },
};
