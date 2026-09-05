# Research Memory V1

**Requirement 13 -- Persistent Research Memory.** The smallest persistent
system that lets a researcher's *thinking* about a discovery accumulate
across time, not just the underlying data. Downstream and additive to
Requirement 11 (Research Corpus) and Requirement 12 (Research Discovery,
External Novelty Validation). Never modifies canonical CyberBriefs, Research
Corpus output, or Research Discovery output -- only reads them, by stable
reference.

Grounded in two completed Requirement 13 functional capability tests (a
Discovery Candidate investigation, and a 3-day incremental research
reflection exercise) and a design report that tested, rather than assumed,
what needed to persist.

## The two objects

**Research Thread** -- a durable, minimal identity for an idea worth
tracking across time (e.g. "Structural Shift <-> Levers"). A thread has a
label, a creation date/author, and a list of *evidence anchors* -- stable
references to existing Requirement 11/12 objects (an observation, a
Discovery Candidate, a longitudinal claim, an External Novelty Assessment,
or a raw canonical item not yet processed into the Research Corpus). A
thread carries **no** mutable interpretation, confidence score, article
status, model status, or graphic object. Its evidence-anchor list may only
grow -- existing anchors are never removed or rewritten.

**Research Memory Event** -- an append-only, immutable, dated record of how
evidence changed understanding of one or more threads. This is the actual
unit of research thought. New understanding is always a *new* event;
nothing is ever edited in place. "Current state" is never stored -- it is
always derived by reading the most recently *recorded* state-affecting
event for a thread.

Nothing else is persisted. Research questions, counterexamples, competing
explanations, uncertainty, and next-evidence needs are **not** separate
objects -- they live as plain narrative and evidence references inside
events (see event types below). This was a deliberate result of the V1
design test, not an oversight: each of those was checked against "does this
need its own persistent object," and none did.

## Append-only, structurally enforced

Events are stored one JSON object per line in `events.jsonl`. Appending is
the only supported write: the implementation reads the existing file,
computes the new content, and **refuses to write** unless the new content
is a strict superset of the old (the old content must be an exact prefix of
the new). Re-appending a record whose `event_id` already exists is
rejected -- events are content-addressed (`event_id` is a deterministic
hash of the event's own fields), so this also makes re-running a seeding
script safe and idempotent. Every write goes through a temp-file-then-
`os.replace` sequence, so a crash mid-write can never leave a corrupted or
partially-written file -- either the prior file survives untouched, or the
fully-written new file is installed.

Threads follow the same discipline: creation refuses to overwrite an
existing thread file, and the only permitted later change -- appending to
`evidence_anchors` -- is only written if the new list strictly extends the
old one.

## Event types

An open, non-bureaucratic vocabulary, each one directly demonstrated by the
two prior capability tests: `NOTICED`, `REINFORCED`, `CONTRADICTED`,
`COUNTEREXAMPLE_ADDED`, `QUESTION_ADDED`, `QUESTION_RESOLVED`,
`INTERPRETATION_REVISED`, `SPLIT`, `NEXT_EVIDENCE_IDENTIFIED`,
`NEXT_EVIDENCE_SATISFIED`, `STATE_CHANGED`, `MODEL_POTENTIAL_FLAGGED`,
`GRAPHIC_POTENTIAL_FLAGGED`, `DORMANT_MARKED`, `SUPERSEDED`, `CLOSED`.

Questions and next-evidence needs are represented by an "opening" event
(`QUESTION_ADDED`, `NEXT_EVIDENCE_IDENTIFIED`) and, later, a "closing" event
that references the opening event's id (`QUESTION_RESOLVED`,
`NEXT_EVIDENCE_SATISFIED`). Open/unresolved status is *derived* --
anything opened that no later event on the thread has closed is still open.
Competing explanations and uncertainty are plain structured prose inside an
`INTERPRETATION_REVISED` event's narrative; nothing forces a winning
explanation.

`MODEL_POTENTIAL_FLAGGED` / `GRAPHIC_POTENTIAL_FLAGGED` mean only "there may
be conceptual structure here worth watching" -- they create no model, no
graphic, no framework, no name, and the system is designed to work
correctly with zero of them for long periods.

## Evidence lineage

