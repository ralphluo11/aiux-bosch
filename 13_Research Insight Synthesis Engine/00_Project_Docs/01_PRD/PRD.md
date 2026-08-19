# Research Insight Synthesis Engine · Product PRD (Alignment & Approval)

**Product name:** Research Insight Synthesis Engine  
**Project ID:** 13 (UXGS Internal)  
**Document role:** **Approval, resourcing, stage decisions** (parent PRD)  
**Execution doc:** `EXECUTION_PRD.md` (design / engineering / Vertical Alpha acceptance)

> **Version:** V2.1｜**Date:** 2026-08-11｜**Status:** Draft — Vertical Alpha scope updated

> **Formal scope decision (2026-08-11):** The current track is `Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery`, using approved existing recordings, transcripts, and project materials. Real-time AI interviewing, Participant Link, Streaming ASR, live adaptive probing, and dual-client Live View are excluded from Alpha and the current MVP. They require a separate post-MVP Go / No-go and remain `Post-MVP TBC`. Any remaining real-time interview description in this parent PRD is a long-term candidate, not a current Release commitment. V2.0 `EXECUTION_PRD.md` controls acceptance.

---

## 01 | Project Overview

| Item | Content |
|------|---------|
| **Product name** | Research Insight Synthesis Engine |
| **Product type** | Enterprise AI Research Intelligence / Evidence Synthesis product |
| **Stage** | Vertical Alpha for evidence synthesis and reviewed delivery from existing research materials |
| **Core flow** | **Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery** |
| **Product owners** | TBC (Data lead + UX lead jointly drive customer & data-info collection) |
| **Audience** | Business Sponsor, Data / UX leads, Eng, pilot stakeholders |

### Near-term milestones (POC per this doc; adjustable post-Kennel)

| Milestone | Date (approx.) | Notes |
|-----------|----------------|-------|
| Customer definition + data-info collection | **2026-07-31** | Data + UX leads |
| Kennel alignment | **2026-07-31** | Schedule anchor |
| **POC end** | **~2026-08-05** | **~1.5 weeks** |
| Phase 1 kickoff | Post-Kennel | See roadmap |

### Document set

| Document | Purpose |
|----------|---------|
| **This PRD** | Approval, alignment, scope & roadmap decisions |
| **EXECUTION_PRD.md** | Pages, APIs, acceptance, gates, data model |
| `WIP/` | POC demo, pilot notes, customer & data collection |

---

## 02 | Background & Objectives

### 2.1 Problems

- Outlines depend on individual craft; **expert structures and question banks** are hard to reuse  
- Interview, transcription, analysis, and reporting sit in separate tools  
- Generic AI can probe dynamically but lacks **product / engineering mechanism** judgment  
- Internal, external, and respondent data lack **traceable linkage**  
- Summaries weakly align to **Bosch context**; external SaaS cannot deeply connect internal data  

### 2.2 Product goals

1. **Evidence-led loop:** approved materials move from registration to analysis and reviewed delivery.  
2. **Human accountable:** AI proposes Evidence, Findings, and Recommendations; humans review and approve with a retained diff.  
3. **Reusable expert structure:** methods, Artifact Contracts, and Benchmarks become versioned assets.  
4. **Dual Track:** Existing Feature work produces Findings / Recommendations; Proposal work produces Assumptions / Opportunities / Validation Plans.  
5. **Post-MVP decision:** real-time AI interviewing can start only after a separate Go / No-go following MVP.

### 2.3 Product principles

1. **End-to-end first** — no broken research chain.  
2. **Human in control** — researchers keep final judgment.  
3. **Knowledge grounded** — knowledge assists questions/summary, never fabricates respondent answers.  
4. **Evidence traceable** — conclusions and enhanced probes trace to sources.  
5. **Neutral by design** — internal hypotheses are not stated as facts to participants.  
6. **Modular outputs** — Guide, Transcript, Evidence, Theme, Insight, Report stored and reusable.

