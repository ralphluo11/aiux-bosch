(() => {
  "use strict";

  const allowedExtensions = new Set(["txt", "md", "csv", "json", "srt", "vtt", "docx"]);
  const input = document.querySelector("#file-input");
  const dropZone = document.querySelector("#drop-zone");
  const fileList = document.querySelector("#file-list");
  const namesInput = document.querySelector("#names");
  const termsInput = document.querySelector("#terms");
  const redactButton = document.querySelector("#redact");
  const downloadAllButton = document.querySelector("#download-all");
  const resultList = document.querySelector("#result-list");
  const summary = document.querySelector("#summary");
  const candidateReview = document.querySelector("#candidate-review");
  const candidateList = document.querySelector("#candidate-list");
  const confirmButton = document.querySelector("#confirm-redact");
  const errorBox = document.querySelector("#error");
  let files = [];
  let outputs = [];
  let candidates = [];

  const escapeRegex = value => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const canonical = value => value.replace(/[\s-]/g, "").toLowerCase();
  const lines = value => value.split(/\r?\n/).map(item => item.trim()).filter(Boolean);

  function defaultRules() {
    const surname = "(?:欧阳|司马|上官|诸葛|夏侯|东方|皇甫|尉迟|公孙|慕容|令狐|宇文|长孙|司徒|司空|端木|独孤|南宫|万俟|闻人|[赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹苏潘葛范彭鲁韦马方任袁柳史唐薛雷贺倪汤罗郝安常傅齐康伍余顾孟黄萧姚邵汪毛戴宋庞熊纪舒项祝董梁杜蓝席季麻贾江童颜郭梅林钟徐邱高夏蔡田樊胡霍万卢莫房解宗丁宣邓单洪左石崔龚程邢裴陆翁甄段富焦侯全班仲宁仇甘厉祖武符刘景詹龙叶白蒲鄂赖卓谭申冉牛温庄晏柴瞿阎连艾向古易廖聂辛简饶曾关查游权益])";
    return [
      ["邮箱", /(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])/gi],
      ["身份证", /(?<![0-9A-Za-z])[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?![0-9A-Za-z])/g],
      ["护照", /(?<![0-9A-Za-z])(?:[EGPSD]\d{7,8}|[HM]\d{8,10})(?![0-9A-Za-z])/gi],
      ["手机号", /(?<!\d)(?:\+?86[- ]?)?1[3-9]\d(?:[- ]?\d{4}){2}(?!\d)/g],
      ["银行卡", /(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)/g],
      ["车牌", /(?<![\u4e00-\u9fffA-Z0-9])[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}(?![A-Z0-9])/gi],
      ["IPv4", /(?<!\d)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\d)/g],
      ["QQ号", /((?:QQ(?:号|号码)?)[：:\s]*)([1-9]\d{4,11})/gi, 2],
      ["微信号", /((?:微信(?:号|号码)?|WeChat)[：:\s]*)([a-z][-_a-z0-9]{5,19})/gi, 2],
      ["姓名", /((?:姓名|联系人|受访者|参与者|客户姓名|用户姓名)[：:\s]*)([\u3400-\u9fff·]{2,6})/g, 2],
      ["姓名", new RegExp(`((?:我叫|本人叫|名字是|称呼是|联系人是|受访者是|参与者是)[：:\\s]*)(${surname}(?:[\\u3400-\\u9fff]{1,3}|[\\u3400-\\u9fff]+·[\\u3400-\\u9fff]+))`, "g"), 2],
      ["姓名", new RegExp(`^(${surname}[\\u3400-\\u9fff]{1,3})(?=[：:])`, "gm"), 1],
      ["地址", /((?:家庭?住址|居住地址|通讯地址|地址)[：:\s]*)([^\n,，;；]{4,100})/g, 2],
      ["座机", /(?<!\d)(?:\+?86[- ]?)?(?:0\d{2,3}[- ]?)?\d{7,8}(?:[-转 ]\d{1,6})?(?!\d)/g],
    ];
  }

  function customRules() {
    const rules = lines(namesInput.value).map(name => ["姓名", new RegExp(escapeRegex(name), "g")]);
    for (const entry of lines(termsInput.value)) {
      const splitAt = entry.indexOf("=");
      if (splitAt < 1 || splitAt === entry.length - 1) throw new Error(`自定义词条格式错误：${entry}`);
      const label = entry.slice(0, splitAt).trim();
      const value = entry.slice(splitAt + 1).trim();
      if (!label || !value) throw new Error(`自定义词条不能为空：${entry}`);
      rules.push([label, new RegExp(escapeRegex(value), "g")]);
    }
    return rules;
  }

  function redact(text, state, rules) {
    let result = text;
    for (const [label, pattern, group = 0] of rules) {
      result = result.replace(pattern, (...args) => {
        const match = args[0];
        const value = group ? args[group] : match;
        const key = `${label}\u0000${canonical(value)}`;
        if (!state.tokens.has(key)) {
          const next = (state.uniqueByType.get(label) || 0) + 1;
          state.uniqueByType.set(label, next);
          state.tokens.set(key, `[${label}_${String(next).padStart(3, "0")}]`);
          if (state.values) state.values.set(key, { label, value });
        }
        state.counts.set(label, (state.counts.get(label) || 0) + 1);
        const token = state.tokens.get(key);
        return group ? match.replace(value, token) : token;
      });
    }
    return result;
  }

  function setFiles(nextFiles) {
    files = Array.from(nextFiles).filter(file => allowedExtensions.has(file.name.split(".").pop().toLowerCase()));
    fileList.innerHTML = files.length ? files.map(file => `<div class="file-row"><span class="file-name">${safe(file.name)}</span><span class="file-meta">${formatBytes(file.size)}</span></div>`).join("") : '<p class="muted">没有可处理的文件</p>';
    redactButton.disabled = files.length === 0;
    outputs = [];
    candidates = [];
    downloadAllButton.disabled = true;
    candidateReview.hidden = true;
    resultList.innerHTML = "";
  }

  function safe(value) {
    const element = document.createElement("span");
    element.textContent = value;
    return element.innerHTML;
  }

  function formatBytes(size) { return size < 1024 ? `${size} B` : `${(size / 1024).toFixed(1)} KB`; }
  function outputName(name) { const dot = name.lastIndexOf("."); return dot < 0 ? `${name}.redacted` : `${name.slice(0, dot)}.redacted${name.slice(dot)}`; }

  const view = (bytes, offset, length) => new DataView(bytes.buffer, bytes.byteOffset + offset, length);
  const u16 = (bytes, offset) => view(bytes, offset, 2).getUint16(0, true);
  const u32 = (bytes, offset) => view(bytes, offset, 4).getUint32(0, true);
  const write16 = (target, offset, value) => new DataView(target.buffer).setUint16(offset, value, true);
  const write32 = (target, offset, value) => new DataView(target.buffer).setUint32(offset, value >>> 0, true);
  const concat = parts => {
    const result = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
    let offset = 0;
    for (const part of parts) { result.set(part, offset); offset += part.length; }
    return result;
  };

  const crcTable = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n += 1) {
      let value = n;
      for (let bit = 0; bit < 8; bit += 1) value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
      table[n] = value >>> 0;
    }
    return table;
  })();
  function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }

  async function inflateRaw(bytes) {
    if (typeof DecompressionStream === "undefined") throw new Error("当前浏览器不支持 DOCX 解压，请升级 Chrome、Edge 或 Safari。");
    let stream;
    try { stream = new DecompressionStream("deflate-raw"); }
    catch (_) { throw new Error("当前浏览器不支持 DOCX 的本地解压格式，请升级浏览器。"); }
    const response = new Response(new Blob([bytes]).stream().pipeThrough(stream));
    return new Uint8Array(await response.arrayBuffer());
  }

  async function readZip(bytes) {
    let eocd = -1;
    for (let index = bytes.length - 22; index >= Math.max(0, bytes.length - 65557); index -= 1) {
      if (u32(bytes, index) === 0x06054b50) { eocd = index; break; }
    }
    if (eocd < 0) throw new Error("DOCX 文件结构无效。");
    const entryCount = u16(bytes, eocd + 10);
    let cursor = u32(bytes, eocd + 16);
    const decoder = new TextDecoder("utf-8");
    const entries = [];
    for (let index = 0; index < entryCount; index += 1) {
      if (u32(bytes, cursor) !== 0x02014b50) throw new Error("DOCX 目录结构无效。");
      const flags = u16(bytes, cursor + 8);
      const method = u16(bytes, cursor + 10);
      const compressedSize = u32(bytes, cursor + 20);
      const nameLength = u16(bytes, cursor + 28);
      const extraLength = u16(bytes, cursor + 30);
      const commentLength = u16(bytes, cursor + 32);
      const localOffset = u32(bytes, cursor + 42);
      if (flags & 1) throw new Error("不支持加密的 DOCX 文件。");
      const name = decoder.decode(bytes.slice(cursor + 46, cursor + 46 + nameLength));
      const localNameLength = u16(bytes, localOffset + 26);
      const localExtraLength = u16(bytes, localOffset + 28);
      const dataStart = localOffset + 30 + localNameLength + localExtraLength;
      const compressed = bytes.slice(dataStart, dataStart + compressedSize);
      let data;
      if (method === 0) data = compressed;
      else if (method === 8) data = await inflateRaw(compressed);
      else throw new Error(`DOCX 包含不支持的压缩方式：${method}`);
      entries.push({ name, data });
      cursor += 46 + nameLength + extraLength + commentLength;
    }
    return entries;
  }

  function buildZip(entries) {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    let offset = 0;
    for (const entry of entries) {
      const name = encoder.encode(entry.name);
      const checksum = crc32(entry.data);
      const local = new Uint8Array(30 + name.length);
      write32(local, 0, 0x04034b50); write16(local, 4, 20); write16(local, 6, 0x0800); write16(local, 8, 0);
      write32(local, 14, checksum); write32(local, 18, entry.data.length); write32(local, 22, entry.data.length); write16(local, 26, name.length);
      local.set(name, 30);
      localParts.push(local, entry.data);

      const central = new Uint8Array(46 + name.length);
      write32(central, 0, 0x02014b50); write16(central, 4, 20); write16(central, 6, 20); write16(central, 8, 0x0800); write16(central, 10, 0);
      write32(central, 16, checksum); write32(central, 20, entry.data.length); write32(central, 24, entry.data.length); write16(central, 28, name.length); write32(central, 42, offset);
      central.set(name, 46);
      centralParts.push(central);
      offset += local.length + entry.data.length;
    }
    const central = concat(centralParts);
    const end = new Uint8Array(22);
    write32(end, 0, 0x06054b50); write16(end, 8, entries.length); write16(end, 10, entries.length); write32(end, 12, central.length); write32(end, 16, offset);
    return concat([...localParts, central, end]);
  }

  async function redactDocx(file, state, rules) {
    const entries = await readZip(new Uint8Array(await file.arrayBuffer()));
    const decoder = new TextDecoder("utf-8");
    const encoder = new TextEncoder();
    for (const entry of entries) {
      if (!/^word\/(?:document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$/.test(entry.name)) continue;
      const document = new DOMParser().parseFromString(decoder.decode(entry.data), "application/xml");
      if (document.querySelector("parsererror")) throw new Error(`无法解析 DOCX 内容：${entry.name}`);
      for (const node of document.getElementsByTagNameNS("http://schemas.openxmlformats.org/wordprocessingml/2006/main", "t")) {
        node.textContent = redact(node.textContent || "", state, rules);
      }
      entry.data = encoder.encode(new XMLSerializer().serializeToString(document));
    }
    return new Blob([buildZip(entries)], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
  }

  async function docxText(file) {
    const entries = await readZip(new Uint8Array(await file.arrayBuffer()));
    const decoder = new TextDecoder("utf-8");
    const parts = [];
    for (const entry of entries) {
      if (!/^word\/(?:document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$/.test(entry.name)) continue;
      const document = new DOMParser().parseFromString(decoder.decode(entry.data), "application/xml");
      if (document.querySelector("parsererror")) throw new Error(`无法解析 DOCX 内容：${entry.name}`);
      parts.push([...document.getElementsByTagNameNS("http://schemas.openxmlformats.org/wordprocessingml/2006/main", "t")].map(node => node.textContent || "").join("\n"));
    }
    return parts.join("\n");
  }

  function selectedRules() {
    return candidates.filter(candidate => candidate.selected).map(candidate => [candidate.label, new RegExp(escapeRegex(candidate.value), "g")]);
  }

  function renderCandidates() {
    candidateList.innerHTML = candidates.length ? candidates.map((candidate, index) => `
      <label class="candidate">
        <input type="checkbox" data-select="${index}" ${candidate.selected ? "checked" : ""} />
        <span class="candidate-type">${safe(candidate.label)}</span>
        <span class="candidate-value" title="${safe(candidate.value)}">${safe(candidate.value)}</span>
        <button class="remove-candidate" data-remove="${index}" type="button">删除</button>
      </label>`).join("") : '<p class="muted" style="padding:12px">没有保留的候选项</p>';
    confirmButton.disabled = !candidates.some(candidate => candidate.selected);
  }

  function download(output) {
    const url = URL.createObjectURL(output.blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = output.name;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  input.addEventListener("change", () => setFiles(input.files));
  for (const eventName of ["dragenter", "dragover"]) dropZone.addEventListener(eventName, event => { event.preventDefault(); dropZone.classList.add("dragging"); });
  for (const eventName of ["dragleave", "drop"]) dropZone.addEventListener(eventName, event => { event.preventDefault(); dropZone.classList.remove("dragging"); });
  dropZone.addEventListener("drop", event => setFiles(event.dataTransfer.files));

  redactButton.addEventListener("click", async () => {
    errorBox.hidden = true;
    try {
      const rules = [...customRules(), ...defaultRules()];
      const state = { tokens: new Map(), counts: new Map(), uniqueByType: new Map(), values: new Map() };
      outputs = [];
      for (const file of files) {
        const extension = file.name.split(".").pop().toLowerCase();
        redact(extension === "docx" ? await docxText(file) : await file.text(), state, rules);
      }
      candidates = [...state.values.values()].map(item => ({ ...item, selected: true }));
      summary.classList.remove("empty");
      const total = [...state.counts.values()].reduce((sum, count) => sum + count, 0);
      summary.innerHTML = `<span class="stat"><strong>${files.length}</strong> 个文件</span><span class="stat"><strong>${candidates.length}</strong> 个唯一候选</span><span class="stat"><strong>${total}</strong> 次出现</span>${[...state.counts].sort().map(([label, count]) => `<span class="stat">${safe(label)} ${count}</span>`).join("")}`;
      candidateReview.hidden = false;
      renderCandidates();
      resultList.innerHTML = "";
      downloadAllButton.disabled = true;
    } catch (error) {
      errorBox.textContent = error.message || "处理失败，请检查文件。";
      errorBox.hidden = false;
    }
  });

  candidateList.addEventListener("change", event => {
    const checkbox = event.target.closest("[data-select]");
    if (!checkbox) return;
    candidates[Number(checkbox.dataset.select)].selected = checkbox.checked;
    confirmButton.disabled = !candidates.some(candidate => candidate.selected);
  });
  candidateList.addEventListener("click", event => {
    const button = event.target.closest("[data-remove]");
    if (!button) return;
    event.preventDefault();
    candidates.splice(Number(button.dataset.remove), 1);
    renderCandidates();
  });
  document.querySelector("#select-all").addEventListener("click", () => { candidates.forEach(item => { item.selected = true; }); renderCandidates(); });
  document.querySelector("#select-none").addEventListener("click", () => { candidates.forEach(item => { item.selected = false; }); renderCandidates(); });

  confirmButton.addEventListener("click", async () => {
    errorBox.hidden = true;
    try {
      const rules = selectedRules();
      const state = { tokens: new Map(), counts: new Map(), uniqueByType: new Map() };
      outputs = [];
      for (const file of files) {
        const extension = file.name.split(".").pop().toLowerCase();
        const blob = extension === "docx"
          ? await redactDocx(file, state, rules)
          : new Blob([redact(await file.text(), state, rules)], { type: "text/plain;charset=utf-8" });
        outputs.push({ name: outputName(file.name), blob });
      }
      resultList.innerHTML = outputs.map((output, index) => `<div class="result-row"><div class="result-copy"><div class="file-name">${safe(output.name)}</div><p>已按确认项完成脱敏</p></div><button type="button" data-download="${index}">下载</button></div>`).join("");
      downloadAllButton.disabled = outputs.length === 0;
    } catch (error) {
      errorBox.textContent = error.message || "脱敏失败，请检查文件。";
      errorBox.hidden = false;
    }
  });

  resultList.addEventListener("click", event => {
    const button = event.target.closest("[data-download]");
    if (button) download(outputs[Number(button.dataset.download)]);
  });
  downloadAllButton.addEventListener("click", () => outputs.forEach((output, index) => setTimeout(() => download(output), index * 180)));
})();
