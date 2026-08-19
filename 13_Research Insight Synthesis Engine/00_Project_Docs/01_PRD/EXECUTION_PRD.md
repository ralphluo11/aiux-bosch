# Research Insight Synthesis Engine · Vertical Alpha Execution PRD

**Version:** V2.0  
**Date:** 2026-08-11  
**Status:** Ready for Alpha Planning  
**Document role:** Authoritative child PRD for current design, engineering, and Alpha acceptance  
**Parent PRD:** `PRD.md`  
**Integration specification:** `UXGS_Enterprise_Research_Platform_Spec_v0.2.docx`

> **Scope decision:** The current track does not include real-time AI interviews. Participant Link, Consent, Mic Check, Streaming ASR, live adaptive probing, researcher/participant real-time clients, and Live Override are all `Post-MVP TBC`. V1.0 clauses that treated these capabilities as POC Must requirements are superseded by this version.

---

## 1. What Alpha must prove

### Proposition A - Evidence-led vertical slice (Must)

> Can approved recordings, transcripts, and project materials pass through `Project Brief → Source → Evidence → Analysis → Human Review → Structured Delivery`, with critical conclusions traceable to source evidence?

### Proposition B - Benchmark testability (Must)

> Can the completed refrigerator research serve as a holdout Benchmark for factual accuracy, evidence location, critical omissions, human edits, and processing time without exposing reference answers to the Agent?

### Alpha does not prove

- Customer value of real-time AI interviewing or Voice Agents;
- Production concurrency, SLA, SSO, full RBAC, or disaster recovery;
- Production SharePoint or internal database integration;
- A complete Owner Portal, Operations Dashboard, Marketplace, or Credits;
- Automatic learning, model fine-tuning, or unreviewed formal delivery;
- Formal `.docx` / `.pptx` generation; Alpha may output structured content or Markdown / HTML.

---

## 2. Alpha inputs and data boundaries

### 2.1 Required inputs

- Approved refrigerator Project Brief;
- Source Inventory with owner, version, date, permission, and data classification;
- De-identified transcripts, research notes, reports, or other approved project materials;
- Holdout Ground Truth frozen by the Research Lead / Domain Expert;
- Benchmark Rubric and stopping conditions.

### 2.2 Data rules

- Unredacted names, contact details, recordings, and sensitive internal content must not enter unapproved services;
- Agent input and Holdout Reference must remain physically separate;
- Uncertain or unauthorized content is marked `TBC / Restricted`, never guessed;
- A Source is registered with permission and version before parsing or analysis;
- Humans approve Benchmark Ground Truth; the Agent does not create it.

---

## 3. Scope matrix

| Capability | Alpha handling | Priority |
|---|---|---|
| Project Brief | Decision, questions, users, scope, data level, delivery, success | **Must** |
| Source Registry | Owner, version, date, permission, parse status, checksum | **Must** |
| Document parsing | TXT / MD first; other formats per verified parser capability | **Must** |
| Evidence / Claim | Atomic claim, verbatim evidence, locator, type, confidence | **Must** |
| Existing Feature Analysis | Finding, severity, impact, evidence strength | **Must** |
| Recommendation | Linked to Finding; clearly separated from facts | **Must** |
| Human Review | Accept / Edit / Reject; retain AI Raw / Human Final and reason | **Must** |
| Structured Delivery | One-page content, Evidence Pack, machine-readable artifacts | **Must** |
| Run Manifest | Model, Prompt/Policy, Skill, Schema, inputs, timing | **Must** |
| Conflict / Gap Detection | Mark conflicts, duplicates, stale sources, and coverage gaps | **Should** |
| Minimal Skill Runtime | Record frozen Skill IDs/versions; no complete Portal | **Should** |
| Offline evaluation | Compare with Holdout and export results | **Must** |
| Proposal Track | Pilot only after the hydrogen peroxide Brief is complete | **Later** |
| Owner Portal / Dashboard | MVP or later | **Won't** |
| SharePoint / enterprise Connector | Pilot, subject to Bosch approval | **Won't** |
| Formal Word / PPT generation | Structured content is sufficient | **Won't** |
| Real-time AI interview flow | Separate Go / No-go after MVP | **Post-MVP TBC** |

---

## 4. End-to-end flow and Gates