### 2.4 Success criteria (decision level)

**Vertical Alpha:**

- Freeze refrigerator Project Brief, Source Inventory, Ground Truth, and Benchmark Rubric;
- Use approved de-identified existing transcripts, notes, reports, and project materials;
- Produce located Evidence / Claims and synthesize Findings / Recommendations;
- Retain AI Raw / Human Final through Accept / Edit / Reject;
- Deliver Human View, Machine View, Evidence Pack, and Run Manifest;
- Use Holdout Reference to evaluate accuracy, omissions, edits, and time.

**Full-product direction:**

- Multi-project, permissions, ≥1 real internal data source  
- Configurable **Bosch context** for outline and summary  
- Knowledge base, cross-project reuse, multi-BU  

---

## 03 | Core Value Proposition (Dual USP)

### USP-A | Data layer: internal ↔ external linkage + Bosch context

> Link Bosch internal data with externally collected data; apply **Bosch-context tuning** in **outline generation** and **summary reports** that external tools cannot match.

| Stage | Outline | Summary |
|-------|---------|---------|
| POC | Expert structure + DB; Connector **stub** | Basic summary + quote traceability |
| Full product | Internal/external sources in Guide; configurable context rules | Bosch-context tone, frame, evidence chain |

### USP-B | Probe layer: mechanism-aware depth

> Generic AI knows *how* to probe; our AI knows *why* a probe matters and which **product / design hypothesis** the next question should test.

```text
Engineering / Product Mechanism
→ User-observable Signal
→ Candidate Hypothesis
→ Discriminating Evidence
→ Neutral Customer-facing Probe
```

| Stage | Capability |
|-------|------------|
| POC | Generic adaptive probe **Must**; Knowledge Pack + mechanism-aware probe **Stretch** |
| Full product | Knowledge Cards, RAG, Guardrail, Research Memory systematized |

**Non-goals:** “Upload files + plain RAG” alone is not the differentiator; unreviewed AI conclusions are not enterprise facts.

---

## 04 | Users & Customer

### 4.1 Customer status

| Item | Status |
|------|--------|
| Pilot customer / Sponsor | **Being defined** — lock + data-info by **2026-07-31** |
| Owners | Data + UX leads |
| POC strategy | **Generic scenario** until customer is locked |

### 4.2 Roles

| Role | Value |
|------|-------|
| **UX Researcher / Research Lead** | Create project, approve materials, review Evidence / Findings, approve delivery |
| **Participant** | Not a direct Alpha user; approved de-identified transcripts may be Sources. Live participation is Post-MVP TBC |
| **Product / Engineering Expert** | Review Knowledge Cards, mechanisms, hypotheses (full product / POC stretch) |
| **Data / Knowledge Owner** | Sources, permissions, sync (Phase 1+) |
| **Business Reader** | Consume summaries and evidence |
| **System Admin** | Workspace, roles, compliance (Phase 2) |

---

## 05 | End-to-end experience

```text
Project Brief → Source Registry → Evidence / Claim
→ Finding / Recommendation → Human Review
→ Structured Delivery → Benchmark Evaluation
```

### 5.1 Project Brief and Research Plan

Define the business decision, research questions, users, boundaries, materials, data level, delivery, and success criteria. Current Alpha uses existing research materials and does not create a Participant Link.

### 5.2 Real-time AI interview (Post-MVP TBC)

Excluded from Alpha and the current MVP. Reconsider only after MVP based on customer need, privacy and consent, ASR quality, real-time cost, and team capacity.

### 5.3 Summary report

POC: single-session themes, key points, quotes, basic export.  
Full product: evidence chain, Bosch context, multi-session aggregation, template library.

### 5.4 Evidence chain (full-product target)

```text
Interview Turn → Transcript → Evidence → Theme → Insight → Report
```

---

## 06 | Scope & Roadmap

### 6.1 Vertical Alpha — **current authoritative scope**

