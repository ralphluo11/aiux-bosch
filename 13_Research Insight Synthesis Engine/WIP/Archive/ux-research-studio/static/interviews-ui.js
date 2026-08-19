/** 访谈素材上传 / 列表 / 转写 */
window.InterviewsUI = {
  async refresh() {
    const path =
      typeof getProjectPath === "function" ? getProjectPath() : "";
    const list = document.getElementById("interviewFileList");
    if (!list) return;
    if (!path) {
      list.innerHTML = '<li class="muted">请先选择项目</li>';
      return;
    }
    try {
      const res = await apiFetch(
        `/api/projects/${encodeURIComponent(path)}/interviews`
      );
      if (!res.ok) {
        list.innerHTML = '<li class="muted">加载失败</li>';
        return;
      }
      const data = await res.json();
      this._renderList(list, data, path);
    } catch {
      /* 401 等已由 apiFetch 处理 */
    }
  },

  _renderList(el, data, projectPath) {
    const items = [];
    (data.transcripts || []).forEach((t) => {
      items.push(
        `<li class="iv-ready"><span class="iv-tag">逐字稿</span> ${t.name} <span class="iv-meta">${Math.round(t.size / 1024)} KB</span></li>`
      );
    });
    (data.manifest || []).forEach((f) => {
      const st = f.status || "pending";
      const cls =
        st === "ready" ? "iv-ready" : st === "error" ? "iv-error" : "iv-pending";
      let actions = "";
      if (f.kind === "media" && st !== "ready") {
        actions = `<button type="button" class="btn btn-ghost btn-sm" data-transcribe="${f.id}">转写</button>`;
      }
      if (st === "error" && f.error) {
        actions += `<span class="iv-err" title="${f.error.replace(/"/g, "&quot;")}">失败</span>`;
      }
      actions += `<button type="button" class="btn btn-ghost btn-sm" data-delete="${f.id}">删除</button>`;
      items.push(
        `<li class="${cls}"><span class="iv-tag">${f.kind === "text" ? "文字" : "媒体"}</span> ${f.original_name} <span class="iv-meta">${st}</span> ${actions}</li>`
      );
    });
    const root = data.root || "06_interviews";
    if (!items.length) {
      el.innerHTML = `<li class="muted">暂无上传。目录：${projectPath}/WIP/Research/${root}/</li>`;
    } else {
      el.innerHTML = items.join("");
    }
    el.querySelectorAll("[data-transcribe]").forEach((btn) => {
      btn.addEventListener("click", () => this.transcribe(btn.dataset.transcribe));
    });
    el.querySelectorAll("[data-delete]").forEach((btn) => {
      btn.addEventListener("click", () => this.remove(btn.dataset.delete));
    });
  },

  async upload(fileList) {
    const path = getProjectPath();
    if (!path || !fileList?.length) return;
    const fd = new FormData();
    for (const f of fileList) fd.append("files", f);
    fd.append(
      "auto_transcribe",
      document.getElementById("autoTranscribe")?.checked ? "true" : "false"
    );
    const overlay = document.getElementById("loadingOverlay");
    const loadingText = document.getElementById("loadingText");
    overlay?.classList.remove("hidden");
    if (loadingText) loadingText.textContent = "正在上传 / 转写访谈素材…";
    try {
      const res = await fetch(apiUrl(`/api/projects/${encodeURIComponent(path)}/interviews/upload`), {
        method: "POST",
        headers: {
          ...(state.sessionToken ? { "X-Session-Token": state.sessionToken } : {}),
          ...(state.token ? { "X-Studio-Token": state.token } : {}),
        },
        body: fd,
      });
      if (res.status === 401) {
        forceLoginUI("请先登录");
        return;
      }
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "上传失败");
        return;
      }
      await this.refresh();
      document.getElementById("footerStatus").textContent =
        `已上传 ${data.uploaded?.length || 0} 个文件`;
    } finally {
      overlay?.classList.add("hidden");
      const input = document.getElementById("interviewFileInput");
      if (input) input.value = "";
    }
  },

  async transcribe(fileId) {
    const path = getProjectPath();
    if (!path) return;
    const res = await apiFetch(
      `/api/projects/${encodeURIComponent(path)}/interviews/${fileId}/transcribe`,
      { method: "POST" }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "转写失败");
      return;
    }
    await this.refresh();
    document.getElementById("footerStatus").textContent = "转写完成";
  },

  async remove(fileId) {
    if (!confirm("确定删除该素材及关联逐字稿？")) return;
    const path = getProjectPath();
    const res = await apiFetch(
      `/api/projects/${encodeURIComponent(path)}/interviews/${fileId}`,
      { method: "DELETE" }
    );
    if (res.ok) await this.refresh();
  },

  bind() {
    document.getElementById("interviewFileInput")?.addEventListener("change", (e) => {
      this.upload(e.target.files);
    });
  },
};
