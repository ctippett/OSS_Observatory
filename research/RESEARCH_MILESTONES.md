# OSS Observatory — Research Milestones

**Purpose:** This is an append-only record of significant intellectual and methodological milestones in the OSS Observatory. It is not a log of daily activity, implementation details, or working notes — those live elsewhere (production Run Records, workflow documents, working directories). An entry belongs here only when something materially changes the Observatory's research architecture, methodology, analytical models, or research capability. Entries are added, never edited or removed, once written.

---

## 2026-09-12

### 1. CyberBrief LLM Execution Contract v1

- Established a provider-neutral execution boundary for CyberBrief.
- Separated the CyberBrief research method from the LLM/runtime executing it.
- Claude/Cowork remains the designated production implementation.

### 2. Implementation A Certification

- Claude/Cowork was fully certified as `CyberBrief LLM Execution Contract v1, Implementation A`.
- `20260912` is the first production run demonstrating contract conformance.
- The Run Record successfully captured Provider, Model, and Execution environment.
- This establishes the stable production reference implementation for future provider comparisons.

### 3. CyberBrief Analytical Variance Framework (AVF)

- Canonized the analytical pipeline: Evidence → Selection → Classification → Interpretation → Longitudinal Meaning.
- Variance may enter at any stage of this pipeline.
- Core proposition: a durable analytical construct should remain meaningfully stable under changes in the execution engine, even when evidence discovery, selection, language, and local interpretation vary.
- AVF distinguishes Evidence Variance, Selection Variance, Classification Variance, Interpretive Variance, and Longitudinal Variance.
- AVF can evaluate both CyberBrief as an analytical system and individual constructs operating within it, including IAD, Half-Life, Structural Shift, longitudinal arcs, and future Models Ledger constructs.
- AVF defines a hypothesis and evaluation framework only. It does not yet establish cross-provider construct stability — no such evaluation has been run.

### 4. Dual Purpose of Alternate Providers

- Providers B, C, D, etc. have two explicit purposes:
  - Engineering: establish provider independence and remove any single LLM provider as a critical dependency.
  - Research: perturb the execution engine while holding the CyberBrief method substantially constant, then measure where analytical results vary and where higher-order constructs remain invariant.
- Alternate providers operate only in isolated shadow/comparison mode and may never write or promote production CyberBrief artifacts.
- The research question is not whether another model can reproduce Claude. It is whether CyberBrief and its analytical constructs remain stable when the execution engine changes.

---

## 2026-09-19

### 1. Two complementary temporal modes recognized

- CyberBrief operates in two temporal modes: unattended research continuity (scheduled production, independent of conversational participation) and attended research conversation (discussion of a brief, immediate or later).
- The two modes are complementary, not sequential dependencies — neither requires the other to occur on a given day.

### 2. Conversation recognized as CyberBrief's primary human-consumption interface

- The LLM conversation, not the TXT file, is CyberBrief's primary interface for human research engagement.
- Its value is in the intellectual affordances a static artifact cannot provide: read, notice, question, investigate, connect, reconsider, develop.
- This recognition does not diminish the TXT, canonical JSON, or CSV roll-up, which retain their existing purposes as the durable, non-conversational record of each run.

### 3. Three durable research records established

- The Observatory recognizes three durable research records: Evidence (what happened in the world), Analysis (what CyberBrief made of it), and Interaction (what happened when the researcher engaged with that analysis).
- Research conversations are the durable record of Interaction, preserved substantially intact rather than aggressively summarized.
- `OSS_Observatory/research_conversations/` was established as the durable storage location for this record.

### 4. Presentation and production recognized as temporally separable

- Discussing a brief may happen immediately after production or later, against an already-completed canonical run, without rerunning production or research.
- Provider independence was clarified to apply to the execution boundary, canonical research structure, and durable artifacts — not to a universal conversational UI; each certified provider presents its own execution in its own native environment.

### 5. AVF scope clarified: excludes researcher interaction

- AVF's boundary was clarified. AVF tracks analytical variance between independent CyberBrief executions across the existing pipeline — Evidence → Selection → Classification → Interpretation → Longitudinal Meaning — and its primary question remains where independent analyses began to diverge, how far that divergence propagated, and what remained analytically stable despite it.
- Researcher interaction is a different object from analytical execution variance. AVF is not extended to include interaction as another stage of this sequence, and no Interaction Variance Framework (IVF) is being created.
- Interaction is instead handled outside AVF: preserved generously through the research-conversation corpus (`research_conversations/`), and interpreted selectively only when a specific research question makes that useful.
- AVF will not track interaction scores, dependency graphs, provenance graphs, conversation matrices, or lineage tracking, and will not attempt to determine which provider produces better conversations, which provider originated an idea, whether an idea survived researcher interrogation, or whether an interaction should become a model.
- AVF's existing secondary research question — whether a durable analytical construct survives despite execution divergence — remains in scope, unchanged, as a secondary question within AVF's own boundary.

This entry documents a research-method and operating-model discovery. It does not claim that a new software subsystem was built.
