const $=(s,r=document)=>r.querySelector(s);const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
let state={projects:[],project:null,view:"portfolio",folder:"brief",artifact:null,messages:[],busy:false,documentMode:"preview",editingQuestionIndex:null,pendingQuestionnaireGap:null,pendingQuestionnaireAdvice:null,pendingQuestionnaireQueue:[],questionnaireSuggestions:[],runtime:null,runtimeTimer:null};
const chatKey=id=>`uxgs-chat-${id}`;
function restoreMessages(id){try{const saved=JSON.parse(localStorage.getItem(chatKey(id))||"[]");state.messages=Array.isArray(saved)?saved:[]}catch{state.messages=[]}}
function persistMessages(){
  if(!state.project?.id)return;
  try{
    const compact=state.messages.slice(-100).map(message=>({
      role:message.role,
      text:String(message.text||"").slice(0,8000)
    }));
    localStorage.setItem(chatKey(state.project.id),JSON.stringify(compact));
  }catch(error){
    console.warn("Chat history could not be persisted",error);
  }
}
const folders=[
  ["context","背景资料来源","上传的 PRD、Charter 与业务资料"],
  ["brief","项目简报","AI 整理后、经人工修改的 Brief.md"],
  ["plan","研究计划与问卷","Research Plan、问卷大纲与问卷"],
  ["responses","问卷答案与原始数据","问卷回答、逐字稿、音视频与结果表"],
  ["evidence","证据与分析","Evidence、Finding、Recommendation"],
  ["review","人工审核","接受、修改、退回与审核理由"],
  ["delivery","交付成果","报告、Evidence Pack 与 Machine View"],
];
const artifactKinds={brief:["brief","Brief.md"],plan:["research_plan","Research Plan.md"],evidence:["evidence_analysis","Evidence and Analysis.md"],review:["human_review","Human Review.md"],delivery:["delivery","Delivery.md"]};
const STALE_REGENERATE_LABEL={plan:"重新生成问卷",evidence:"重新生成结构化结果",delivery:"重新生成 Delivery"};
function briefUpdatedAt(){
  const brief=(state.project?.artifacts||[]).find(a=>a.kind==="brief");
  return brief?.updated_at||null;
}
function downstreamStale(folderId){
  if(folderId==="brief"||folderId==="context"||folderId==="responses")return false;
  const briefAt=briefUpdatedAt();
  if(!briefAt)return false;
  if(folderId==="evidence"){
    const at=state.project?.latest_analysis?.created_at;
    return Boolean(at)&&new Date(briefAt)>new Date(at);
  }
  const kind=artifactKinds[folderId]?.[0];
  const artifact=kind?(state.project?.artifacts||[]).find(a=>a.kind===kind):null;
  if(!artifact)return false;
  return new Date(briefAt)>new Date(artifact.updated_at);
}
function staleNotice(folderId){
  if(!downstreamStale(folderId))return"";
  const regenLabel=STALE_REGENERATE_LABEL[folderId];
  const action=regenLabel?`<button class="button" data-regenerate-stale="${folderId}">🔄 ${regenLabel}</button>`:"";
  const note=folderId==="review"?"Project Brief 在这份记录生成之后又改过，建议人工核对结论是否仍然成立，不建议自动重跑覆盖已写的审核意见。":"Project Brief 在这份内容生成之后又改过，以下内容可能基于旧版本。";
  return `<div class="notice warn"><strong>⚠️ 可能已过期</strong><p>${note}</p>${action}</div>`;
}
function runtimePlan(path){
  if(path.endsWith("/summary"))return["读取 Brief 与背景来源","核对已确认信息","识别信息缺口","形成建议与依据","准备更新文档"];
  if(path.endsWith("/questionnaire"))return["读取已确认 Brief","检查研究目标与角色","组织研究阶段","生成开放问题与追问","检查覆盖与非引导性","准备写入问卷"];
  if(path.endsWith("/analyze"))return["读取研究原始资料","提取可追溯 Evidence","聚合 Findings","形成 Insights 与限制","准备结构化结果"];
  if(path.endsWith("/artifacts/revise"))return["读取当前文档","解析修改要求","保持证据边界","重写相关章节","准备写回文档"];
  return null;
}
function questionnaireGapId(text){
  const value=String(text||"");
  if(/受访|角色|决策者|操作人员|采购|负责人|渠道商|集成商/.test(value))return"TARGET_ROLE";
  if(/场景|行业|应用范围|草莓|大棚/.test(value))return"SCENARIO_SCOPE";
  if(/优先|价值点|研究重点|研究范围/.test(value))return"RESEARCH_PRIORITY";
  if(/业务.*决策|产品.*决策|支持.*决策|研究目标/.test(value))return"DECISION_TO_SUPPORT";
  if(/访谈形式|访谈时长|预计时长|样本|人数/.test(value))return"INTERVIEW_LOGISTICS";
  if(/商业|价格|采购方式|部署模式|运维模式|合作模式|ROI/.test(value))return"COMMERCIAL_SCOPE";
  if(/地域|市场范围|国家|省份|全国|海外/.test(value))return"GEOGRAPHY";
  if(/假设|替代方案|竞争|采用障碍/.test(value))return"HYPOTHESES_ALTERNATIVES";
  return `CUSTOM_${value.replace(/\s+/g,"").slice(0,32)}`;
}
function answeredQuestionnaireGapIds(notes){
  const ids=new Set();
  for(const match of String(notes||"").matchAll(/问题：([^\n]+)/g))ids.add(questionnaireGapId(match[1]));
  for(const match of String(notes||"").matchAll(/\[([A-Z_]+)\]/g))ids.add(match[1]);
  return ids;
}
function runtimeHtml(){if(!state.runtime)return '<div class="runtime-empty">等待任务 · 运行时会显示可审计阶段</div>';return `<div class="runtime-head"><strong>Live Runtime</strong><span>${esc(state.runtime.status)}</span></div><small>展示输入、阶段和结果；不展示模型隐藏的逐步思维链。</small><ol>${state.runtime.steps.map((step,index)=>`<li class="${index<state.runtime.current?"done":index===state.runtime.current&&state.runtime.status==="运行中"?"active":""}"><span>${index<state.runtime.current?"✓":index===state.runtime.current?"●":"○"}</span>${esc(step)}</li>`).join("")}</ol>`}
function updateRuntimeView(){const el=$("#runtime-trace");if(el){el.innerHTML=runtimeHtml();el.scrollTop=el.scrollHeight}}
function startRuntime(steps){clearInterval(state.runtimeTimer);state.runtime={steps,current:0,status:"运行中"};updateRuntimeView();state.runtimeTimer=setInterval(()=>{state.runtime.current=Math.min(state.runtime.current+1,state.runtime.steps.length-1);updateRuntimeView()},1200)}
function finishRuntime(ok,message){clearInterval(state.runtimeTimer);if(!state.runtime)return;state.runtime.current=ok?state.runtime.steps.length:state.runtime.current;state.runtime.status=ok?"完成":`失败 · ${message||"未知原因"}`;updateRuntimeView()}
async function api(path,options={}){const plan=options.method==="POST"?runtimePlan(path):null;if(plan)startRuntime(plan);try{const r=await fetch(path,{headers:{"Content-Type":"application/json"},...options});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error?.message||d.error||`HTTP ${r.status}`);if(plan)finishRuntime(true);return d}catch(error){if(plan)finishRuntime(false,error.message);throw error}}
function toast(t){const n=document.createElement("div");n.className="notice";n.textContent=t;$("#toast-region").append(n);setTimeout(()=>n.remove(),3600)}
function statusOf(p){if(p.latest_analysis)return["Review","已有分析，等待人工审核"];if(p.latest_questionnaire)return["Plan","问卷草案已生成"];const answered=(String(p.project_notes||"").match(/用户回答：/g)||[]).length;if(answered)return["Clarify",`已保存 ${answered} 项问卷前回答`];if((p.transcript_count||0)>0)return["Sources","资料已加入，等待整理"];return["Brief","项目简报待完善"]}
async function loadProjects(){const d=await api("/api/projects");state.projects=d.projects||[]}
async function openProject(id,folder="brief"){const switching=state.project?.id!==id;state.project=await api(`/api/projects/${id}`);if(switching)restoreMessages(id);state.view="workspace";state.folder=folder;state.documentMode="preview";state.editingQuestionIndex=null;selectArtifact();render()}
function selectArtifact(){const key=artifactKinds[state.folder]?.[0];state.artifact=key?(state.project?.artifacts||[]).find(a=>a.kind===key)||null:null}
function inlineMarkdown(value){return esc(value).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/`([^`]+)`/g,"<code>$1</code>")}
function markdownToHtml(markdown){
  const lines=String(markdown||"").split(/\r?\n/);let html="",list=null;
  const closeList=()=>{if(list){html+=`</${list}>`;list=null}};
  for(const raw of lines){
    const line=raw.trimEnd();
    if(!line.trim()){closeList();continue}
    const heading=line.match(/^(#{1,4})\s+(.+)$/);
    if(heading){closeList();const level=heading[1].length;html+=`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`;continue}
    if(/^>\s?/.test(line)){closeList();html+=`<blockquote>${inlineMarkdown(line.replace(/^>\s?/,""))}</blockquote>`;continue}
    const bullet=line.match(/^[-*]\s+(.*)$/);
    const ordered=line.match(/^\d+\.\s+(.*)$/);
    if(bullet||ordered){const type=bullet?"ul":"ol";if(list!==type){closeList();list=type;html+=`<${type}>`}const body=(bullet||ordered)[1];const task=body.match(/^\[([ xX])\]\s*(.*)$/);html+=task?`<li class="task ${task[1].trim()?"done":""}"><span aria-hidden="true">${task[1].trim()?"✓":"○"}</span>${inlineMarkdown(task[2])}</li>`:`<li>${inlineMarkdown(body)}</li>`;continue}
    closeList();
    if(/^---+$/.test(line)){html+="<hr/>";continue}
    html+=`<p>${inlineMarkdown(line)}</p>`;
  }
  closeList();return html;
}
function structuredDocument(markdown){
  const source=String(markdown||"");
  const title=(source.match(/^#\s+(.+)$/m)||[])[1]||"Research artifact";
  const withoutTitle=source.replace(/^#\s+.+\r?\n?/,"");
  const chunks=withoutTitle.split(/(?=^##\s+)/m).filter(chunk=>chunk.trim());
  const sections=chunks.map((chunk,index)=>{
    const match=chunk.match(/^##\s+(.+)$/m);
    const sectionTitle=match?.[1]|| (index===0?"Document status":"Details");
    const body=match?chunk.replace(/^##\s+.+\r?\n?/,""):chunk;
    const tone=/缺失|风险|限制|TBC|Gap/i.test(sectionTitle)?" warning":/Evidence|证据|确认|完成|Summary|总结/i.test(sectionTitle)?" evidence":"";
    return `<section class="artifact-section${tone}"><header><span>${String(index+1).padStart(2,"0")}</span><h2>${inlineMarkdown(sectionTitle)}</h2></header><div class="artifact-section-body">${markdownToHtml(body)}</div></section>`;
  }).join("");
  return `<div class="artifact-cover"><p class="eyebrow">Research artifact</p><h1>${inlineMarkdown(title)}</h1><div class="artifact-summary"><span>结构化阅读视图</span><span>${chunks.length} 个内容区块</span><span>底层版本：Markdown</span></div></div><div class="artifact-sections">${sections||`<section class="artifact-section">${markdownToHtml(withoutTitle)}</section>`}</div>`;
}
function parseQuestionBlocks(markdown){
  const source=String(markdown||"");
  const re=/^### (\d+)\.\s+(.+)$/gm;
  const matches=[...source.matchAll(re)];
  if(!matches.length)return null;
  const blocks=matches.map((m,i)=>{
    const start=m.index;
    const end=i+1<matches.length?matches[i+1].index:source.length;
    return {number:m[1],title:m[2],raw:source.slice(start,end).replace(/\s+$/,"")};
  });
  let preamble=source.slice(0,matches[0].index);
  preamble=preamble.replace(/\n##[^\n]*\n*$/,"\n").trim();
  return {preamble,blocks};
}
function questionBlockBody(raw){
  return raw.split("\n").slice(1).join("\n").replace(/^\n+/,"");
}
function rebuildQuestionnaireMarkdown(parsed){
  const body=parsed.blocks.map(b=>b.raw).join("\n\n");
  return parsed.preamble?`${parsed.preamble}\n\n${body}`:body;
}
function questionnaireView(content){
  const parsed=parseQuestionBlocks(content);
  if(!parsed)return `<article class="artifact-page structured-artifact">${structuredDocument(content)}</article>`;
  const preambleHtml=parsed.preamble?structuredDocument(parsed.preamble):"";
  const cards=parsed.blocks.map((block,index)=>{
    const editing=state.editingQuestionIndex===index;
    const body=questionBlockBody(block.raw);
    return `<div class="question-card">
      <div class="question-card-head"><strong>${esc(block.number)}. ${esc(block.title)}</strong>${editing?"":`<button class="button text" data-edit-question="${index}">✏️ 编辑</button>`}</div>
      ${editing
        ?`<textarea class="markdown-editor question-editor" id="question-edit-${index}">${esc(body)}</textarea><div class="doc-actions"><span></span><div><button class="button text" data-cancel-question="${index}">取消</button><button class="button primary" data-save-question="${index}">保存这道题</button></div></div>`
        :`<div class="question-card-body">${markdownToHtml(body)}</div>`}
    </div>`;
  }).join("");
  return `<article class="artifact-page structured-artifact">${preambleHtml}<div class="question-list"><h2>问卷大纲与问题</h2>${cards}</div></article>`;
}
function parseBriefSuggestions(markdown){
  const source=String(markdown||"");
  const re=/^### 建议 (\d+)$/gm;
  const matches=[...source.matchAll(re)];
  if(!matches.length)return null;
  return matches.map((m,i)=>{
    const start=m.index;
    const end=i+1<matches.length?matches[i+1].index:source.length;
    const chunk=source.slice(start,end);
    const gap=(chunk.match(/\*\*待补充：\*\*\s*([^\n]+)/)||[])[1]||"";
    const recommendation=(chunk.match(/\*\*AI 工作建议（待确认）：\*\*\s*([^\n]+)/)||[])[1]||"";
    const rationale=(chunk.match(/\*\*建议理由：\*\*\s*([^\n]+)/)||[])[1]||"";
    return {number:m[1],gap:gap.trim(),recommendation:recommendation.trim(),rationale:rationale.trim()};
  }).filter(item=>item.gap);
}
function briefView(content){
  const suggestions=parseBriefSuggestions(content);
  if(!suggestions||!suggestions.length)return `<article class="artifact-page structured-artifact">${structuredDocument(content)}</article>`;
  const withoutSuggestions=content.replace(/\n## 问卷生成前的 AI 建议[\s\S]*$/,"\n");
  const answered=answeredQuestionnaireGapIds(state.project?.project_notes||"");
  const rows=suggestions.map((s,index)=>{
    const isAnswered=answered.has(questionnaireGapId(s.gap));
    return `<div class="gap-row">
      <label for="gap-input-${index}"><strong>${esc(s.gap)}</strong>${isAnswered?'<span class="tag confidence-high">已回答过</span>':""}</label>
      <p class="gap-rationale">${esc(s.rationale)}</p>
      <textarea id="gap-input-${index}" class="gap-input" data-gap="${esc(s.gap)}">${esc(s.recommendation)}</textarea>
    </div>`;
  }).join("");
  return `<article class="artifact-page structured-artifact">${structuredDocument(withoutSuggestions)}</article><div class="gap-form"><h2>问卷生成前的 AI 建议 · 确认或改写</h2><p class="block-intro">每条已经预填 AI 的建议，可以直接用，也可以改成你自己的答案；填完一次性保存，不用逐条在对话里打字。</p>${rows}<div class="doc-actions"><span>${suggestions.length} 条待确认</span><div><button class="button primary" id="save-gap-form">保存并继续</button></div></div></div>`;
}
async function saveGapForm(){
  const rows=$$(".gap-input");
  const entries=rows.map(ta=>({gap:ta.dataset.gap,answer:ta.value.trim()})).filter(e=>e.answer);
  if(!entries.length)return toast("没有可保存的回答");
  const noteLines=entries.map(e=>`问题：${e.gap}\n用户回答：${e.answer}`);
  const notes=[state.project.project_notes||"",...noteLines].filter(Boolean).join("\n\n");
  state.project=await api(`/api/projects/${state.project.id}/brief`,{method:"POST",body:JSON.stringify({
    name:state.project.name,research_goal:state.project.research_goal,research_questions:state.project.research_questions,
    target_users:state.project.target_users||"",project_notes:notes,language:state.project.language||"zh-CN",
  })});
  toast("已保存，正在重新生成 Brief…");
  await summarizeWithRecommendations();
}
const EDITABLE_SELECTION_FOLDERS=["brief","plan","review","delivery"];
function editableSelectionScopeActive(){
  return EDITABLE_SELECTION_FOLDERS.includes(state.folder)&&state.documentMode!=="edit"&&state.editingQuestionIndex===null;
}
function selectionContainerFor(node){
  const el=node.nodeType===1?node:node.parentElement;
  return el?el.closest(".artifact-page, .question-card-body"):null;
}
function ensureSelectionToolbar(){
  let el=document.getElementById("selection-toolbar");
  if(!el){
    el=document.createElement("div");
    el.id="selection-toolbar";
    el.className="selection-toolbar";
    el.hidden=true;
    document.body.appendChild(el);
  }
  return el;
}
function hideSelectionToolbar(){
  const el=document.getElementById("selection-toolbar");
  if(el)el.hidden=true;
}
function handleSelectionChange(){
  const toolbar=ensureSelectionToolbar();
  if(!editableSelectionScopeActive()){toolbar.hidden=true;return;}
  const selection=window.getSelection&&window.getSelection();
  if(!selection||selection.isCollapsed||selection.rangeCount===0){toolbar.hidden=true;return;}
  const text=selection.toString().trim();
  if(!text||text.length>600){toolbar.hidden=true;return;}
  const range=selection.getRangeAt(0);
  const container=selectionContainerFor(range.commonAncestorContainer);
  if(!container){toolbar.hidden=true;return;}
  const rect=range.getBoundingClientRect();
  if(!rect||(rect.width===0&&rect.height===0)){toolbar.hidden=true;return;}
  toolbar.hidden=false;
  toolbar.style.top=`${window.scrollY+rect.top-42}px`;
  toolbar.style.left=`${window.scrollX+rect.left}px`;
  toolbar.innerHTML=`<button type="button" class="selection-toolbar-btn" data-open-selection-prompt>✨ 用 AI 改这段</button>`;
  toolbar.querySelector("[data-open-selection-prompt]").addEventListener("click",()=>openSelectionPromptBox(text,range));
}
function openSelectionPromptBox(text,range){
  const toolbar=ensureSelectionToolbar();
  const preview=text.length>60?`${text.slice(0,60)}…`:text;
  toolbar.innerHTML=`<div class="selection-prompt-box"><p class="selection-quote">已选中："${esc(preview)}"</p><textarea class="selection-prompt-input" placeholder="想怎么改？比如：更口语化 / 收窄到单一参与者 / 补充一个具体例子"></textarea><div class="selection-prompt-actions"><button type="button" class="button text" data-selection-cancel>取消</button><button type="button" class="button primary" data-selection-submit>生成</button></div></div>`;
  toolbar.querySelector("[data-selection-cancel]").addEventListener("click",()=>{toolbar.hidden=true});
  toolbar.querySelector("[data-selection-submit]").addEventListener("click",()=>submitSelectionPrompt(text,range,toolbar));
  toolbar.querySelector(".selection-prompt-input").focus();
}
async function submitSelectionPrompt(text,range,toolbar){
  const instruction=toolbar.querySelector(".selection-prompt-input").value.trim();
  if(!instruction)return;
  const submitBtn=toolbar.querySelector("[data-selection-submit]");
  submitBtn.disabled=true;submitBtn.textContent="生成中…";
  try{
    const [kind,title]=artifactKinds[state.folder]||["draft","草稿"];
    const result=await api(`/api/projects/${state.project.id}/artifacts/revise`,{method:"POST",body:JSON.stringify({kind,title,content:text,instruction})});
    insertInlineSuggestion(range,text,result.revised_content);
  }catch(error){
    toast(`生成失败：${error.message}`);
  }finally{
    toolbar.hidden=true;
  }
}
function insertInlineSuggestion(range,originalText,revisedText){
  const mark=document.createElement("mark");
  mark.className="ai-original-marked";
  try{
    range.surroundContents(mark);
  }catch(error){
    toast("这段文字跨越了多个格式区域，暂时无法在原位置插入建议；可以尝试只选中一句完整的话。");
    return;
  }
  const suggestion=document.createElement("span");
  suggestion.className="ai-suggestion-inline";
  suggestion.innerHTML=`<span class="ai-suggestion-label">AI 建议</span><span class="ai-suggestion-text"></span><span class="ai-suggestion-actions"><button type="button" data-accept>✓ 采用</button><button type="button" data-reject>✕ 忽略</button></span>`;
  suggestion.querySelector(".ai-suggestion-text").textContent=revisedText;
  mark.after(suggestion);
  suggestion.querySelector("[data-accept]").addEventListener("click",()=>acceptInlineSuggestion(mark,suggestion,originalText,revisedText));
  suggestion.querySelector("[data-reject]").addEventListener("click",()=>{
    suggestion.remove();
    const parent=mark.parentNode;
    mark.replaceWith(document.createTextNode(originalText));
    parent?.normalize();
  });
}
async function acceptInlineSuggestion(mark,suggestion,originalText,revisedText){
  const current=state.artifact?.content||"";
  if(!current.includes(originalText)){
    toast("原文位置已变化，无法自动写回；建议手动复制这段文字。");
    return;
  }
  const updated=current.replace(originalText,revisedText);
  suggestion.remove();
  mark.replaceWith(document.createTextNode(revisedText));
  await saveArtifact(updated);
}
async function saveQuestionBlockEdit(index){
  const parsed=parseQuestionBlocks(state.artifact?.content||"");
  if(!parsed||!parsed.blocks[index])return;
  const textarea=$(`#question-edit-${index}`);
  const heading=parsed.blocks[index].raw.split("\n")[0];
  parsed.blocks[index].raw=`${heading}\n${(textarea?.value||"").trim()}`;
  state.editingQuestionIndex=null;
  await saveArtifact(rebuildQuestionnaireMarkdown(parsed));
}
function artifactsForFolder(folder){
  if(folder==="context")return (state.project?.transcripts||[]).filter(item=>item.segment==="project_context").map(item=>({title:item.file_name,status:"Source"}));
  if(folder==="responses")return (state.project?.transcripts||[]).filter(item=>item.segment==="research_result").map(item=>({title:item.file_name,status:"Research data"}));
  if(folder==="evidence"){
    const a=state.project?.latest_analysis;
    return a?[{title:"Findings & Insights",status:`${(a.insights||[]).length} insight`}]:[];
  }
  const kind=artifactKinds[folder]?.[0];
  return kind?(state.project?.artifacts||[]).filter(item=>item.kind===kind):[];
}
function folderTree(){
  return folders.map(([id,label,desc])=>{
    const items=artifactsForFolder(id);
    const stale=downstreamStale(id);
    return `<section class="folder-group ${state.folder===id?"active":""}"><button class="folder" data-folder="${id}"><span class="folder-chevron">${state.folder===id?"⌄":"›"}</span><div><strong>${label}${stale?' <span class="stale-dot" title="可能已过期">⚠️</span>':""}</strong><small>${desc}</small></div><b>${items.length}</b></button>${state.folder===id?`<div class="folder-files">${items.map(item=>`<button class="file-node active" data-folder="${id}"><span class="file-type">${/\.md$/i.test(item.title)?"MD":"DOC"}</span><span><strong>${esc(item.title)}</strong><small>${esc(item.status||"Draft")}</small></span></button>`).join("")||'<div class="folder-empty">尚未生成文件</div>'}</div>`:""}</section>`;
  }).join("");
}
function messageHtml(message){
  const text=String(message.text||"");
  const artifactName=(text.match(/(?:生成了|已更新|生成)：?\s*([^\n]+\.(?:md|docx|pptx|json))/i)||[])[1];
  const body=esc(text).replace(/\n/g,"<br>");
  const card=artifactName?`<button class="chat-artifact" data-open-artifact="${esc(artifactName.trim())}"><span class="chat-artifact-icon">DOC</span><span><strong>${esc(artifactName.trim())}</strong><small>已保存到项目产物 · 点击打开</small></span><span>→</span></button>`:"";
  return `<div class="message ${message.role}"><div>${body}</div>${card}</div>`;
}
function header(){return `<img class="supergraphic" src="/assets/supergraphic-responsive.svg" alt="" aria-hidden="true"/><header class="topbar"><a class="brand" href="#" id="home-link" aria-label="返回项目列表"><img class="bosch-logo" src="/assets/bosch-logo.svg" alt="Bosch"/><div><strong>UXGS Research Studio</strong><small>Evidence-first Research Agent</small></div></a>${state.view==="workspace"?`<div class="project-head"><span>${esc(state.project?.name)}</span><button class="button" id="back-projects">所有项目</button></div>`:"<span>Project Portfolio</span>"}</header>`}
function portfolio(){return `<div class="wizard">${header()}<main class="portfolio"><div class="portfolio-title"><div><p class="eyebrow">Research Agent</p><h1>研究项目</h1><p>每个项目拥有独立资料、Artifact、审核状态和交付成果。</p></div><button class="button primary" id="new-project">新建项目</button></div><section class="project-grid">${state.projects.map(p=>{const s=statusOf(p);return `<article class="project-card"><button class="project-open" data-project="${p.id}" aria-label="打开项目 ${esc(p.name)}"><div class="project-card-top"><span class="status-label">${s[0]}</span><span>→</span></div><h2>${esc(p.name)}</h2><p>${esc(p.research_goal)}</p><div class="project-progress"><span>${s[1]}</span><strong>${p.transcript_count||0} 个来源</strong></div></button><div class="project-card-actions"><small>${esc(p.id)}</small><button class="button danger" data-delete-project="${p.id}" data-project-name="${esc(p.name)}">删除项目</button></div></article>`}).join("")||'<div class="empty">还没有项目。新建一个项目开始。</div>'}</section></main></div>`}
function newProject(){return `<div class="wizard">${header()}<main class="new-project-page"><p class="eyebrow">New project</p><h1>先告诉 Research Agent 你要研究什么</h1><p>这不是必须一次填完的表单。只写你确定的内容，其余信息进入项目后通过对话和资料逐步补齐。</p><form class="card" id="new-project-form"><div class="field"><label>项目名称</label><input name="name" required/></div><div class="field"><label>目前确定的研究目标</label><textarea name="goal" required></textarea></div><div class="field"><label>目前最想回答的问题</label><textarea name="question" required></textarea></div><div class="actions"><button class="button" id="cancel-new" type="button">取消</button><button class="button primary" type="submit">创建项目并开始对话</button></div></form></main></div>`}
function sourceCard(f){const category=f.segment||"unclassified";return `<article class="source-item"><div><strong>${esc(f.file_name)}</strong><small>${category==="project_context"?"项目背景":category==="research_result"?"调研原始资料":"待分类，不参与 AI 运行"}</small></div><div class="file-actions"><select data-classify="${f.id}" aria-label="修改 ${esc(f.file_name)} 的分类"><option value="unclassified" ${!f.segment||category==="unclassified"?"selected":""}>待分类</option><option value="project_context" ${category==="project_context"?"selected":""}>项目背景</option><option value="research_result" ${category==="research_result"?"selected":""}>调研原始资料</option></select><button class="icon-button danger" data-delete="${f.id}" aria-label="删除 ${esc(f.file_name)}">删除</button></div></article>`}
function sourcesPane(category){const items=(state.project?.transcripts||[]).filter(f=>category==="project_context"?f.segment==="project_context":f.segment==="research_result");const isContext=category==="project_context";return `<div class="document-pane"><div class="doc-heading"><div><p class="eyebrow">${isContext?"Source Registry":"Response Registry"}</p><h1>${isContext?"背景资料来源":"问卷答案与原始研究数据"}</h1><p>${isContext?"只用于理解项目、补齐 Brief 和制定研究计划。":"问卷完成后，把回答、逐字稿、结果表或录音录像放在这里。只有这里的内容进入结构化 Evidence 与 Analysis。"}</p></div></div>${!isContext?'<div class="notice"><strong>推荐的答案结构</strong>表格建议包含 participant_id、question_id、question、answer；访谈逐字稿应保留完整 Q+A，音视频将保留时间码。</div>':""}<div class="upload-zone"><input id="source-files" type="file" multiple accept=".txt,.md,.csv,.json,.docx,.pptx,.xlsx,.pdf,.png,.jpg,.jpeg,.webp,.gif,.mp3,.mp4,.mpeg,.mpga,.m4a,.wav,.webm"/><button class="button" id="upload-source" data-category="${category}">${isContext?"上传背景资料":"上传问卷答案／研究数据"}</button><small>支持文档、PDF、图片、音频和视频，单文件上限 25 MB。图片和音视频需要 Live AI；PDF 保留页码，音视频保留时间码。</small></div><div class="source-list">${items.map(sourceCard).join("")||`<div class="empty">${isContext?"这个文件夹还没有背景资料":"问卷尚未产生答案，或答案还没有上传"}</div>`}</div>${!isContext&&items.length?'<div class="doc-actions"><span>这些来源将作为结构化分析的唯一研究数据</span><button class="button primary" id="analyze-responses">生成结构化结果</button></div>':""}</div>`}
function defaultDocument(){const p=state.project;if(state.folder==="brief")return `# ${p.name} - Project Brief\n\n## 研究目标\n${p.research_goal}\n\n## 研究问题\n${p.research_questions.map(x=>`- ${x}`).join("\n")}\n\n## 目标用户\n${p.target_users||"TBC"}\n\n## 仍需补充\n- Sponsor / Owner: TBC\n- 决策与成功标准: TBC\n- 数据等级与权限: TBC\n`;
if(state.folder==="plan")return `# Research Plan\n\n当前尚未生成研究计划。请在右侧对话中要求 Agent 检查 Brief 和背景资料。\n`;
if(state.folder==="evidence")return `# Evidence and Analysis\n\n当前尚未运行证据提取与分析。\n`;
if(state.folder==="review")return `# Human Review\n\n- 状态: Draft\n- Reviewer: TBC\n- 审核意见: TBC\n`;
return `# Delivery\n\n当前尚未生成结构化交付。\n`;}
function documentPane(){
  if(state.folder==="evidence"){
    return `<div class="document-pane"><div class="doc-heading"><div><p class="eyebrow">Project output</p><h1>证据与分析</h1><p>关键发现为主视图；点开每条结论查看支撑证据、Theme 归属与 Judge 判定。</p></div></div>${staleNotice("evidence")}<div class="notice"><strong>结构化结果来源边界</strong>这里只分析"问卷答案与原始数据"，不会把 PRD、Charter 等项目背景当成用户回答。</div>${reportView(state.project.latest_analysis)}</div>`;
  }
  const meta=artifactKinds[state.folder],content=state.artifact?.content||defaultDocument(),editing=state.documentMode==="edit";
  const usesQuestionCards=state.folder==="plan"&&!editing&&parseQuestionBlocks(content);
  const bodyHtml=editing?`<textarea class="markdown-editor" id="artifact-editor" aria-label="编辑 ${esc(meta[1])}">${esc(content)}</textarea>`
    :state.folder==="plan"?questionnaireView(content)
    :state.folder==="brief"?briefView(content)
    :`<article class="artifact-page structured-artifact">${structuredDocument(content)}</article>`;
  return `<div class="document-pane"><div class="doc-heading"><div><p class="eyebrow">Project output</p><h1>${esc(meta[1])}</h1><p>${usesQuestionCards?"每道题可单独编辑；改动只影响这一道题，不会动其他题目。":"这里展示可审阅的结构化产物；Markdown 只作为底层可移植格式。"}</p></div><div class="doc-heading-actions"><span class="status-label">${esc(state.artifact?.status||"Draft")}</span><button class="button" id="toggle-document-mode">${editing?"结构化预览":"编辑整篇源文件"}</button></div></div>${editing?"":staleNotice(state.folder)}${bodyHtml}<div class="doc-actions"><span>${editing?"Markdown 源文件编辑模式":"结构化阅读模式 · 自动保存为项目 Artifact"}</span><div>${editing?'<button class="button primary" id="save-artifact">保存并预览</button>':""}</div></div></div>`;
}
function chatPane(){const prompts=state.folder==="context"?["整理背景资料清单","根据背景资料总结项目","检查还缺哪些背景"]:state.folder==="brief"?["根据背景资料总结项目","检查 Brief 还缺什么","把我的回答写入 Brief"]:state.folder==="plan"?["检查是否可以生成研究计划","先生成问卷大纲","根据确认的大纲生成具体问题"]:state.folder==="responses"?["检查问卷答案是否完整","生成结构化结果","列出缺失回答和数据问题"]:state.folder==="evidence"?["从问卷答案提取 Evidence","标记冲突与证据缺口","生成结构化结果"]:state.folder==="review"?["生成审核清单","总结需要人工确认的内容","把审核意见写入文档"]:state.folder==="delivery"?["生成 One-page Delivery","生成 Evidence Pack 目录","检查交付还缺什么"]:["总结当前文件夹","检查下一道 Gate"];
return `<aside class="chat-pane"><div class="chat-title"><span class="ai-dot">AI</span><div><strong>Research Agent</strong><small>生成的结果会作为项目产物保存</small></div></div><section class="runtime-trace" id="runtime-trace" aria-live="polite">${runtimeHtml()}</section><div class="messages">${state.messages.map(messageHtml).join("")||'<div class="message"><div>我会把对话结果保存成左侧可打开的项目产物。缺失信息会标成 TBC，不会猜测。</div></div>'}</div><div class="prompt-chips">${prompts.map(x=>`<button data-prompt="${esc(x)}">${esc(x)}</button>`).join("")}</div><div class="composer"><textarea id="chat-input" placeholder="说你想整理、检查或生成什么…"></textarea><div><label class="attach"><input id="chat-files" type="file" multiple accept=".txt,.md,.csv,.json,.docx,.pptx,.xlsx,.pdf,.png,.jpg,.jpeg,.webp,.gif,.mp3,.mp4,.mpeg,.mpga,.m4a,.wav,.webm" hidden/>＋ 添加资料</label><button class="button primary" id="send-chat">发送</button></div></div></aside>`}
function workspace(){return `<div class="wizard">${header()}<div class="workspace-shell"><nav class="folder-nav" aria-label="项目产物空间"><div class="project-summary"><small>PROJECT OUTPUTS</small><strong>${esc(state.project.name)}</strong><span>${statusOf(state.project)[1]}</span></div><div class="tree-label">产物与资料</div>${folderTree()}</nav>${state.folder==="context"?sourcesPane("project_context"):state.folder==="responses"?sourcesPane("research_result"):documentPane()}${chatPane()}</div></div>`}
function render(){
  persistMessages();
  hideSelectionToolbar();
  const previousDocumentScroll=$(".document-pane")?.scrollTop||0;
  const previousFolderScroll=$(".folder-nav")?.scrollTop||0;
  document.body.classList.toggle("workspace-mode",state.view==="workspace");
  $("#app").innerHTML=state.view==="portfolio"?portfolio():state.view==="new"?newProject():workspace();
  bind();
  const documentPaneElement=$(".document-pane");if(documentPaneElement)documentPaneElement.scrollTop=previousDocumentScroll;
  const folderPaneElement=$(".folder-nav");if(folderPaneElement)folderPaneElement.scrollTop=previousFolderScroll;
  const messagesElement=$(".messages");if(messagesElement)messagesElement.scrollTop=messagesElement.scrollHeight;
}
async function regeneratePlan(){
  toast("正在重新生成问卷…");
  const q=await api(`/api/projects/${state.project.id}/questionnaire`,{method:"POST",body:"{}"});
  const md=`# ${q.title}\n\n## 推断 Track\n${q.inferred_track} - ${q.track_rationale}\n\n## 缺失信息\n${(q.missing_information||[]).map(x=>`- ${x}`).join("\n")||"- 无"}\n\n## 问卷大纲与问题\n${q.questions.map((x,i)=>`### ${i+1}. ${x.intent}\n${x.text}\n\n- 可能回答方向: ${(x.possible_answers||[]).join("；")}\n- 建议追问: ${(x.suggested_probes||[]).join("；")}`).join("\n\n")}`;
  await saveArtifact(md);
}
async function saveArtifact(content){const [kind,title]=artifactKinds[state.folder];await api(`/api/projects/${state.project.id}/artifacts`,{method:"POST",body:JSON.stringify({kind,title,content,status:"human_edited"})});await openProject(state.project.id,state.folder);toast("文档已保存")}
async function upload(category,files){for(const f of files){const b64=await new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(String(r.result).split(",")[1]);r.onerror=no;r.readAsDataURL(f)});await api(`/api/projects/${state.project.id}/documents`,{method:"POST",body:JSON.stringify({source_id:`SRC-${Date.now()}-${Math.random().toString(16).slice(2,6)}`,file_name:f.name,content_base64:b64,segment:category})})}await openProject(state.project.id,state.folder);toast("文件已加入当前项目")}
function questionnaireMarkdown(q){return `# ${q.title}\n\n## Research Track\n- Track: ${q.inferred_track}\n- 判断依据: ${q.track_rationale}\n\n## Evidence Readiness\n> 每道问题必须说明要获得什么证据、如何按缺口追问，以及何时可以进入下一题。问题覆盖不等于证据覆盖。\n\n## 缺失信息与风险\n${(q.missing_information||[]).map(x=>`- ${x}`).join("\n")||"- 无"}\n\n## 深度访谈设计\n${q.questions.map((x,i)=>`### ${i+1}. ${x.intent}\n**主问题：** ${x.text}\n\n**对应研究问题：** ${(x.research_question_ids||[]).join("、")}\n\n**需要获得的证据**\n${(x.evidence_needed||[]).map(item=>`- ${item}`).join("\n")||"- TBC"}\n\n**Probe Tree**\n${(x.suggested_probes||[]).map(item=>`- ${item}`).join("\n")||"- TBC"}\n\n**完成标准**\n${(x.completion_criteria||[]).map(item=>`- ${item}`).join("\n")||"- TBC"}\n\n**停止条件**\n${(x.stop_conditions||[]).map(item=>`- ${item}`).join("\n")||"- TBC"}\n\n- 时间护栏: 最多 ${x.max_followups??"TBC"} 次追问`).join("\n\n")}`}
async function runChat(text){state.messages.push({role:"user",text});if(/背景资料.*总结|总结项目|总结.*背景/.test(text)){state.messages.push({role:"assistant",text:"正在读取已分类为“项目背景”的来源，并检查 Brief 缺口…"});render();try{const s=await api(`/api/projects/${state.project.id}/summary`,{method:"POST",body:"{}"});const confirmed=(s.confirmed_information||[]).map(x=>`- ${x.field}: ${x.value}（来源: ${(x.source_ids||[]).join("、")||"未绑定"}）`).join("\n")||"- 暂无可确认信息";const missing=(s.missing_information||[]).map(x=>`- ${x}`).join("\n")||"- 无";const md=`# ${state.project.name} - Project Brief\n\n> Status: AI-generated draft\n> Mode: ${s.agent_mode||"unknown"}\n> Model: ${s.model||"none"}\n\n## 项目总结\n${s.context_summary||"未生成总结"}\n\n## 已确认信息\n${confirmed}\n\n## Research Track 建议\n- Track: ${s.inferred_track||"uncertain"}\n- 判断依据: ${s.track_rationale||"未提供"}\n\n## 仍需补充\n${missing}\n\n## 本次读取来源\n${(s.source_files||[]).map((x,i)=>`- ${x} (${s.source_ids[i]})`).join("\n")||"- 只读取了 Project Brief；没有已分类的背景文件"}\n`;state.folder="brief";selectArtifact();await saveArtifact(md);state.messages.push({role:"assistant",text:`运行完成\n\n生成了：Brief.md\n运行模式：${s.agent_mode||"unknown"}${s.model?` / ${s.model}`:""}\n读取来源：${(s.source_files||[]).length} 个\n已确认信息：${(s.confirmed_information||[]).length} 项\n未生成／待补充：${(s.missing_information||[]).length} 项\n\n公开判断依据：${s.track_rationale||"未提供"}\n\n缺失信息：\n${missing}\n\n说明：这里展示可审计的输入、输出与判断依据，不展示模型隐藏的逐步思维过程。`});render()}catch(error){state.messages.push({role:"assistant",text:`运行失败\n\n没有生成 Brief.md。\n原因：${error.message}\n下一步：检查 Live AI 配置、背景文件分类和文件解析状态。`});render()}return}if(state.folder==="plan"&&/问卷|计划/.test(text)){state.messages.push({role:"assistant",text:"正在检查 Brief 并生成研究计划／问卷草案…"});render();const q=await api(`/api/projects/${state.project.id}/questionnaire`,{method:"POST",body:"{}"});const md=`# ${q.title}\n\n## 推断 Track\n${q.inferred_track} - ${q.track_rationale}\n\n## 缺失信息\n${(q.missing_information||[]).map(x=>`- ${x}`).join("\n")||"- 无"}\n\n## 问卷大纲与问题\n${q.questions.map((x,i)=>`### ${i+1}. ${x.intent}\n${x.text}\n\n- 可能回答方向: ${(x.possible_answers||[]).join("；")}\n- 建议追问: ${(x.suggested_probes||[]).join("；")}`).join("\n\n")}`;await saveArtifact(md);state.messages.push({role:"assistant",text:`运行完成\n生成了：Research Plan.md\n模式：${q.agent_mode}\n缺失信息：${(q.missing_information||[]).length} 项`});render()}else{state.messages.push({role:"assistant",text:"没有生成文件。原因：当前请求尚未映射到这个文件夹的受控 Agent 节点。请使用建议动作，或明确指定要更新的 Artifact。"});render()}}
const VERDICT_LABELS={pass:["✓ Pass","success"],revise:["↻ Revise","warning"],reject:["✕ Reject","error"],human_review:["◐ 需人工审核","accent"]};
function verdictBadge(verdict){const [label,tone]=VERDICT_LABELS[verdict]||["—","accent"];return `<span class="verdict-badge tone-${tone}">${esc(label)}</span>`}
function evidenceDetail(analysis,insight){
  const findingsById=Object.fromEntries((analysis.findings||[]).map(f=>[f.finding_id,f]));
  const evidenceById=Object.fromEntries((analysis.evidence||[]).map(e=>[e.evidence_id,e]));
  const themesById=Object.fromEntries((analysis.themes||[]).map(t=>[t.theme_id,t]));
  const flagsByFinding={};for(const flag of (analysis.quality_assurance?.overgeneralization_flags||[]))(flagsByFinding[flag.finding_id]??=[]).push(flag);
  const judgement=(analysis.quality_assurance?.judgements||[]).find(j=>j.insight_id===insight.insight_id);
  const findingBlocks=(insight.finding_ids||[]).map(id=>findingsById[id]).filter(Boolean).map(f=>{
    const evidenceItems=(f.evidence_ids||[]).map(id=>evidenceById[id]).filter(Boolean);
    const themeNames=(f.theme_ids||[]).map(id=>themesById[id]?.name).filter(Boolean);
    const flags=flagsByFinding[f.finding_id]||[];
    return `<div class="evidence-finding">
      <div class="evidence-finding-head"><strong>${esc(f.title)}</strong>${themeNames.length?`<span class="tag">Theme: ${esc(themeNames.join("、"))}</span>`:""}</div>
      <p>${esc(f.statement)}</p>
      ${flags.length?`<div class="notice warn"><strong>需要人工确认</strong>${flags.map(fl=>esc(fl.message)).join("<br>")}</div>`:""}
      <ul class="evidence-quotes">${evidenceItems.map(e=>`<li><span class="quote-participant">${esc(e.participant_id)}</span>“${esc(e.quote)}”</li>`).join("")||"<li>无逐字证据</li>"}</ul>
    </div>`;
  }).join("");
  const lastRevision=(insight.revision_history||[]).slice(-1)[0];
  return `<div class="evidence-detail">
    ${judgement?`<div class="judge-line">${verdictBadge(judgement.verdict)}<span>${esc(judgement.note||"")}</span></div>`:""}
    ${lastRevision?`<div class="notice"><strong>该结论已被 Judge 要求收窄一次</strong><p>原表述：${esc(lastRevision.previous_statement)}</p></div>`:""}
    ${findingBlocks||"<p>暂无关联 Finding</p>"}
  </div>`;
}
function reportView(analysis){
  if(!analysis){
    return `<div class="empty">还没有分析结果。<br>请先在"问卷答案与原始数据"上传回答或逐字稿，再生成结构化结果。</div>
    <div class="doc-actions"><span></span><div><button class="button primary" id="generate-analysis">生成结构化结果</button></div></div>`;
  }
  const insights=analysis.insights||[];
  const gaps=[...(analysis.gaps||[]),...(analysis.limitations||[])];
  return `<article class="artifact-page report-view">
    <p class="eyebrow">Research Report</p>
    <h1>${esc(state.project.name)} · 研究结论</h1>
    <p class="report-meta">状态：${esc(analysis.review_status||"AI Draft")} · 模式：${esc(analysis.agent_mode||"—")}${analysis.model?` · ${esc(analysis.model)}`:""}</p>
    <h2>Executive Summary</h2>
    <p>${esc(analysis.executive_summary||"暂无总结")}</p>
    <h2>关键发现（${insights.length}）</h2>
    ${insights.length?insights.map(i=>`
      <details class="report-insight">
        <summary><strong>${esc(i.statement)}</strong><span class="tag confidence-${esc(i.confidence||"low")}">${esc(i.confidence||"—")}</span><span class="reveal-hint">查看证据</span></summary>
        ${evidenceDetail(analysis,i)}
      </details>`).join(""):'<div class="empty">Evidence 尚不足以形成 Insight</div>'}
    ${gaps.length?`<h2>Gaps &amp; Limitations</h2><ul>${gaps.map(g=>`<li>${esc(typeof g==="string"?g:g.statement||g.description||JSON.stringify(g))}</li>`).join("")}</ul>`:""}
  </article>
  <div class="doc-actions"><span>结构化阅读模式 · 直接来自最新一次分析</span><div><button class="button" id="generate-analysis">重新生成结构化结果</button></div></div>`;
}
async function analyzeResponses(){const sources=(state.project.transcripts||[]).filter(x=>x.segment==="research_result");if(!sources.length)return toast("请先在“问卷答案与原始数据”上传回答或逐字稿");toast("正在从问卷答案生成结构化 Evidence 与 Analysis…");await api(`/api/projects/${state.project.id}/analyze`,{method:"POST",body:"{}"});await openProject(state.project.id,"evidence");toast("结构化结果已生成，等待人工审核")}
async function summarizeWithRecommendations(){
  const result=await api(`/api/projects/${state.project.id}/summary`,{method:"POST",body:"{}"});
  const confirmed=(result.confirmed_information||[]).map(x=>`- ${x.field}: ${x.value}（来源: ${(x.source_ids||[]).join("、")||"未绑定"}）`).join("\n")||"- 暂无可确认信息";
  const missing=(result.missing_information||[]).map(x=>`- ${x}`).join("\n")||"- 无";
  const suggestions=(result.suggested_information||[]).map((x,index)=>`### 建议 ${index+1}\n**待补充：** ${x.gap}\n\n**AI 工作建议（待确认）：** ${x.recommendation}\n\n**建议理由：** ${x.rationale}`).join("\n\n")||"- AI 暂未提供建议，请用户补充或重新运行。";
  const md=`# ${state.project.name} - Project Brief\n\n> Status: AI-generated draft / Human confirmation required\n> Mode: ${result.agent_mode||"unknown"}\n> Model: ${result.model||"none"}\n\n## 项目总结\n${result.context_summary||"未生成总结"}\n\n## 已确认信息\n${confirmed}\n\n## Research Track 建议\n- Track: ${result.inferred_track||"uncertain"}\n- 判断依据: ${result.track_rationale||"未提供"}\n\n## 仍需补充\n${missing}\n\n## 问卷生成前的 AI 建议\n> 以下内容是推进工作的建议，不是项目事实。请在右侧对话中确认、修改或否决；确认后再生成问卷大纲。\n\n${suggestions}\n\n## 本次读取来源\n${(result.source_files||[]).map((x,i)=>`- ${x} (${result.source_ids[i]})`).join("\n")||"- 只读取了 Project Brief；没有已分类的背景文件"}\n`;
  state.folder="brief";selectArtifact();await saveArtifact(md);return result;
}
async function questionnaireGate(){
  const brief=(state.project.artifacts||[]).find(item=>item.kind==="brief")?.content||"";
  const missingSection=brief.match(/## 仍需补充\s*([\s\S]*?)(?=\n## |$)/);
  const localGaps=(missingSection?.[1]||"").split("\n").map(line=>line.match(/^[-*]\s+(.+)$/)?.[1]?.trim()).filter(Boolean).filter(item=>item!=="无"&&!/^无[。.]?$/.test(item));
  const fallbackGaps=[
    "请确认本轮优先覆盖的目标受访者类型与角色。",
    "请确认本轮研究要优先支持的业务或产品决策。",
    "请确认需要覆盖的主要应用场景及优先顺序。",
    "请确认访谈形式、预计时长与样本范围。",
    "请确认必须验证的假设、替代方案或采用障碍。"
  ];
  const gateGaps=missingSection?localGaps:fallbackGaps;
  const check={
    missing_information:gateGaps,
    suggested_information:gateGaps.map(gap=>({gap,recommendation:"请基于当前项目实际情况确认；也可以让 AI 先给建议。",rationale:"该信息会影响访纲分组、阶段设计和追问深度。"}))
  };
  const answeredIds=answeredQuestionnaireGapIds(state.project.project_notes||"");
  const gaps=(check.missing_information||[]).filter(gap=>!answeredIds.has(questionnaireGapId(gap)));
  if(!gaps.length){state.pendingQuestionnaireGap=null;return true}
  state.pendingQuestionnaireQueue=gaps.slice(1);
  state.questionnaireSuggestions=check.suggested_information||[];
  const gap=gaps[0];
  const advice=(check.suggested_information||[]).find(x=>x.gap===gap)||(check.suggested_information||[])[0];
  state.pendingQuestionnaireGap=gap;
  state.pendingQuestionnaireAdvice=advice?.recommendation||null;
  state.messages.push({role:"assistant",text:`生成问卷前还缺少一项关键信息：\n\n${gap}\n\nAI 建议（待确认）：${advice?.recommendation||"请根据当前项目实际情况补充。"}\n建议理由：${advice?.rationale||"这项信息会直接影响受访者分组和问题深度。"}\n\n你可以直接回答，也可以说“采用建议”。收到后我会写入 Brief，再检查下一项。`});
  render();return false;
}
async function saveQuestionnaireClarification(answer){
  const gap=state.pendingQuestionnaireGap;
  const effectiveAnswer=/采用.*建议|接受.*建议/.test(answer)&&state.pendingQuestionnaireAdvice?state.pendingQuestionnaireAdvice:answer;
  const notes=[state.project.project_notes||"",`问卷前澄清 [${questionnaireGapId(gap)}]\n问题：${gap}\n用户回答：${effectiveAnswer}`].filter(Boolean).join("\n\n");
  const payload={name:state.project.name,research_goal:state.project.research_goal,research_questions:state.project.research_questions,target_users:state.project.target_users||"",project_notes:notes,language:state.project.language||"zh-CN"};
  state.project=await api(`/api/projects/${state.project.id}/brief`,{method:"POST",body:JSON.stringify(payload)});
  state.pendingQuestionnaireGap=null;
  state.pendingQuestionnaireAdvice=null;
  state.messages.push({role:"user",text:answer},{role:"assistant",text:"已把回答写入 Project Brief，正在重新检查问卷生成条件…"});render();
  if(state.pendingQuestionnaireQueue.length){
    const nextGap=state.pendingQuestionnaireQueue.shift();
    const advice=state.questionnaireSuggestions.find(x=>x.gap===nextGap);
    state.pendingQuestionnaireGap=nextGap;
    state.pendingQuestionnaireAdvice=advice?.recommendation||null;
    state.messages.push({role:"assistant",text:`上一项已保存。下一项：\n\n${nextGap}\n\nAI 建议（待确认）：${advice?.recommendation||"请根据项目实际情况补充。"}\n建议理由：${advice?.rationale||"这项信息会影响问卷结构与追问深度。"}\n\n请直接回答，或回复“采用建议”。`});render();return;
  }
  state.messages.push({role:"assistant",text:"所有已识别缺口都已回答。正在进行最后一次 AI 完整性检查，通常需要 20–70 秒…"});render();
  try{
    const ready=await questionnaireGate();
    if(ready){state.messages.push({role:"assistant",text:"必要信息已经满足。现在可以生成问卷大纲；我会先给结构和研究阶段，不会直接跳到浅层问题。"});render()}
  }catch(error){
    state.messages.push({role:"assistant",text:`完整性检查未完成：${error.message}\n\n你的回答已经写入 Brief，没有丢失。请点击“生成问卷大纲”重新检查。`});render();
  }
}
async function generateReviewArtifact(){const a=state.project.latest_analysis;if(!a)throw new Error("请先生成 Evidence 与 Analysis");const md=`# Human Review\n\n> Status: Draft\n> Reviewer: TBC\n\n## 待审核 Evidence (${(a.evidence||[]).length})\n${(a.evidence||[]).map(e=>`- [ ] ${e.evidence_id}: “${e.quote}” - Accept / Edit / Reject`).join("\n")||"- 无"}\n\n## 待审核 Findings (${(a.findings||[]).length})\n${(a.findings||[]).map(f=>`- [ ] ${f.finding_id}: ${f.title}`).join("\n")||"- 无"}\n\n## 待审核 Insights (${(a.insights||[]).length})\n${(a.insights||[]).map(i=>`- [ ] ${i.insight_id}: ${i.title}`).join("\n")||"- 无"}\n\n## 审核意见\n- TBC\n`;state.folder="review";selectArtifact();await saveArtifact(md)}
function reviewTarget(text){if(/insight|洞察/i.test(text))return"Insight";if(/evidence|证据|引用/i.test(text))return"Evidence";if(/finding|发现|事实/i.test(text))return"Finding";if(/recommend|建议/i.test(text))return"Recommendation";if(/报告|交付|措辞|表达/i.test(text))return"Delivery wording";return"Current research artifact"}
async function applyReviewFeedback(text){const existing=(state.project.artifacts||[]).find(a=>a.kind==="human_review");const base=existing?.content||(state.project.latest_analysis?`# Human Review\n\n> Status: Draft\n\n## Review feedback\n`:`# Human Review\n\n> Status: Draft\n> Analysis: TBC\n\n## Review feedback\n`);const target=reviewTarget(text);const entry=`\n### Edit request · ${new Date().toLocaleString()}\n- Target: ${target}\n- Decision: Edit requested\n- Reviewer instruction: ${text}\n- Processing status: Pending AI revision / human confirmation\n`;state.folder="review";selectArtifact();await saveArtifact(base+entry);return target}
async function reviseCurrentArtifact(text){
  if(!state.artifact)throw new Error("当前没有可修改的 Artifact");
  const result=await api(`/api/projects/${state.project.id}/artifacts/revise`,{
    method:"POST",
    body:JSON.stringify({kind:state.artifact.kind,title:state.artifact.title,content:state.artifact.content,instruction:text})
  });
  const folder=state.folder;
  await openProject(state.project.id,folder);
  return result;
}
async function generateDeliveryArtifact(){const a=state.project.latest_analysis;if(!a)throw new Error("请先生成并审核结构化分析");const md=`# Structured Delivery\n\n> Status: AI-generated draft / Human approval required\n\n## Executive Summary\n${a.executive_summary||"TBC - 需要基于已审核 Finding 完成"}\n\n## Key Findings\n${(a.findings||[]).map(f=>`### ${f.title}\n${f.summary||f.description||""}\n\nEvidence: ${(f.evidence_ids||[]).join("、")}`).join("\n\n")||"- 无"}\n\n## Recommendations / Insights\n${(a.insights||[]).map(i=>`- ${i.title}: ${i.statement||i.summary||""}`).join("\n")||"- 无"}\n\n## Evidence Pack\n- Evidence count: ${(a.evidence||[]).length}\n- Review status: ${a.review_status||"TBC"}\n\n## Limitations\n${(a.limitations||[]).map(x=>`- ${x}`).join("\n")||"- TBC"}\n`;state.folder="delivery";selectArtifact();await saveArtifact(md)}
const baseRunChat=runChat;
runChat=async function(text){
  const isRevisionRequest=/修改|改成|调整|补充|删除|不要|不应|应该|希望|依然|仍然|不够|更[多好]|需要|root cause|措辞|重写|审核|意见/i.test(text);
  const isControlledGeneration=/^(根据背景资料总结项目|检查 Brief 还缺什么|先生成问卷大纲|根据确认的大纲生成具体问题|检查是否可以生成研究计划|生成结构化结果|从问卷答案提取 Evidence|生成 One-page Delivery|生成 Evidence Pack 目录|检查交付还缺什么)$/i.test(text.trim());
  if(/背景资料.*总结|总结项目|总结.*背景/.test(text)){
    state.messages.push({role:"user",text},{role:"assistant",text:"正在整理已确认信息、识别缺口，并为每个缺口生成问卷前工作建议…"});render();
    const result=await summarizeWithRecommendations();
    state.messages.push({role:"assistant",text:`运行完成\n\n已更新：Brief.md\n新增：问卷生成前的 AI 建议\n建议数量：${(result.suggested_information||[]).length}\n\n这些建议均标记为“待确认”，不会被当成项目事实。你可以直接告诉我哪条接受、修改或否决。`});render();return;
  }
  if(state.folder==="plan"&&state.pendingQuestionnaireGap){
    await saveQuestionnaireClarification(text);return;
  }
  if(state.folder==="plan"&&isControlledGeneration&&/问卷|研究计划/.test(text)){
    state.messages.push({role:"user",text},{role:"assistant",text:"正在执行问卷前 Research Readiness Check…"});render();
    try{if(!await questionnaireGate())return}catch(error){state.messages.push({role:"assistant",text:`准备度检查未完成：${error.message}\n\n请稍后点击同一按钮重试；已经保存的 Brief 和回答不会丢失。`});render();return}
    state.messages.push({role:"assistant",text:"准备度通过。正在从 Evidence Needed 生成主问题、Probe Tree 与完成标准…"});render();
    const questionnaire=await api(`/api/projects/${state.project.id}/questionnaire`,{method:"POST",body:"{}"});
    await saveArtifact(questionnaireMarkdown(questionnaire));
    state.messages.push({role:"assistant",text:`运行完成\n生成了：Research Plan.md\n证据准备度：已为 ${questionnaire.questions.length} 个主问题生成 Evidence Needed 与完成标准\n模式：${questionnaire.agent_mode}\n缺失信息：${(questionnaire.missing_information||[]).length} 项`});render();return;
  }
  if((state.folder==="responses"||state.folder==="evidence")&&/结构化|Evidence|Analysis|分析|提取/.test(text)){
    state.messages.push({role:"user",text},{role:"assistant",text:"正在从“问卷答案与原始数据”生成结构化 Evidence 与 Analysis…"});render();
    await analyzeResponses();state.messages.push({role:"assistant",text:`运行完成\n已更新："证据与分析"报告（${(state.project.latest_analysis?.insights||[]).length} 条 Insight）\n输入边界：仅问卷答案与 research_result 来源\n下一步：进入人工审核`});render();return;
  }
  if(state.folder==="review"||(state.artifact&&(isRevisionRequest||!isControlledGeneration))){
    state.messages.push({role:"user",text},{role:"assistant",text:"正在按你的意见修改当前文档，并保留审核记录…"});render();
    const originalFolder=state.folder;
    try{
      const result=await reviseCurrentArtifact(text);
      state.messages.push({role:"assistant",text:`修改完成\n\n已更新：${state.artifact?.title||"当前文档"}\n状态：AI revised · 待人工确认\n模型：${result.model||"Live AI"}\n修改摘要：${result.change_summary}\n\n完整新版本已写回左侧文档，可以继续手动修改或通过对话再改。`});render();
    }catch(error){
      state.folder=originalFolder;
      const target=await applyReviewFeedback(text);
      state.messages.push({role:"assistant",text:`修改要求已保存，但没有假装完成改写。\n\n记录位置：Human Review.md\n修改目标：${target}\n原因：${error.message}\n下一步：接通 Live AI 后重新执行这条意见。`});render();
    }
    return;
  }
  if(state.folder==="delivery"&&/交付|Delivery|Evidence Pack|报告/.test(text)){
    state.messages.push({role:"user",text},{role:"assistant",text:"正在生成 Delivery.md…"});render();
    await generateDeliveryArtifact();state.messages.push({role:"assistant",text:"运行完成\n生成了：Delivery.md\n状态：AI-generated draft\n未生成：Approved 交付\n原因：尚需 Human Review"});render();return;
  }
  return baseRunChat(text);
};
function bind(){$("#home-link")?.addEventListener("click",e=>{e.preventDefault();state.view="portfolio";render()});$("#back-projects")?.addEventListener("click",()=>{state.view="portfolio";render()});$("#new-project")?.addEventListener("click",()=>{state.view="new";render()});$("#cancel-new")?.addEventListener("click",()=>{state.view="portfolio";render()});$$('[data-project]').forEach(x=>x.addEventListener("click",()=>openProject(x.dataset.project)));$$('[data-folder]').forEach(x=>x.addEventListener("click",()=>{state.folder=x.dataset.folder;state.documentMode="preview";state.editingQuestionIndex=null;selectArtifact();render()}));$("#toggle-document-mode")?.addEventListener("click",()=>{state.documentMode=state.documentMode==="edit"?"preview":"edit";render()});$("#new-project-form")?.addEventListener("submit",async e=>{e.preventDefault();const d=new FormData(e.target);const p=await api("/api/projects",{method:"POST",body:JSON.stringify({name:d.get("name"),research_goal:d.get("goal"),research_questions:[d.get("question")],target_users:"",language:"zh-CN"})});await loadProjects();await openProject(p.id)});$("#save-artifact")?.addEventListener("click",async()=>{try{await saveArtifact($("#artifact-editor").value);state.documentMode="preview";render()}catch(e){toast(e.message)}});$("#generate-analysis")?.addEventListener("click",()=>analyzeResponses().catch(e=>toast(e.message)));$("#analyze-responses")?.addEventListener("click",()=>analyzeResponses().catch(e=>toast(e.message)));$("#upload-source")?.addEventListener("click",()=>{const files=[...$("#source-files").files];if(!files.length)return toast("请先选择文件");upload($("#upload-source").dataset.category,files).catch(e=>toast(e.message))});$$('[data-classify]').forEach(x=>x.addEventListener("change",async()=>{await api(`/api/projects/${state.project.id}/sources/${x.dataset.classify}`,{method:"POST",body:JSON.stringify({category:x.value})});await openProject(state.project.id,state.folder)}));$$('[data-delete]').forEach(x=>x.addEventListener("click",async()=>{if(!confirm(`${x.getAttribute("aria-label")}？此操作无法撤销。`))return;await api(`/api/projects/${state.project.id}/sources/${x.dataset.delete}`,{method:"DELETE"});await openProject(state.project.id,state.folder)}));$$('[data-prompt]').forEach(x=>x.addEventListener("click",()=>{$("#chat-input").value=x.dataset.prompt}));$("#send-chat")?.addEventListener("click",()=>{const t=$("#chat-input").value.trim();if(!t)return;runChat(t).catch(e=>toast(e.message))});$("#chat-files")?.addEventListener("change",e=>{const category=state.folder==="responses"?"research_result":"project_context";upload(category,[...e.target.files]).catch(x=>toast(x.message))});$$('[data-edit-question]').forEach(x=>x.addEventListener("click",()=>{state.editingQuestionIndex=Number(x.dataset.editQuestion);render()}));$$('[data-cancel-question]').forEach(x=>x.addEventListener("click",()=>{state.editingQuestionIndex=null;render()}));$$('[data-save-question]').forEach(x=>x.addEventListener("click",()=>saveQuestionBlockEdit(Number(x.dataset.saveQuestion)).catch(e=>toast(e.message))));$$('[data-regenerate-stale]').forEach(x=>x.addEventListener("click",()=>{const folder=x.dataset.regenerateStale;const action=folder==="plan"?regeneratePlan:folder==="evidence"?analyzeResponses:folder==="delivery"?generateDeliveryArtifact:null;if(action)action().catch(e=>toast(e.message))}));$("#save-gap-form")?.addEventListener("click",()=>saveGapForm().catch(e=>toast(e.message)))}
document.addEventListener("mouseup",()=>{setTimeout(handleSelectionChange,0)});
document.addEventListener("mousedown",event=>{
  const toolbar=document.getElementById("selection-toolbar");
  if(toolbar&&!toolbar.hidden&&!toolbar.contains(event.target))toolbar.hidden=true;
});
document.addEventListener("click",async event=>{
  const artifactButton=event.target.closest("[data-open-artifact]");
  if(artifactButton){
    const match=Object.entries(artifactKinds).find(([,meta])=>meta[1]===artifactButton.dataset.openArtifact);
    if(match){state.folder=match[0];state.documentMode="preview";selectArtifact();render()}
    return;
  }
  const button=event.target.closest("[data-delete-project]");if(!button)return;
  const name=button.dataset.projectName;
  if(!confirm(`删除项目“${name}”？该项目的资料、问卷、分析和文档都会永久删除。`))return;
  try{
    await api(`/api/projects/${button.dataset.deleteProject}`,{method:"DELETE"});
    localStorage.removeItem(chatKey(button.dataset.deleteProject));
    await loadProjects();render();toast(`项目“${name}”已删除`);
  }catch(error){toast(`删除失败：${error.message}`)}
});
loadProjects().then(render).catch(e=>{$("#app").innerHTML=`<div class="empty">工作台加载失败：${esc(e.message)}</div>`});