| In scope | Out of scope |
|----------|--------------|
| Refrigerator Brief, Source Inventory, Holdout Ground Truth | Real-time AI interview, Participant Link, ASR, Live View |
| Approved de-identified transcripts, notes, reports, project materials | Production internal database connection |
| Evidence / Claim source location and validation | Multi-project / multi-BU |
| Finding / Recommendation and Human Review | SSO / full RBAC / full audit platform |
| Human View, Machine View, Evidence Pack, Run Manifest | Owner Portal / Dashboard / Marketplace |
| Offline Benchmark Evaluation | Formal PPT / Word file generation |

**Minimum acceptance loop:**  
1 approved Brief → 1 de-identified input set → Evidence / Findings → Human Review → 1 structured delivery + Benchmark result.

> Feature-level acceptance, gates, P0 list: **EXECUTION_PRD.md**.

### 6.2 Phase 1 — first shippable version

- Multi-project management & permissions  
- **≥1** real internal data source + curated external sources  
- USP-A: Bosch-context rules for outline & summary  
- USP-B: Knowledge Cards, light RAG, Guardrail, stable mechanism-aware probes  
- Evidence review workspace, stronger export  
- Multi Study / Session within one BU  

### 6.3 Phase 2 — enterprise

- Knowledge base, cross-project Research Memory  
- Multi-BU tenancy, SSO, audit, data governance  
- Deep internal–external correlation (full USP-A)  
- Template library, evaluation, ops dashboard  

### 6.4 Phase 3 (vision)

Cross-product / market signal correlation, trends & knowledge gaps, Synthetic User evaluated separately.

---

## 07 | Capability blueprint (full product · strategic)

| Module | Description | POC | Phase 1 |
|--------|-------------|-----|---------|
| Project / Study mgmt | Goals, hypotheses, status | Single Study | Multi-project |
| Research Plan | Brief, method, scope, Gates | ✅ | ✅ |
| Participant Link & Consent | Link, consent, device check | Post-MVP TBC | Post-MVP TBC |
| Real-Time Voice + ASR | Voice, transcript, turn submit | Post-MVP TBC | Post-MVP TBC |
| Interview Orchestrator | Coverage, adaptation, fallback | Post-MVP TBC | Post-MVP TBC |
| Researcher Live View | Monitor, accept / override | Post-MVP TBC | Post-MVP TBC |
| Generic Adaptive Probe | Probe without knowledge hit | Post-MVP TBC | Post-MVP TBC |
| Domain Intelligence | Internal/external, Connector | Stub | ≥1 live source |
| Knowledge Cards + RAG | Mechanism–signal–hypothesis–probe | Stretch | ✅ |
| Question Guardrail | Neutrality, confidentiality | Lite | ✅ |
| Evidence / Insight Pipeline | Theme, Insight, review | Lite | ✅ |
| Report Generation | Summary, export | Basic | Enhanced |
| Research Memory | Cross-project reuse | — | Phase 2 |
| Admin / Governance | SSO, RBAC, audit | — | Phase 2 |

---

## 08 | Success metrics (approval level)

| Category | Direction (full product) |
|----------|----------------------------|
| Efficiency | Shorter time from interview to reportable output |
| Quality | Insight evidence linkage ≥95%; researcher acceptance ≥80% |
| Experience | Session completion; acceptable next-question latency |
| USP | Traceable knowledge probes; mechanism-aware beats generic in blind review; zero high-risk leading/leak |
| Compliance | Classification, AI channel, retention confirmed before Phase 1 |

POC thresholds: **EXECUTION_PRD.md** § Acceptance.

---

## 09 | Risks & responses (summary)

| Risk | Response |
|------|----------|
| Engineering knowledge → leading questions | Hypotheses internal only; Guardrail + neutral wording |
| Stale / wrong-model content | Metadata filter, validity, review status |
| AI hallucination in summary | Evidence-first; quotes must map to Turns |
| Knowledge overload | Coverage map, probe budget, top-k |
| POC scope creep | Execution PRD Must / Stretch / Won't |
| Customer undefined | Generic POC + Connector stub; bind scenario after 7/31 |