| Gate | Activity | Pass condition | Accountable role |
|---|---|---|---|
| G0 Intake | Complete Brief and Track | Sponsor, decision, scope, materials, success criteria clear | Research Lead |
| G1 Data | Register Sources | Permission, data level, Owner, version, redaction confirmed | Project / Data Owner |
| G2 Benchmark | Freeze Holdout | Ground Truth, Rubric, sample unit, disputes confirmed | Research Lead + Domain Expert |
| G3 Evidence | Parse and extract Evidence / Claims | Critical Claims locate source text; unlocated content cannot be fact | Research Lead |
| G4 Synthesis | Produce Findings / Recommendations | Facts, inference, recommendation separated; omissions checked | Domain Reviewer |
| G5 Review | Human review and editing | AI Raw, Human Final, action, and reason saved | Research Lead |
| G6 Delivery | Lock output | Human View, Machine View, Evidence Pack, Run Manifest complete | Approver |

A failed Gate cannot be silently skipped. Return, correction, and rerun are allowed and must preserve history.

---

## 5. Minimum Artifact Contract

| Object | Minimum fields |
|---|---|
| `Project` | id, name, track, owner, scope, status, data_classification |
| `Brief` | decision, goals, research_questions, users, constraints, delivery, success |
| `Source` | id, title, owner, version, date, permission, checksum, parse_status |
| `Evidence` | id, source_id, locator, verbatim_text, context, access_scope |
| `Claim` | id, statement, claim_type, evidence_ids, confidence, review_status |
| `Finding` | id, statement, evidence_ids, impact, severity, confidence |
| `Recommendation` | id, finding_ids, proposal, rationale, status |
| `Review` | id, artifact_id, action, ai_raw, human_final, reason, reviewer, timestamp |
| `Run` | id, inputs, model, skill_versions, prompt_policy, schema_version, status |
| `Delivery` | id, audience, version, artifacts, permissions, approved_at |

A `fact` requires at least one valid Evidence link. A Recommendation cannot masquerade as a Finding. Unreviewed automated output cannot be Approved.

---

## 6. Initial Skills

Alpha should freeze only 4-6 Skills:

1. `validate-project-brief`
2. `ingest-and-register-source`
3. `extract-evidence-and-claims`
4. `detect-evidence-conflicts`
5. `analyze-existing-feature`
6. `generate-reviewed-delivery`

Each Skill minimally records ID, version, Owner, input, output, forbidden behavior, tests, and failure behavior. A complete Registry, approval UI, rollback, and retirement workflow belongs to MVP.

---

## 7. Alpha acceptance

### Must

- [ ] Refrigerator Brief, Source Inventory, and Holdout Ground Truth are approved;
- [ ] The Agent cannot access the Holdout Reference;
- [ ] At least one approved de-identified input set completes the full flow;
- [ ] Core Artifacts pass Schema validation;
- [ ] Every approved factual Claim opens the correct source and locator;
- [ ] Findings and Recommendations remain distinct;
- [ ] Review retains AI Raw, Human Final, action, and reason;
- [ ] Human View, Machine View, Evidence Pack, and Run Manifest are delivered;
- [ ] Evaluation records matches, omissions, errors, edits, and time;
- [ ] No unapproved sensitive production data is processed.

### Proposed metrics, to be approved after Benchmark freeze

| Metric | Initial proposal |
|---|---:|
| Schema validity | ≥99% |
| Critical Claim evidence location | ≥95% |
| Unsupported fact rate | ≤2%; high-risk facts 0 |
| Benchmark critical fact accuracy | ≥95% |
| Critical omission rate | ≤5% |
| Permission violations | 0 |
| Human time change | Establish a real baseline; do not pre-commit ROI |

These remain Proposed Targets until Ground Truth and the sample unit are approved. They are not achieved results.

---

## 8. Conditions for Governed MVP

1. Refrigerator Benchmark accuracy, omission, and evidence location meet approved thresholds;
2. Real users complete Alpha Review and record major edits and failures;
3. Artifact Schema, initial Skills, and Review Contract stabilize;
4. Data classification, retention, deletion, and approved model boundaries have Owners;
5. Backend, identity, security, and operations resources are confirmed.

After MVP completion, real-time AI interviewing receives a separate Go / No-go based on customer need, research value, privacy and consent, real-time cost, ASR quality, and team capacity. It does not automatically return as a Must.

---

## 9. Immediate actions

1. Create the refrigerator Benchmark material package;
2. Complete the Project Brief and Source Inventory;
3. Freeze Ground Truth and Rubric;
4. Confirm the minimum Artifact Schema;
5. Select 4-6 initial Skills;
6. Pilot-label 10-15 samples before expansion;
7. Run one de-identified Vertical Alpha input set.
