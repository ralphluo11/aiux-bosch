const STORAGE_KEY = "uxrs_v4";
const AUTH_KEY = "uxrs_auth_token";
const AI_LABEL = "DeepSeek";

const MODULE_HINTS = {
  1: "3 个研究问题 + 阶段总结",
  2: "核心问题 · 6–8 信息方向 · 3 条洞察",
  3: "角色卡 · 四象限 · 5 条访谈重点",
  4: "每类人群招募卡",
  5: "每类人群访纲",
  6: "参考模拟 + 上传真实访谈",
  7: "素材分析 + 用户画像",
  8: "信号 · 洞察 · 旅程 · 机会点",
  9: "发散 6–8 · 收敛 1 概念",
};

const state = {
  modules: [],
  activeTab: 1,
  fieldsByModule: {},
  progress: { completed: [], current_module: 1 },
  currentProjectPath: "",
  generating: false,
  token: new URLSearchParams(location.search).get("token") || "",
  sessionToken: localStorage.getItem(AUTH_KEY) || "",
  auth: { required: true, logged_in: false, username: "", display_name: "" },
  appReady: false,
};

function headers() {
  const h = { "Content-Type": "application/json" };
  if (state.token) h["X-Studio-Token"] = state.token;
  if (state.sessionToken) h["X-Session-Token"] = state.sessionToken;
  return h;
}

function apiUrl(path) {
  if (state.token && !path.includes("token=")) {
    return `${path}${path.includes("?") ? "&" : "?"}token=${encodeURIComponent(state.token)}`;
  }
  return path;
}

function projectApiPath(relPath) {
  return relPath
    .split("/")
    .filter(Boolean)
    .map((seg) => encodeURIComponent(seg))
    .join("/");
}

function clearSession() {
  state.sessionToken = "";
  localStorage.removeItem(AUTH_KEY);
  state.auth = { required: true, logged_in: false, username: "", display_name: "" };
  state.appReady = false;
}

function forceLoginUI(hint) {
  clearSession();
  updateUserBar();
  showAuthOverlay(true, hint || "请先注册账户，登录后再使用");
  setAuthTab(state.auth.register_required ? "register" : "login");
}