---

## 10 | RASIC

**RASIC:** R Responsible · A Accountable · S Support · I Informed · C Consulted  

**Roles:** UX · Data · PM (dual-hat TBC) · Res · **Eng** (FE+BE+AI, one team) · Biz · IT/Sec · Ops (full product)

### 10.1 Customer definition + POC

| Role | Customer def | Data info | POC scope | Outline | Live interview | Summary | Data interface | Kennel | POC demo |
|------|--------------|-----------|-----------|---------|----------------|---------|----------------|--------|----------|
| UX | R | C | A/R | A/R | C | A/C | I | R | A |
| Data | R | A/R | C | S | I | C | A/C | R | S |
| PM | C | C | R | C | C | C | C | A | R |
| Res | C | C | C | C | C | C | I | I | S |
| Eng | I | C | C | R | A/R | R | R | S | R |
| Biz | A/C | C | I | I | I | I | I | I | C/I |
| IT/Sec | I | I | I | I | C | I | C | I | I |

### 10.2 Phase 1

| Role | Roadmap | Multi-project | E2E | Source select | Integration | Bosch context | Evidence | Report | Compliance | Launch | Rollout |
|------|---------|---------------|-----|---------------|-------------|---------------|----------|--------|------------|--------|---------|
| UX | C | A/R | A/R | C | I | A/R | A/R | A/C | I | I | R |
| Data | C | C | S | A/R | A/C | R | C | C | C | C | S |
| PM | A/R | R | R | C | C | C | C | R | C | A | A/R |
| Res | C | C | C | C | I | C | C | C | I | I | R |
| Eng | C | R | R | R | R | R | R | R | S | S | S |
| Biz | C | C | C | C | C | C | I | C | C | C | A/C |
| IT/Sec | I | C | I | C | C | C | I | I | A/R | C | I |
| Ops | I | I | I | I | S | I | I | I | S | R | S |

### 10.3 Phase 2

| Role | KB strategy | KB build | Multi-BU | Internal–external | Templates | Multi-BU ops |
|------|-------------|----------|----------|---------------------|-----------|--------------|
| UX | C | C | C | C | A/R | S |
| Data | A/R | A/C | C | A/R | S | S |
| PM | R | C | A/R | R | R | A |
| Res | C | C | I | C | C | C |
| Eng | R | R | R | R | R | S |
| Biz | C | C | C | C | C | R |
| IT/Sec | C | C | A/C | C | I | C |
| Ops | I | S | R | I | R | A/R |

---

## 11 | Open Items / TBC

| Item | Owner | Due |
|------|-------|-----|
| Pilot customer & Sponsor | Data + UX | 2026-07-31 |
| Data-info list & conclusions | Data + UX | 2026-07-31 |
| Internal data source selection | After customer def | Post-Kennel |
| Compliance (classification, AI, hosting) | IT/Sec + team | Before Phase 1 |
| PM / Ops separate? Final A for customer? | Team | TBC |
| Schedule tweak post-Kennel | Team | After 2026-07-31 |

---

## 12 | One-line positioning

> **Research Insight Synthesis Engine is an enterprise Research Intelligence capability that turns approved existing research materials into traceable Evidence, reviewed Findings, Recommendations, and structured delivery. Real-time AI interviewing is Post-MVP TBC.**

---

## Appendix | Document Control

| Field | Value |
|-------|-------|
| **Document Version** | 2.1 |
| **Last Updated** | 2026-08-11 |
| **Status** | Draft |
| **Languages** | `PRD.md` · `PRD_CN.md` · `PRD_bilingual.html` |
| **Execution** | `EXECUTION_PRD.md` · `EXECUTION_PRD_CN.md` |