Every evidence reference is validated and resolved against the existing,
unmodified Requirement 11/12 lineage -- `research_discovery/external_novelty.py`'s
own helpers (`load_observations`, `find_candidate`, `resolve_evidence`,
`resolve_candidate_trace`, `read_assessment`) are reused directly, plus two
small read-only additions here for longitudinal claims and raw canonical
items that haven't yet been processed into the Research Corpus. Nothing in
this module duplicates Requirement 11/12 content -- it only reads it, by
reference, on demand. There is no second, parallel evidence graph.

A safeguard checks `case_continuity.json` before allowing a
`REINFORCED`/`CONTRADICTED`/`COUNTEREXAMPLE_ADDED` event to cite two
`observation` references as independent evidence: if they're the same
underlying case, the write is rejected.

## AI / researcher provenance

Every event carries an `origin`: `researcher-authored` or
`ai-suggested-researcher-accepted`. Nothing is ever silently attributed to
the researcher if it originated as an AI suggestion. `suggest_thread_relevance()`
is the only AI-facing entry point that produces candidate event content --
it is a pure function that returns suggestions and **persists nothing**; a
suggestion only becomes a real event if something (a person, in practice)
calls `append_event(..., origin="ai-suggested-researcher-accepted")`
explicitly.

## One memory, three modes

`investigate(thread_id)`, `catch_up(window_start, window_end)`, and
`suggest_thread_relevance(new_evidence_refs)` are the only three read
functions a Workbench would call for Investigation Mode, Reflection/
Catch-up Mode, and Daily Research Mode respectively -- all three read the
exact same `events.jsonl` and thread files. `catch_up()` deliberately
returns each affected thread's *full* history, not just events inside the
requested window, because the prior capability test showed that a
window-only catch-up misses connections to older memory (the Aug 31 Gryxa
event is outside any Sep 2-4 window but is essential context for the "AI as
accelerant" thread).

## What V1 does not do

No UI, no dashboard, no natural-language corpus query, no Writing Mode, no
article/model/graphic generation, no publishing/export, no collaboration,
no formal knowledge graph or causal graph, no confidence scoring, no
automatic thread promotion, no general-purpose notes system, and no
separate Question/Counterexample/Explanation/Uncertainty/Next-Evidence/
Hypothesis/Model/Graphic objects. `suggest_thread_relevance()` is a small,
explicitly-labeled heuristic (tag/candidate-structure matching plus a
couple of keyword checks) -- not a natural-language interface, and it is
not claimed to be complete (see "Known limitations" below).

## Files

- `research_memory.py` -- the two objects, evidence resolution, and the
  three mode-support functions.
- `seed_v1_research_memory.py` -- populates the smallest legitimate V1
  example set, using only real material from the two completed Requirement
  13 capability tests (three threads: Structural Shift <-> Levers;
  Incentives / Levers exclusivity; AI as accelerant). Idempotent.
- `acceptance_tests_research_memory.py` -- 30+ checks, run against an
  isolated temporary copy of the real data tree (never the live one) for
  every destructive/rejection test, plus a small read-only check against
  the real, live seeded data.

Data lives under `CyberBrief/Data/research_workbench/` (`threads/*.json`,
`events.jsonl`), alongside `research_corpus/` and `research_discovery/`'s
own output directories, and is untracked by git in the same way those are.

## Known limitations

- `suggest_thread_relevance()` only detects relevance through a thread's
  `discovery_candidate` evidence anchors and simple keyword matching against
  open next-evidence narratives. It does **not** detect relevance for
  threads anchored only to a longitudinal claim or raw canonical item (e.g.
  it would not, on its own, have connected Unit 42 to the pre-existing
  Gryxa claim the way a researcher did by reasoning) -- that kind of
  connection remains a human (or AI-assisted-in-conversation) judgment, not
  an automatic capability of this module.
- Evidence references to a longitudinal claim are matched by exact
  `claim_text` (no stable id exists for claims in the current Requirement 11
  schema). This is a read-only lookup convenience in this module; it does
  not require or imply any change to Requirement 11.
- A future Discovery regeneration may formally confirm or reverse an
  interpretive event that anticipated the change (e.g. the "Incentives /
  Levers exclusivity" thread's `WEAKENING` state, if a future Discovery run
  drops that candidate entirely). No reconciliation between a future
  Discovery diff and this event log is built in V1 -- this is a known,
  unexercised design edge case, not a defect.