async function apiFetch(path, options = {}) {
  const res = await fetch(apiUrl(path), {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  if (res.status === 401 && state.auth.required) {
    forceLoginUI("登录已过期，请重新登录");
    throw new Error("未登录");
  }
  return res;
}

function isLoggedIn() {
  return (
    state.auth.required &&
    state.auth.logged_in &&
    state.auth.username &&
    state.auth.username !== "anonymous"
  );
}

function getProjectPath() {
  return document.getElementById("projectPath").value.trim() || document.getElementById("projectSelect").value;
}

function getContext() {
  return {
    topic: document.getElementById("topic").value.trim(),
    audience: document.getElementById("audience").value.trim(),
    stage: document.getElementById("stage").value.trim(),
    core_question: document.getElementById("coreQuestion").value.trim(),
    notes: "",
    project_path: getProjectPath(),
  };
}

function getStore() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function resetModulesEmpty() {
  state.fieldsByModule = {};
  state.modules.forEach((m) => {
    state.fieldsByModule[m.id] = MarkdownBridge.emptyFields(m.id);
  });
}

function ensureFields(id) {
  if (!state.fieldsByModule[id]) {
    state.fieldsByModule[id] = MarkdownBridge.emptyFields(id);
  }
  return state.fieldsByModule[id];
}

function isCompleted(id) {
  return (state.progress.completed || []).includes(id);
}

function setGenerating(on, moduleId) {
  state.generating = on;
  const overlay = document.getElementById("loadingOverlay");
  const btn = document.getElementById("generateBtn");
  const canvas = document.getElementById("canvasArea");
  const saveBtn = document.getElementById("saveBtn");
  const markBtn = document.getElementById("markDoneBtn");

  overlay?.classList.toggle("hidden", !on);
  if (on && moduleId) {
    document.getElementById("loadingText").textContent =
      `DeepSeek 正在生成模块 ${moduleId}…`;
  }
  btn?.classList.toggle("is-loading", on);
  btn.disabled = on;
  saveBtn.disabled = on;
  markBtn.disabled = on;
  canvas?.classList.toggle("is-busy", on);
  document.getElementById("footerStatus").textContent = on
    ? `DeepSeek 生成中（模块 ${moduleId || state.activeTab}）…`
    : "就绪";
}

function snapshotCurrentProject() {
  const path = state.currentProjectPath;
  if (!path) return;
  const store = getStore();
  store.projects = store.projects || {};
  store.projects[path] = {
    fieldsByModule: JSON.parse(JSON.stringify(state.fieldsByModule)),
    topic: document.getElementById("topic").value,
    audience: document.getElementById("audience").value,
    stage: document.getElementById("stage").value,
    core_question: document.getElementById("coreQuestion").value,
    activeTab: state.activeTab,
  };
  store.lastProject = path;
  saveStore(store);
}

function applyProjectSnapshot(snap) {
  if (!snap) return false;
  state.fieldsByModule = JSON.parse(JSON.stringify(snap.fieldsByModule || {}));
  state.modules.forEach((m) => ensureFields(m.id));
  if (snap.topic != null) document.getElementById("topic").value = snap.topic;
  if (snap.audience != null) document.getElementById("audience").value = snap.audience;
  if (snap.stage != null) document.getElementById("stage").value = snap.stage;
  if (snap.core_question != null) document.getElementById("coreQuestion").value = snap.core_question;
  if (snap.activeTab) state.activeTab = snap.activeTab;
  return true;
}

const ACTION_LABELS = {
  save: "保存",
  generate: "AI 生成",
  mark_complete: "标记完成",
  mark_incomplete: "取消完成",
  progress_update: "更新进度",
  load_disk: "载入磁盘",
};

function showAuthError(msg) {
  const el = document.getElementById("authError");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.toggle("hidden", !msg);
}

function setAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach((b) => {
    b.classList.toggle("active", b.dataset.authTab === tab);
  });
  document.getElementById("loginForm")?.classList.toggle("hidden", tab !== "login");
  document.getElementById("registerForm")?.classList.toggle("hidden", tab !== "register");
  showAuthError("");
}

function showAuthOverlay(show, hint) {
  const overlay = document.getElementById("loginOverlay");
  const shell = document.getElementById("appShell");
  overlay?.classList.toggle("hidden", !show);
  shell?.classList.toggle("hidden", show);
  document.querySelector(".top-header")?.classList.toggle("hidden", show);
  document.querySelector(".footer-bar")?.classList.toggle("hidden", show);
  window.ChatUI?.setFabVisible(!show);
  if (show) window.ChatUI?.closePopover();
  if (hint && document.getElementById("authHint")) {
    document.getElementById("authHint").textContent = hint;
  }
}

function updateUserBar() {
  const chip = document.getElementById("userChip");
  const logout = document.getElementById("logoutBtn");
  const name = state.auth.display_name || state.auth.username;
  if (isLoggedIn() && name) {
    chip.textContent = name;
    chip.classList.remove("hidden");
    logout?.classList.remove("hidden");
  } else {
    chip?.classList.add("hidden");
    logout?.classList.add("hidden");
  }
}

async function checkAuth() {
  const res = await fetch(apiUrl("/api/auth/status"), { headers: headers() });
  if (!res.ok) {
    forceLoginUI("无法验证登录状态，请注册或登录");
    return false;
  }
  state.auth = await res.json();

  if (state.auth.auth_disabled || !state.auth.required) {
    forceLoginUI(
      state.auth.message ||
        "服务器未开启强制登录。请让管理员在 .env 设置 STUDIO_REQUIRE_AUTH=true 并重启服务。"
    );
    return false;
  }

  if (isLoggedIn()) {
    showAuthOverlay(false);
    updateUserBar();
    return true;
  }

  if (state.sessionToken) {
    clearSession();
  }
  const hint = state.auth.register_required
    ? "团队首次使用：请先注册你的账号（每人独立账号）"
    : "请使用已注册账号登录（无账号请先点「注册」）";
  showAuthOverlay(true, hint);
  setAuthTab(state.auth.register_required ? "register" : "login");
  return false;
}

async function handleLogin(e) {
  e.preventDefault();
  showAuthError("");
  const username = document.getElementById("loginUser").value.trim();
  const password = document.getElementById("loginPass").value;
  const res = await fetch(apiUrl("/api/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showAuthError(err.detail || "登录失败");
    return;
  }
  const data = await res.json();
  state.sessionToken = data.session_token;
  localStorage.setItem(AUTH_KEY, state.sessionToken);
  state.auth = {
    required: true,
    logged_in: true,
    username: data.username,
    display_name: data.display_name || data.username,
  };
  showAuthOverlay(false);
  updateUserBar();
  if (!state.appReady) await bootApp();
}

async function handleRegister(e) {
  e.preventDefault();
  showAuthError("");
  const username = document.getElementById("regUser").value.trim();
  const display_name = document.getElementById("regDisplay").value.trim();
  const password = document.getElementById("regPass").value;
  const password2 = document.getElementById("regPass2").value;
  if (password !== password2) {
    showAuthError("两次密码不一致");
    return;
  }
  const res = await fetch(apiUrl("/api/auth/register"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, display_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showAuthError(err.detail || "注册失败");
    return;
  }
  const data = await res.json();
  state.sessionToken = data.session_token;
  localStorage.setItem(AUTH_KEY, state.sessionToken);
  state.auth = {
    required: true,
    logged_in: true,
    username: data.username,
    display_name: data.display_name || data.username,
  };
  showAuthOverlay(false);
  updateUserBar();
  if (!state.appReady) await bootApp();
}

function logout() {
  clearSession();
  updateUserBar();
  showAuthOverlay(true, "请登录后继续");
  setAuthTab("login");
}

async function fetchActivity() {
  const path = getProjectPath();
  const list = document.getElementById("activityList");
  const hint = document.getElementById("activityLogPath");
  if (!list) return;
  if (!path) {
    list.innerHTML = "<li>请选择项目</li>";
    if (hint) hint.textContent = "";
    return;
  }
  const res = await apiFetch(`/api/projects/${encodeURIComponent(path)}/activity`);
  if (!res.ok) {
    list.innerHTML = "<li>无法加载记录</li>";
    return;
  }
  const data = await res.json();
  const entries = data.entries || [];
  if (!entries.length) {
    list.innerHTML = "<li>暂无修改记录</li>";
  } else {
    list.innerHTML = entries
      .map((e) => {
        const act = ACTION_LABELS[e.action] || e.action;
        const mod = e.module_id ? ` · 模块${e.module_id}` : "";
        return `<li><strong>${e.user}</strong> ${e.time}<br>${act}${mod}${e.detail ? " — " + e.detail : ""}</li>`;
      })
      .join("");
  }
  if (hint && data.log_markdown) {
    hint.textContent = `完整日志：${path}/${data.log_markdown}`;
  }
}

async function noteActivity(action, detail, moduleId) {
  const path = getProjectPath();
  if (!path) return;
  await apiFetch(`/api/projects/${encodeURIComponent(path)}/activity`, {
    method: "POST",
    body: JSON.stringify({ action, detail, module_id: moduleId || null }),
  });
  await fetchActivity();
}

async function onProjectChange(newPath) {
  if (state.generating) return;

  if (state.currentProjectPath && state.currentProjectPath !== newPath) {
    snapshotCurrentProject();
  }

  state.currentProjectPath = newPath;

  if (!newPath) {
    state.progress = { completed: [], current_module: 1 };
    resetModulesEmpty();
    state.activeTab = 1;
    renderTabs();
    renderCanvas();
    renderProgressUI();
    document.getElementById("footerStatus").textContent = "未选择项目";
    await fetchActivity();
    return;
  }

  const store = getStore();
  const cached = store.projects?.[newPath];
  if (cached) {
    applyProjectSnapshot(cached);
  } else {
    resetModulesEmpty();
    await loadFromDisk();
  }

  await fetchProgress();
  if (state.progress.current_module) {
    state.activeTab = state.progress.current_module;
  }
  renderTabs();
  renderCanvas();
  renderProgressUI();
  document.getElementById("footerStatus").textContent = `已切换：${newPath}`;
  await fetchActivity();
  if (window.InterviewsUI) await InterviewsUI.refresh();
}

function renderProgressUI() {
  const done = state.progress.completed || [];
  const pct = Math.round((done.length / 9) * 100);
  document.getElementById("progressPct").textContent = `${pct}%`;
  document.getElementById("progressFill").style.width = `${pct}%`;
  const cur = state.progress.current_module || state.activeTab;
  const name = state.modules.find((m) => m.id === cur)?.title || `模块 ${cur}`;
  document.getElementById("progressHint").textContent = getProjectPath()
    ? `当前进行到：模块 ${cur} ${name} · 已完成 ${done.length}/9`
    : "请选择项目";

  const rail = document.getElementById("railSteps");
  rail.innerHTML = "";
  state.modules.forEach((m) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "rail-step-btn";
    if (isCompleted(m.id)) btn.classList.add("done");
    if (m.id === state.activeTab) btn.classList.add("active");
    btn.innerHTML = `<span class="num">${m.id}</span><span class="name">${m.title}</span>${isCompleted(m.id) ? '<span class="check">✓</span>' : ""}`;
    btn.addEventListener("click", () => switchTab(m.id));
    li.appendChild(btn);
    rail.appendChild(li);
  });

  document.getElementById("tabNav")?.querySelectorAll(".tab-btn").forEach((btn) => {
    const id = Number(btn.dataset.tab);
    btn.classList.toggle("active", id === state.activeTab);
    btn.classList.toggle("done", isCompleted(id));
  });

  document.getElementById("markDoneBtn").textContent = isCompleted(state.activeTab)
    ? "取消已完成"
    : "标记已完成";
}

function renderTabs() {
  const nav = document.getElementById("tabNav");
  nav.innerHTML = "";
  state.modules.forEach((m) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tab-btn";
    btn.dataset.tab = String(m.id);
    btn.setAttribute("role", "tab");
    btn.textContent = `${m.id}. ${m.title}`;
    if (m.id === state.activeTab) btn.classList.add("active");
    if (isCompleted(m.id)) btn.classList.add("done");
    btn.addEventListener("click", () => switchTab(m.id));
    nav.appendChild(btn);
  });
}

function renderBlockField(block, value, onChange, disabled) {
  const wrap = document.createElement("div");
  wrap.className = "block-field";
  const label = document.createElement("label");
  label.textContent = block.label;
  wrap.appendChild(label);
  if (block.hint) {
    const hint = document.createElement("span");
    hint.className = "block-hint";
    hint.textContent = block.hint;
    wrap.appendChild(hint);
  }

  let input;
  if (block.type === "textarea") {
    input = document.createElement("textarea");
    input.rows = block.rows || 3;
  } else if (block.type === "list") {
    input = document.createElement("textarea");
    input.rows = block.max || 6;
    input.placeholder = "每行一条";
    const arr = Array.isArray(value) ? value : [];
    input.value = arr.join("\n");
    input.disabled = disabled;
    input.addEventListener("input", () => {
      onChange(block.id, MarkdownBridge.parseList(input.value));
    });
    wrap.appendChild(input);
    return wrap;
  } else {
    input = document.createElement("input");
    input.type = "text";
  }
  input.dataset.field = block.id;
  input.value = value ?? "";
  input.disabled = disabled;
  input.addEventListener("input", () => onChange(block.id, input.value));
  wrap.appendChild(input);
  return wrap;
}

function renderCanvas() {
  const id = state.activeTab;
  const schema = window.MODULE_SCHEMAS[id];
  const fields = ensureFields(id);
  const area = document.getElementById("canvasArea");
  area.innerHTML = "";
  const busy = state.generating;

  document.getElementById("activeTabTitle").textContent = `模块 ${id} · ${schema?.title || ""}`;
  document.getElementById("activeTabDesc").textContent = MODULE_HINTS[id] || "";

  const onChange = (key, val) => {
    if (state.generating) return;
    fields[key] = val;
    snapshotCurrentProject();
  };

  (schema?.sections || []).forEach((sec) => {
    const section = document.createElement("div");
    section.className = "canvas-section";
    const head = document.createElement("h3");
    head.className = "section-label";
    head.textContent = sec.label;
    section.appendChild(head);

    const grid = document.createElement("div");
    grid.className = sec.blocks.length > 4 ? "blocks-grid" : "blocks-stack";

    sec.blocks.forEach((block) => {
      const card = document.createElement("div");
      card.className = "block-card";
      card.appendChild(renderBlockField(block, fields[block.id], onChange, busy));
      grid.appendChild(card);
    });
    section.appendChild(grid);
    area.appendChild(section);
  });

  area.classList.toggle("is-busy", busy);
  renderProgressUI();
}

function switchTab(id) {
  if (state.generating) return;
  state.activeTab = id;
  state.progress.current_module = id;
  renderTabs();
  renderCanvas();
  renderProgressUI();
  snapshotCurrentProject();
  if (window.ChatUI) {
    window.ChatUI.reset();
    window.ChatUI.updateModuleLabel();
  }
  if (getProjectPath()) persistProgress({ current_module: id });
}

async function exportPpt() {
  const path = getProjectPath();
  if (!path) {
    alert("请先选择项目");
    return;
  }
  const overlay = document.getElementById("loadingOverlay");
  overlay?.classList.remove("hidden");
  document.getElementById("loadingText").textContent = "正在生成 PPT…";
  try {
    const res = await apiFetch(`/api/projects/${projectApiPath(path)}/export-ppt`, {
      method: "POST",
      body: JSON.stringify(getContext()),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "导出失败");
      return;
    }
    const dl = apiUrl(data.download_url);
    window.open(dl, "_blank");
    document.getElementById("footerStatus").textContent = `PPT 已生成：${data.filename}`;
  } catch (e) {
    if (e.message !== "未登录") alert(e.message);
  } finally {
    overlay?.classList.add("hidden");
  }
}

async function fetchProgress() {
  const path = getProjectPath();
  if (!path) {
    state.progress = { completed: [], current_module: 1 };
    return;
  }
  const res = await apiFetch(`/api/projects/${encodeURIComponent(path)}/progress`);
  if (res.ok) state.progress = await res.json();
}

async function persistProgress(extra = {}) {
  const path = getProjectPath();
  if (!path) return;
  await apiFetch(`/api/projects/${encodeURIComponent(path)}/progress`, {
    method: "POST",
    body: JSON.stringify({
      completed: state.progress.completed || [],
      current_module: state.progress.current_module || state.activeTab,
      ...extra,
    }),
  });
  await fetchProgress();
  renderProgressUI();
  renderTabs();
  await fetchActivity();
}

async function toggleMarkDone() {
  if (state.generating) return;
  const id = state.activeTab;
  const completed = new Set(state.progress.completed || []);
  if (completed.has(id)) {
    await persistProgress({ mark_incomplete: id });
    completed.delete(id);
  } else {
    const md = MarkdownBridge.fieldsToMarkdown(id, ensureFields(id));
    if (!md.trim()) {
      alert("请先填写或生成内容，再标记完成");
      return;
    }
    await saveModule(false);
    await persistProgress({ mark_complete: id });
    completed.add(id);
  }
  state.progress.completed = [...completed].sort((a, b) => a - b);
  renderProgressUI();
  renderTabs();
}

async function getPrior() {
  const prior = {};
  const path = getProjectPath();
  for (let i = 1; i < state.activeTab; i++) {
    if (i === 6 && state.activeTab >= 7 && path) {
      try {
        const res = await apiFetch(
          `/api/projects/${encodeURIComponent(path)}/interviews/combined`
        );
        if (res.ok) {
          const data = await res.json();
          if (data.content?.trim()) {
            prior[6] = data.content;
            continue;
          }
        }
      } catch (_) {}
    }
    prior[i] = MarkdownBridge.fieldsToMarkdown(i, ensureFields(i));
  }
  return prior;
}

async function generateModule() {
  if (state.generating) return;
  const path = getProjectPath();
  if (!path) {
    alert("请先选择项目");
    return;
  }

  const moduleId = state.activeTab;
  setGenerating(true, moduleId);

  try {
    const res = await apiFetch("/api/generate", {
      method: "POST",
      body: JSON.stringify({
        module_id: moduleId,
        context: getContext(),
        prior_modules: await getPrior(),
        stream: false,
        provider: "openai",
      }),
    });
    if (!res.ok) {
      const err = await res.text();
      alert(`生成失败：${err}`);
      return;
    }
    const data = await res.json();
    const raw = MarkdownBridge.normalizeGeneratedContent(data.content || "");
    const fields = MarkdownBridge.markdownToFields(moduleId, raw);
    state.fieldsByModule[moduleId] = fields;
    snapshotCurrentProject();
    renderCanvas();
    const stat = MarkdownBridge.countFilledFields(moduleId, fields);
    let msg = `模块 ${moduleId} 已由 DeepSeek 填充（${stat.filled}/${stat.total} 格）`;
    if (stat.filled < stat.total * 0.6) {
      msg += " — 部分格子未能自动解析，可再点一次生成或手动补全";
    }
    if (moduleId === 8) {
      const emptySig = ["signal_org", "signal_tech", "signal_user"].filter(
        (k) => !String(fields[k] || "").trim()
      );
      if (emptySig.length) {
        msg += "；组织/技术/用户痛点未写出时请再生成一次（已加强模板要求四项必填）";
      }
      if (!String(fields.journey_md || "").includes("阶段五")) {
        msg += "；旅程建议写满阶段一～五";
      }
    }
    document.getElementById("footerStatus").textContent = msg;
    await fetchActivity();
  } catch (e) {
    alert(`生成失败：${e.message}`);
    document.getElementById("footerStatus").textContent = "生成失败";
  } finally {
    setGenerating(false);
  }
}

async function saveModule() {
  if (state.generating) return;
  const path = getProjectPath();
  if (!path) {
    alert("请先选择项目");
    return;
  }
  const id = state.activeTab;
  const content = MarkdownBridge.fieldsToMarkdown(id, ensureFields(id));
  const body = { module_id: id, project_path: path, content };
  const f = ensureFields(id);
  if (id === 6 && f.mock_filename) body.extra_filename = f.mock_filename;

  const res = await apiFetch("/api/save", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    alert("保存失败");
    return;
  }
  snapshotCurrentProject();
  document.getElementById("footerStatus").textContent = `已保存模块 ${id}`;
  await fetchActivity();
}

async function loadFromDisk() {
  const path = getProjectPath();
  if (!path) return;

  resetModulesEmpty();

  const ctxRes = await apiFetch(`/api/projects/${encodeURIComponent(path)}/context`);
  if (!ctxRes.ok) return;
  const files = (await ctxRes.json()).research_files || [];

  for (const m of state.modules) {
    try {
      if (m.output_is_dir) {
        const match =
          files.find((f) => f.name.startsWith("06_interviews/reference/")) ||
          files.find((f) => f.name.startsWith("06_mock-transcripts/"));
        if (!match) continue;
        const fr = await apiFetch(
          `/api/projects/${encodeURIComponent(path)}/files/${encodeURIComponent(match.name)}`
        );
        const fd = await fr.json();
        if (fr.ok && fd.content) {
          const fields = MarkdownBridge.markdownToFields(6, fd.content);
          fields.mock_filename = match.name.split("/").pop();
          state.fieldsByModule[6] = fields;
        }
        continue;
      }

      const match = files.find((f) => f.name === m.output_file);
      if (!match) continue;
      const fr = await fetch(
        apiUrl(`/api/projects/${encodeURIComponent(path)}/files/${encodeURIComponent(match.name)}`),
        { headers: headers() }
      );
      const fd = await fr.json();
      if (fr.ok && fd.content) {
        state.fieldsByModule[m.id] = MarkdownBridge.markdownToFields(
          m.id,
          MarkdownBridge.normalizeGeneratedContent(fd.content)
        );
      }
    } catch (_) {}
  }
  snapshotCurrentProject();
}

function renderReview() {
  const root = document.getElementById("reviewContent");
  root.innerHTML = "";
  const path = getProjectPath();
  if (!path) {
    root.innerHTML = "<p>请先选择项目</p>";
    return;
  }
  state.modules.forEach((m) => {
    const sec = document.createElement("section");
    sec.className = "review-module";
    const done = isCompleted(m.id);
    const fields = ensureFields(m.id);
    const md = MarkdownBridge.fieldsToMarkdown(m.id, fields);
    sec.innerHTML = `
      <div class="review-head">
        <h3>模块 ${m.id} · ${m.title}</h3>
        <span class="status-badge ${done ? "saved" : md.trim() ? "draft" : ""}">${done ? "已完成" : md.trim() ? "有草稿" : "空"}</span>
        <button type="button" class="btn btn-ghost btn-sm" data-goto="${m.id}">去编辑</button>
      </div>
      <div class="review-body markdown-body">${marked.parse(md || "_暂无内容_")}</div>
    `;
    sec.querySelector("[data-goto]").addEventListener("click", () => {
      document.getElementById("reviewOverlay").classList.add("hidden");
      switchTab(m.id);
    });
    root.appendChild(sec);
  });
}

async function fetchModules() {
  const res = await apiFetch("/api/modules");
  state.modules = await res.json();
  resetModulesEmpty();
}

async function fetchProjects() {
  const res = await apiFetch("/api/projects");
  const list = await res.json();
  const sel = document.getElementById("projectSelect");
  const cur = getProjectPath();
  sel.innerHTML = '<option value="">— 选择 —</option>';
  list.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.path;
    const prog = p.progress;
    const tag = prog ? ` · ${prog.completed_count}/9` : "";
    opt.textContent = p.path + tag;
    sel.appendChild(opt);
  });
  if (cur) sel.value = cur;
}

