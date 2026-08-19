/** 研究对话：可拖动 FAB + 贴合气泡弹层（无遮罩） */
const CHAT_FAB_POS_KEY = "uxrs_chat_fab_pos";

window.ChatUI = {
  history: [],
  pendingChanges: null,
  modalOpen: false,
  _typingId: null,
  _drag: { active: false, moved: false, ox: 0, oy: 0, startX: 0, startY: 0 },

  bind() {
    this.initFab();
    document.getElementById("chatForm")?.addEventListener("submit", (e) => {
      e.preventDefault();
      this.send();
    });
    document.getElementById("chatModalClose")?.addEventListener("click", () => {
      this.closePopover();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.modalOpen) this.closePopover();
    });
    window.addEventListener("resize", () => {
      if (this.modalOpen) this.positionPopover();
    });
    document.getElementById("chatMessages")?.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-chat-confirm]");
      if (btn) this.confirmApply();
    });
    this.bindChatInputKeys();
  },

  bindChatInputKeys() {
    const input = document.getElementById("chatInput");
    if (!input) return;
    let composing = false;
    input.addEventListener("compositionstart", () => {
      composing = true;
    });
    input.addEventListener("compositionend", () => {
      composing = false;
    });
    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || e.shiftKey) return;
      if (composing || e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      document.getElementById("chatForm")?.requestSubmit();
    });
  },

  buildFieldCatalog(moduleId) {
    const schema = window.MODULE_SCHEMAS?.[moduleId];
    const catalog = [];
    schema?.sections?.forEach((sec) => {
      sec.blocks?.forEach((b) => {
        catalog.push({
          id: b.id,
          label: b.label || b.id,
          section: sec.label || "",
          type: b.type || "text",
        });
      });
    });
    return catalog;
  },

  initFab() {
    const fab = document.getElementById("chatFab");
    if (!fab) return;
    const saved = this._loadFabPos();
    if (saved) {
      fab.style.left = `${saved.x}px`;
      fab.style.top = `${saved.y}px`;
      fab.style.right = "auto";
      fab.style.bottom = "auto";
    } else {
      fab.style.right = "24px";
      fab.style.bottom = "72px";
    }
    fab.addEventListener("pointerdown", (e) => this._onFabPointerDown(e));
    window.addEventListener("pointermove", (e) => this._onFabPointerMove(e));
    window.addEventListener("pointerup", (e) => this._onFabPointerUp(e));
  },

  _loadFabPos() {
    try {
      return JSON.parse(localStorage.getItem(CHAT_FAB_POS_KEY) || "null");
    } catch {
      return null;
    }
  },

  _saveFabPos(x, y) {
    localStorage.setItem(CHAT_FAB_POS_KEY, JSON.stringify({ x, y }));
  },

  _clampFab(fab) {
    const pad = 8;
    const w = fab.offsetWidth;
    const h = fab.offsetHeight;
    let x = parseFloat(fab.style.left) || 0;
    let y = parseFloat(fab.style.top) || 0;
    x = Math.max(pad, Math.min(window.innerWidth - w - pad, x));
    y = Math.max(pad, Math.min(window.innerHeight - h - pad, y));
    fab.style.left = `${x}px`;
    fab.style.top = `${y}px`;
    fab.style.right = "auto";
    fab.style.bottom = "auto";
    this._saveFabPos(x, y);
  },

  _onFabPointerDown(e) {
    if (e.button !== 0) return;
    const fab = document.getElementById("chatFab");
    const rect = fab.getBoundingClientRect();
    if (!fab.style.left || fab.style.right) {
      fab.style.left = `${rect.left}px`;
      fab.style.top = `${rect.top}px`;
      fab.style.right = "auto";
      fab.style.bottom = "auto";
    }
    this._drag = {
      active: true,
      moved: false,
      ox: e.clientX - rect.left,
      oy: e.clientY - rect.top,
      startX: e.clientX,
      startY: e.clientY,
    };
    fab.setPointerCapture(e.pointerId);
    fab.classList.add("is-dragging");
  },

  _onFabPointerMove(e) {
    if (!this._drag.active) return;
    const fab = document.getElementById("chatFab");
    if (Math.abs(e.clientX - this._drag.startX) > 4 || Math.abs(e.clientY - this._drag.startY) > 4) {
      this._drag.moved = true;
    }
    fab.style.left = `${e.clientX - this._drag.ox}px`;
    fab.style.top = `${e.clientY - this._drag.oy}px`;
    fab.style.right = "auto";
    fab.style.bottom = "auto";
    if (this.modalOpen) this.positionPopover();
  },

  _onFabPointerUp(e) {
    if (!this._drag.active) return;
    const fab = document.getElementById("chatFab");
    this._drag.active = false;
    fab.classList.remove("is-dragging");
    try {
      fab.releasePointerCapture(e.pointerId);
    } catch (_) {}
    this._clampFab(fab);
    if (!this._drag.moved) {
      this.togglePopover();
    }
  },

  togglePopover() {
    if (this.modalOpen) this.closePopover();
    else this.openPopover();
  },

  setFabVisible(show) {
    document.getElementById("chatFab")?.classList.toggle("hidden", !show);
    if (!show) this.closePopover();
  },

  updateModuleLabel() {
    const id = state.activeTab;
    const mod = state.modules.find((m) => m.id === id);
    const label = document.getElementById("chatFabLabel");
    const modalTitle = document.getElementById("chatModalTitle");
    const modalSub = document.getElementById("chatModalSubtitle");
    if (label) label.textContent = `模块 ${id}`;
    if (modalTitle) modalTitle.textContent = `研究对话 · ${mod?.title || "当前模块"}`;
    if (modalSub) modalSub.textContent = `模块 ${id} · 确认后写入画布`;
  },

  positionPopover() {
    const fab = document.getElementById("chatFab");
    const pop = document.getElementById("chatPopover");
    if (!fab || !pop || pop.classList.contains("hidden")) return;

    const fr = fab.getBoundingClientRect();
    pop.classList.remove("hidden");
    const pw = pop.offsetWidth;
    const ph = pop.offsetHeight;
    const gap = 14;
    const pad = 8;

    let top = fr.top - ph - gap;
    let placeBelow = false;
    if (top < 56) {
      top = fr.bottom + gap;
      placeBelow = true;
    }

    let left = fr.left + fr.width / 2 - pw / 2;
    left = Math.max(pad, Math.min(window.innerWidth - pw - pad, left));

    pop.style.left = `${left}px`;
    pop.style.top = `${top}px`;
    pop.classList.toggle("arrow-below", placeBelow);

    const arrow = pop.querySelector(".chat-popover-arrow");
    if (arrow) {
      const arrowLeft = fr.left + fr.width / 2 - left - 6;
      arrow.style.left = `${Math.max(12, Math.min(pw - 24, arrowLeft))}px`;
      arrow.style.marginLeft = "0";
    }
  },

  openPopover() {
    const path = getProjectPath();
    if (!path) {
      alert("请先选择项目");
      return;
    }
    this.updateModuleLabel();
    const pop = document.getElementById("chatPopover");
    pop?.classList.remove("hidden");
    this.modalOpen = true;
    this.render();
    this.positionPopover();
    document.getElementById("chatInput")?.focus();
  },

  closePopover() {
    document.getElementById("chatPopover")?.classList.add("hidden");
    this.modalOpen = false;
    this._removeTyping();
  },

  reset() {
    this.history = [];
    this.pendingChanges = null;
    this._removeTyping();
    this.render();
    this.updateModuleLabel();
  },

  _fieldLabel(fieldId) {
    const schema = window.MODULE_SCHEMAS[state.activeTab];
    if (!schema) return fieldId;
    for (const sec of schema.sections) {
      for (const b of sec.blocks) {
        if (b.id === fieldId) return b.label || fieldId;
      }
    }
    return fieldId;
  },

  _formatPreview(changes) {
    return Object.entries(changes || {})
      .map(([k, v]) => {
        const label = this._fieldLabel(k);
        const text = Array.isArray(v)
          ? v.filter(Boolean).join("；")
          : String(v || "").trim();
        const short = text.length > 600 ? `${text.slice(0, 600)}…` : text;
        return `<div class="preview-label">${label}</div><div>${marked.parse(short || "（空）")}</div>`;
      })
      .join("");
  },

  _removeTyping() {
    if (this._typingId) {
      this.history = this.history.filter((m) => m.id !== this._typingId);
      this._typingId = null;
    }
  },

  _setTyping(on) {
    this._removeTyping();
    if (on) {
      this._typingId = `typing-${Date.now()}`;
      this.history.push({ id: this._typingId, role: "assistant", content: "正在整理修改稿…", typing: true });
    }
    this.render();
  },

  appendMessage(role, content, extra = {}) {
    this.history.push({ id: `m-${Date.now()}`, role, content, ...extra });
    this.render();
  },

  render() {
    const box = document.getElementById("chatMessages");
    if (!box) return;

    if (!this.history.length) {
      box.innerHTML =
        '<p class="chat-hint">请用<strong>左侧画布上的板块名称</strong>说明要改哪一块（如「市场」「Q1 研究说明」「用户痛点」）。我会直接给出修改稿，点气泡内「确认修改」写入画布。<br/>Enter 发送；中文输入法选词时的回车不会发送。</p>';
      return;
    }

    box.innerHTML = this.history
      .map((m) => {
        if (m.typing) {
          return `<div class="chat-bubble assistant typing">${m.content}</div>`;
        }
        const cls = m.role === "user" ? "chat-bubble user" : "chat-bubble assistant";
        let inner = marked.parse(m.content || "");
        if (m.proposedHtml) {
          inner += `<div class="chat-proposed-preview">${m.proposedHtml}</div>`;
          inner += `<button type="button" class="btn btn-primary btn-sm chat-confirm-inline" data-chat-confirm>确认修改</button>`;
        }
        return `<div class="${cls}">${inner}</div>`;
      })
      .join("");
    box.scrollTop = box.scrollHeight;
  },

  async confirmApply() {
    if (!this.pendingChanges) return;
    const changes = { ...this.pendingChanges };
    this.pendingChanges = null;
    this.applyChanges(changes);
    const idx = this.history.findLastIndex((m) => m.proposedHtml);
    if (idx >= 0) {
      const m = this.history[idx];
      this.history[idx] = {
        ...m,
        proposedHtml: undefined,
        content: `${m.content || ""}\n\n**已确认并写入左侧画布**。满意后请点侧栏「保存」落盘。`,
      };
    }
    this.render();
    const path = getProjectPath();
    if (path) await noteActivity("chat_apply", `模块 ${state.activeTab} 对话确认`);
  },

  async send() {
    const path = getProjectPath();
    if (!path) {
      alert("请先选择项目");
      return;
    }
    const input = document.getElementById("chatInput");
    const sendBtn = document.getElementById("chatSendBtn");
    const text = (input?.value || "").trim();
    if (!text) return;

    this.pendingChanges = null;
    this.appendMessage("user", text);
    input.value = "";
    sendBtn && (sendBtn.disabled = true);
    this._setTyping(true);

    const moduleId = state.activeTab;
    const prior = {};
    for (let i = 1; i < moduleId; i++) {
      prior[i] = MarkdownBridge.fieldsToMarkdown(i, ensureFields(i));
    }

    try {
      const res = await apiFetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          module_id: moduleId,
          project_path: path,
          context: getContext(),
          current_fields: ensureFields(moduleId),
          field_catalog: this.buildFieldCatalog(moduleId),
          prior_modules: prior,
          history: this.history
            .filter((m) => !m.typing && !m.proposedHtml)
            .slice(0, -1)
            .map((m) => ({ role: m.role, content: m.content })),
          message: text,
          force_confirm: false,
        }),
      });
      this._removeTyping();
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        this.appendMessage("assistant", `出错了：${err.detail || "请重试"}`);
        return;
      }
      const data = await res.json();
      let reply = data.reply || "";
      if (data.conflicts?.length) {
        reply += `\n\n⚠ ${data.conflicts.join("；")}`;
      }
      if (data.gaps?.length) {
        reply += `\n\n💡 ${data.gaps.join("；")}`;
      }

      if (data.status === "awaiting_confirm" && data.proposed_changes) {
        this.pendingChanges = data.proposed_changes;
        this.history.push({
          id: `m-${Date.now()}`,
          role: "assistant",
          content: reply,
          proposedHtml: this._formatPreview(data.proposed_changes),
        });
      } else {
        this.appendMessage("assistant", reply || "请再具体说明要改哪一块内容。");
      }
      this.render();
    } catch (e) {
      this._removeTyping();
      if (e.message !== "未登录") {
        this.appendMessage("assistant", `请求失败：${e.message}`);
      }
    } finally {
      sendBtn && (sendBtn.disabled = false);
      this.render();
    }
  },

  applyChanges(changes) {
    const id = state.activeTab;
    const fields = ensureFields(id);
    const schema = window.MODULE_SCHEMAS[id];
    const listIds = new Set();
    schema?.sections?.forEach((sec) => {
      sec.blocks.forEach((b) => {
        if (b.type === "list") listIds.add(b.id);
      });
    });
    for (const [k, v] of Object.entries(changes || {})) {
      if (listIds.has(k)) {
        fields[k] = Array.isArray(v) ? v : MarkdownBridge.parseList(String(v));
      } else {
        fields[k] = v;
      }
    }
    snapshotCurrentProject();
    renderCanvas();
  },
};