async function fetchHealth() {
  const res = await fetch(apiUrl("/api/health"), { headers: headers() });
  const h = await res.json();
  const pill = document.getElementById("healthPill");
  if (h.openai_configured) {
    pill.textContent = `${AI_LABEL} 就绪`;
    pill.className = "status-pill ok";
  } else {
    pill.textContent = `${AI_LABEL} 未配置`;
    pill.className = "status-pill warn";
  }
}

function bindEvents() {
  document.getElementById("loginForm")?.addEventListener("submit", handleLogin);
  document.getElementById("registerForm")?.addEventListener("submit", handleRegister);
  document.querySelectorAll(".auth-tab").forEach((btn) => {
    btn.addEventListener("click", () => setAuthTab(btn.dataset.authTab));
  });
  document.getElementById("logoutBtn")?.addEventListener("click", logout);

  document.getElementById("projectSelect").addEventListener("change", async (e) => {
    document.getElementById("projectPath").value = e.target.value;
    await onProjectChange(e.target.value);
  });

  document.getElementById("projectPath").addEventListener("change", async (e) => {
    const path = e.target.value.trim();
    document.getElementById("projectSelect").value = path;
    await onProjectChange(path);
  });

  ["topic", "audience", "stage", "coreQuestion"].forEach((id) => {
    document.getElementById(id).addEventListener("change", snapshotCurrentProject);
  });

  document.getElementById("generateBtn").addEventListener("click", generateModule);
  document.getElementById("saveBtn").addEventListener("click", saveModule);
  document.getElementById("markDoneBtn").addEventListener("click", toggleMarkDone);
  document.getElementById("loadFromDisk").addEventListener("click", async () => {
    if (!getProjectPath()) return alert("请先选择项目");
    await loadFromDisk();
    await fetchProgress();
    renderCanvas();
    await noteActivity("load_disk", "从 WIP/Research 载入到画布");
    document.getElementById("footerStatus").textContent = "已从磁盘重新载入";
  });
  document.getElementById("refreshProjects").addEventListener("click", fetchProjects);
  document.getElementById("exportPptBtn")?.addEventListener("click", exportPpt);
  window.ChatUI?.bind();
  document.getElementById("reviewAllBtn").addEventListener("click", () => {
    renderReview();
    document.getElementById("reviewOverlay").classList.remove("hidden");
  });
  document.getElementById("closeReview").addEventListener("click", () => {
    document.getElementById("reviewOverlay").classList.add("hidden");
  });
  document.getElementById("validateBtn").addEventListener("click", async () => {
    const path = getProjectPath();
    if (!path) return alert("请选择项目");
    const res = await apiFetch(`/api/validate?project_path=${encodeURIComponent(path)}`, {
      method: "POST",
    });
    const d = await res.json();
    alert(d.ok ? "校验通过" : "校验未通过");
  });
}

async function bootApp() {
  if (state.appReady) return;
  state.appReady = true;
  await fetchHealth();
  await fetchModules();
  renderTabs();

  const store = getStore();
  const last = store.lastProject || "";
  if (last) {
    document.getElementById("projectPath").value = last;
  }

  await fetchProjects();
  if (last) {
    document.getElementById("projectSelect").value = last;
    await onProjectChange(last);
  } else {
    resetModulesEmpty();
    renderCanvas();
    renderProgressUI();
    await fetchActivity();
  }
  if (window.InterviewsUI) await InterviewsUI.refresh();
  window.ChatUI?.setFabVisible(true);
  window.ChatUI?.updateModuleLabel();
}

async function init() {
  bindEvents();
  window.InterviewsUI?.bind();
  window.ChatUI?.reset();
  const ok = await checkAuth();
  if (ok) await bootApp();
}

init();
