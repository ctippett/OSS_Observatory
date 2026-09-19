# CyberBrief LLM Execution Contract v1

**Status:** DRAFT — not yet adopted, not yet referenced by `cyberbrief_production_workflow.md`, not committed.
**Purpose:** Define the provider-neutral boundary for the *content-generation stage* of CyberBrief production — research through candidate JSON, TXT, and Run Record — the stage currently performed entirely by an interactive Claude/Cowork session. This contract does not change what that stage produces or how it behaves; it names the boundary so a second LLM provider or runtime could, in principle, satisfy it without touching Schema v1, the validator, or anything downstream of validation.
**Relationship to existing documents:** This contract does not supersede `cyberbrief_production_workflow.md`. The workflow document remains the authoritative *content* of what the content-generation stage must do (methodology, format, selection criteria, Schema v1 shape). This contract describes the *interface* around that content — its inputs, required capabilities, outputs, and handoff to the deterministic stages — so that interface is visible independent of which LLM is executing it.

---

## 1. Inputs

The content-generation stage requires exactly these inputs; nothing else about the caller's identity or environment should be load-bearing.

1. **Workflow/instructions** — the complete text of `OSS_Observatory/cyberbrief_production_workflow.md` at a known commit. This is the sole source of methodology, format, and schema-shape guidance; it must be read in full each run, not reconstructed from memory of a prior run (workflow §0).
2. **Execution date or retrospective date range** — a single `YYYY-MM-DD` for a daily run, or a `<start>_<end>` range for a retrospective covering one or more missed dates (workflow §2.7, §9). All dates are interpreted in the authoritative CyberBrief timezone, `America/Chicago` (see Section 7's timezone note) — a daily run's `YYYY-MM-DD` is the calendar date in that timezone, not UTC or the executing host's local time.
3. **Relevant prior state / trackers / canonical artifacts**, read-only:
   - For deduplication ("do not repeat an item unless a material update occurred," workflow §2.7): the immediately preceding canonical CyberBrief JSON, and any canonical artifact whose coverage period overlaps the current research window (e.g., a retrospective's range may overlap more than one prior canonical file). An ongoing story may be included again only when a material new development has occurred since the most recent canonical artifact that covered it — not on a fixed lookback depth beyond that overlap rule. This also serves gap detection against the prior run.
   - `CyberBrief/Briefs/MORNING_BRIEF.md`, for the existing archive index the run will append to.
   - `CyberBrief/Data/LongHalfLife/LongHalfLife_Tracker_May2026.xlsx`, for existing Structural Shift entries the run may extend (workflow §7).
   - Prior Run Records, only as needed to establish whether a gap exists and what range a retrospective must cover.
4. **Required configuration:**
   - Repository root path (the `OSS_Observatory` / `CyberBrief` sibling layout, workflow §9).
   - The current `OSS_Observatory` git commit hash, for the Run Record's `Workflow commit` field (workflow §12.2) — recorded as `unknown` if unavailable, never blocking the run.
   - `cyberbrief.schema.json` and `Canonical_CyberBrief_Schema_v1.md`, read-only, as the shape contract the candidate JSON must satisfy.

No API keys, model identifiers, or provider-specific configuration are contract inputs — those are implementation details of whichever runtime executes the stage (see Section 7 and the Implementation A / second-provider sections below).

---

## 2. Required capabilities

A runtime executing this stage must provide, at minimum:

1. **Web research / search** — genuine, iterative research capable of consulting the source universe (workflow §2.13) as a coverage baseline while discovering additional credible sources, applying the evidence-quality principle (§2.14: primary/authoritative preferred, secondary for discovery/context, corroboration when evidence is uncertain or disputed — not a mechanical two-source rule).
2. **File read/write** against the connected `DoGoodData` filesystem — reading the workflow, schema, and prior artifacts; writing the TXT brief, candidate JSON, and Run Record to their specified paths (workflow §9).
3. **Structured JSON generation** conforming exactly to Schema v1's shape (`additionalProperties: false` at both top level and within `iad_signal`, `breach_specifics`, `adversary_spotlight`, `micro_tracking`), including the `source_urls` array requirement (§2.16, §4.3) and the conditional shapes in §4.4–4.7 — produced independently from the TXT, not derived from it (§4.1: "not a rendering").
4. **Ability to follow the existing production workflow and schema as written instructions** — the runtime must be able to ingest a long, detailed natural-language/markdown specification and execute it faithfully across many interacting rules (selection criteria, conditional sections, explicit prohibitions), not just generate free-text prose. This is the capability most specific to an agentic LLM session and the hardest to substitute mechanically.

No capability beyond these four is required for the content-generation stage. Capabilities belonging to later stages (schema validation, CSV derivation, corpus/discovery/memory generation) are explicitly out of scope — see Section 4's "no modification of deterministic downstream logic" and Section 8.

---

## 3. Required outputs

Exactly three artifacts constitute the pre-validation generation stage's output, plus one conditional TXT-variant:

1. **TXT briefing** — `CyberBrief/Briefs/YYYYMMDD_cyberbrief.txt` (daily) or `CyberBrief/Briefs/<start>_<end>_cyberbrief_retrospective.txt` (retrospective), in the canonical section format (workflow §3.1): header, per-item entries, Adversary Spotlight (conditional), Micro-Tracking (conditional), Inflection Watch, Longitudinal Arcs, Daily Narrative, Strategic Insights, Industry Research Reference (conditional), end-of-brief marker.
2. **Candidate canonical JSON** — written to `CyberBrief/Data/.candidate/YYYYMMDD_cyberbrief.candidate.json` for a daily run, or `CyberBrief/Data/.candidate/<start>_<end>_cyberbrief.candidate.json` for a retrospective (never directly to the canonical path — workflow §4.9), independently constructed from the same research/synthesis as the TXT, not parsed or serialized from it. The retrospective candidate path is stated explicitly here because the workflow document's §4.9/§9 give the daily candidate pattern and the retrospective TXT/canonical-JSON/run-record patterns, but do not separately spell out the retrospective *candidate* filename — this contract fills that one naming gap by direct extension of the existing convention, without introducing a new one.
3. **Run Record** — `CyberBrief/Data/YYYYMMDD_run_record.md` (or the `<start>_<end>` retrospective form), created *before* research begins (workflow §12.2) and updated through the nine-stage checklist (§12.3) as the run proceeds, with an append-only Execution Notes section (§12.4) for any material event the checklist's single-valued stage fields cannot represent.

No other artifact belongs to this stage. The CSV roll-up, canonical JSON promotion, `MORNING_BRIEF.md` update, and Long Half-Life tracker update are downstream, deterministic, and gated behind validation (Section 5) — they are not part of what the content-generation stage itself produces, even though the same session currently goes on to perform them after validation succeeds.

---

## 4. Behavioral obligations

These are inherited directly from the workflow document, not new rules introduced by this contract:

- **Same-day / retrospective rules** — a daily run covers the current execution date; a retrospective run is triggered when a gap against the prior run is detected. A retrospective covers only missed, *completed* run periods — it never absorbs the current execution date's own observation, which is always produced as its own separate daily brief. For example: if the last successful daily run was September 8 and execution resumes September 11, the correct output is a September 9–10 retrospective *and* a separate September 11 daily run — not a September 9–11 retrospective. Principle: retrospectives repair history; they do not consume today's observation. The retrospective's missed range is covered in full in one run (never silently dropped) and is named/filed as `<start>_<end>_cyberbrief_retrospective` / `<start>_<end>_run_record.md` (§2.7, §9, §12.1); the current execution date's daily brief and Run Record follow the ordinary daily naming convention, produced separately in the same session.
- **Quiet-day / zero-item protocol** — the workflow specifies no forced minimum item count: "up to 6 significant developments... fewer is acceptable" (§2.7), and per focus area, "if none occurred today... state that explicitly rather than forcing inclusion" (§2.7). This floor extends, without contradiction, all the way to zero: a day on which no development meets the selection criteria (referent requirement, first-reported-in-24h, etc.) is a valid outcome, not a failure, and must never be resolved by relaxing selection criteria to manufacture an item. On such a day: (a) the candidate JSON is schema-valid with `"items": []` and `"signal_counts": {"structural_shift": 0, "policy_evolution": 0, "incident": 0}` — confirmed against `cyberbrief.schema.json`, which imposes no minimum on `items` and only `minimum: 0` on each `signal_counts` field, so this requires no schema change; (b) the TXT brief states plainly that no qualifying development occurred, rather than silently shipping a shorter-than-usual brief with no explanation, mirroring the existing per-focus-area "state explicitly" rule at the whole-brief level; (c) conditional top-level fields with nothing to report (`adversary_spotlight`, `micro_tracking`, `inflection_watch`) are `null`, consistent with their existing conditional-inclusion rules elsewhere in this contract; (d) the Run Record proceeds through all nine stages normally — a zero-item day is not itself a failure mode and must not be recorded as one.
- **No forced stories** — items require a concrete named referent (organization, project, foundation, government body, or adversary group); items without one are excluded regardless of count pressure (§2.7's "Referent requirement").
- **Structural-shift gate** — a Structural Shift classification requires a specific, observable action or decision by a named organization, project, or governing body; Positive Structural Signals qualify without an incident trigger, but the gate itself is not optional (§2.4).
- **Arc handling** — the four longitudinal arcs inform classification but are not a daily output requirement; the workflow explicitly states "do not force arc mapping" (§2.2). An item's `arc` field may be empty.
- **Source/provenance requirements** — every item's `source_urls` must hold ≥1 HTTP/HTTPS URL for evidence *materially used* to support the observation, not every URL encountered during research (§2.16); `source` remains the separate human-readable outlet field.
- **No modification of deterministic downstream logic** — the content-generation stage must never edit `cyberbrief.schema.json`, `Canonical_CyberBrief_Schema_v1.md`, `validators/cyberbrief_validator.py`, or any `research_corpus/` / `research_discovery/` / `research_workbench/` script, and must never weaken the schema to make a day's output pass (§4.8: "If a real day's research doesn't fit the schema, that's a validation failure to report... not a reason to loosen the contract").
- **Production designation & shadow-mode isolation** — only the single designated production implementation (today, Claude/Cowork) may write or promote canonical CyberBrief artifacts, update `MORNING_BRIEF.md`, or update the Long Half-Life tracker. Any second-provider or experimental implementation being evaluated alongside production must run in an isolated shadow/comparison mode, writing only to a provider-specific test location (analogous in spirit to the existing `.candidate/` staging path, but never the same path, and never the canonical path even after validation passes). A shadow/comparison run must never modify, overwrite, promote, or update production canonical artifacts, trackers, or research state, regardless of whether its own output validates successfully.

---

## 5. Validation handoff

1. The candidate JSON, once written, is validated by invoking the **existing, unmodified** `validators/cyberbrief_validator.py` against the candidate path — the same invocation regardless of which runtime produced the candidate (workflow §5).
2. **On success:** the candidate is promoted (copied/renamed) to the canonical path `CyberBrief/Data/YYYYMMDD_cyberbrief.json`; the Run Record's stage 4 is marked `PASS` and stage 5 `DONE` with the promoted path (§5.1, §12.5); the run proceeds to CSV, tracker updates, and presentation.
3. **On failure:** the runtime must report the validator's exact `Reason:` and `Location:` output verbatim; must not treat the run as successful; must not update `MORNING_BRIEF.md` or the Long Half-Life tracker; must not present the invalid candidate as canonical; must leave the invalid candidate file in place as evidence; must not touch any existing canonical JSON for that date; and must record stage 4 as `FAIL` with the verbatim reason/location, marking stages 5–8 `SKIPPED (validation failed)` (§5.2, §12.5). The TXT brief may still be presented on its own merits, with the run's incompleteness stated plainly (§5.2, §8).
4. **What the LLM must and must not do after validation:** after a passing validation, the same session (today; see Implementation A) continues to CSV generation, `MORNING_BRIEF.md`, and tracker updates per the workflow — but this contract does not require those steps be performed by the same runtime that generated the candidate. What every runtime must not do, regardless of outcome: it must never alter the validator's verdict, never re-run validation with a modified schema, and never write directly to a canonical path without going through the candidate-then-promote sequence.

---

## 6. Failure and recovery semantics

- **Research failure** (the runtime cannot complete adequate research for the date/range) — the run is not silently abandoned. The Run Record documents how far the run progressed (stage checklist) and Execution Notes captures the reason, so the gap is visible and recoverable as a retrospective on a later run, per the existing deduplication/gap-detection rule (§2.7).
- **Tool/search failure** (a research tool is unavailable or errors) — treated as a material execution event: logged in Execution Notes rather than silently worked around or omitted (§12.4's "any other execution event needed to reconstruct... how the run reached its final canonical state").
- **Malformed output** (candidate JSON is not valid JSON, or fails schema validation) — handled entirely by Section 5's validation handoff: reported verbatim, run marked incomplete, invalid candidate preserved as evidence, no silent repair or schema weakening.
- **Partial artifact generation** (e.g., TXT written but JSON generation fails before a candidate exists) — the Run Record's per-stage checklist makes this visible artifact-by-artifact (stage 2 `DONE`, stage 3 `SKIPPED (<reason>)` or left `PENDING` with the reason in Execution Notes); the run is not presented as complete.
- **Retrospective recovery** — any gap between the last successful canonical run and the current execution date is covered by a single retrospective run spanning the full *missed, completed* range, named and filed per §2.7/§9/§12.1, rather than by multiple silently-dropped days or by quietly starting fresh at the current date. Per Section 4's retrospective boundary rule, the current execution date itself is never included in that retrospective range — it is always produced as its own separate daily run in the same session, immediately following the retrospective.

In every failure mode, the Run Record is still written and preserved — it is not gated behind success (§12.8). This is the mechanism by which failure becomes visible from disk alone, regardless of which runtime executed the stage.

---

## 7. Provenance

Every run's Run Record must capture exactly six provenance fields, regardless of which runtime executes the run:

1. **Provider** — the organization/vendor supplying the LLM (e.g., `Anthropic`).
2. **Model** — the specific model identifier used for the run (e.g., `claude-sonnet-5`), not a family name or marketing label.
3. **Execution environment** — how the run was executed (e.g., `Cowork interactive session`, `scheduled task`, `standalone script`) plus, where available, a session or run identifier. No fixed enum is prescribed in this draft; for a shadow/comparison run under Section 4's production-designation rule, this field must also make clear that the run was non-production (e.g., `Cowork interactive session (shadow/comparison, non-production)`).
4. **Workflow version/commit** — the `OSS_Observatory` git commit hash at the time of the run. This is the existing `Workflow commit` field (§12.2); this contract does not rename it, only confirms it satisfies this provenance requirement.
5. **Schema version** — today, `cyberbrief.schema.json` has no independent version field or hash of its own (confirmed directly: its `title` is the static string "OSS Observatory Canonical CyberBrief Schema v1," with no `version` key). Because the schema is co-located with, and co-committed alongside, the workflow document in the same repository, the same `Workflow commit` value (item 4) currently also pins the schema's exact state. If the schema is ever versioned or committed independently of the workflow document, this field must be captured separately at that time — this draft does not require that split prematurely, since doing so today would describe a repository structure that does not yet exist.
6. **Run mode** — `Daily` or `Retrospective (<start>–<end>)`. This is the existing `Run type` field (§12.2/§12.9); this contract does not rename it, only confirms it satisfies this provenance requirement.

**Timezone note:** the authoritative CyberBrief timezone is `America/Chicago` (Section 1, Decision 2 in Section 9). All dates recorded in the Run Record — execution date, retrospective range boundaries, and the `Run started` timestamp's calendar date — are interpreted in this timezone rather than UTC or the executing host's default timezone. `America/Chicago` observes daylight saving time (CST/CDT); this is a named timezone, not a fixed offset, so the correct offset varies by calendar date and must be resolved accordingly rather than hardcoded.

**Implementation status:** the current Run Record template (§12.9) already captures fields 4 and 6 (`Workflow commit`, `Run type`). It has no fields for 1, 2, or 3 (`Provider`, `Model`, `Execution environment`), and field 5 (`Schema version`) is only implicitly true rather than explicitly written. Adding the three missing fields (and, optionally, making field 5 explicit) to the Run Record template in `cyberbrief_production_workflow.md` §12.9 is the concrete, minimal follow-up this contract identifies — but implementing it means editing the workflow document, which is out of scope for this hardening pass (this draft may only be revised here). This section records the requirement; it does not implement the template change.

---

## 8. Non-goals

- **Do not redesign the canonical schema.** Schema v1, `cyberbrief.schema.json`, and `Canonical_CyberBrief_Schema_v1.md` are out of scope for this contract and for any implementation of it.
- **Do not change current outputs.** This contract must produce identical TXT/JSON/Run-Record behavior to what the workflow document already specifies; it names an existing boundary, it does not move it.
- **Do not replace Claude.** Claude/Cowork remains the production runtime. This contract exists to describe the boundary Claude already sits behind, not to justify or schedule a provider swap.
- **Do not modify deterministic post-validation scripts.** `validators/cyberbrief_validator.py`, `research_corpus/`, `research_discovery/`, and `research_workbench/` are unaffected by, and unaware of, which runtime produced the candidate JSON they consume.
- **Do not let a second provider under evaluation touch production state.** Per Section 4's production-designation rule, an experimental or comparison implementation is out of scope for writing, promoting, or influencing any canonical artifact, tracker, or research-state file — its entire footprint must be confined to its own provider-specific test location.
- **Do not require a universal or provider-neutral conversational presentation.** Provider independence under this contract applies to the execution boundary, the canonical research structure, validation requirements, and the durable research artifacts (Section 3) — not to the conversational interface a provider uses to present or discuss its own completed execution. A certified provider may present and discuss its own execution in its own native conversational environment. Presentation differences across providers need not be normalized into a common UI, dashboard, or application layer.

---

## 9. Resolved decisions (previously listed as ambiguities)

The four ambiguities identified during hardening have been resolved by explicit production decisions. Each is stated here for traceability, cross-referenced to where it is now enforced elsewhere in this contract, and to the original ambiguity it replaces.

1. **Retrospective boundary (resolves former ambiguity 1).** A retrospective covers only missed, completed run periods. The current execution period is always produced as its own separate daily brief; a retrospective must never absorb it. Worked example: if the last successful daily run was September 8 and execution resumes September 11, the run produces a September 9–10 retrospective and a separate September 11 daily run. Principle: retrospectives repair history; they do not consume today's observation. Enforced in Section 4 ("Same-day / retrospective rules," "Production designation & shadow-mode isolation") and Section 6 ("Retrospective recovery"). **Historical note:** the real archived `CyberBrief/Data/20260909_20260911_cyberbrief_retrospective` artifact predates this decision and folds the execution day (September 11) into its range — it does not conform to this rule. This is a pre-contract historical exception, not something this contract requires retroactively fixing, and is noted here only for transparency.

2. **Timezone (resolves former ambiguity 2).** The authoritative CyberBrief timezone is `America/Chicago`. All execution dates, daily periods, retrospective range boundaries, and Run Record dates are interpreted in this timezone, including across its CST/CDT daylight-saving transitions — not a fixed UTC offset. Enforced in Section 1 (Input #2) and Section 7 (Provenance closing note).

3. **Deduplication window (resolves former ambiguity 3).** Duplicate-story checking inspects the immediately preceding canonical run and any canonical artifact whose coverage period overlaps the current research window — not a fixed lookback depth beyond that overlap. An ongoing story may be included again only when a material new development has occurred since the most recent canonical artifact that covered it. Enforced in Section 1 (Input #3).

4. **Concurrent/provider execution (resolves former ambiguity 4).** Only the single designated production implementation may write or promote canonical CyberBrief artifacts, trackers, or research state. Any second-provider or experimental implementation must run in isolated shadow/comparison mode, writing only to a provider-specific test location, and must never modify, overwrite, promote, or update production canonical artifacts, trackers, or research state — regardless of whether its own output validates. Enforced in Section 4 ("Production designation & shadow-mode isolation") and Section 8 ("Do not let a second provider under evaluation touch production state").

With all four resolved, no known ambiguity remains in this contract that would allow two compliant providers to produce structurally or semantically incompatible artifacts for the same input. Any *new* ambiguity surfaced by an actual second-provider implementation attempt would be a fresh finding, not a reopening of these four.

---

## Implementation A: current Claude/Cowork production mapped onto this contract

| Contract section | Current Claude/Cowork implementation |
|---|---|
| Inputs | Delivered by the device bridge: Claude reads `cyberbrief_production_workflow.md`, prior canonical JSON, `MORNING_BRIEF.md`, and the tracker directly from the connected `DoGoodData` folder via file tools, inside an interactive Cowork session (scheduled or manual). |
| Web research/search | Claude's native web search tool, used iteratively per §2.13–2.14. |
| File read/write | Claude's native Read/Write/Edit tools (or the device-bridge equivalents), operating directly on the connected filesystem. |
| Structured JSON generation | Claude authors the candidate JSON by hand, from its own synthesis of the research — no separate JSON-generation call or library. |
| Follow the workflow as instructions | Claude reads the full markdown file each run and executes it as natural-language instructions — this *is* the capability described in Section 2.4; no separate interpretation layer exists. |
| Outputs (TXT, candidate JSON, Run Record) | All three are written by Claude directly, via file tools, to their specified paths, in the same session. |
| Validation handoff | Claude invokes `cyberbrief_validator.py` itself (via a shell tool) and reads its stdout/exit code directly. |
| Failure/recovery | Claude updates the Run Record's stage checklist and Execution Notes by hand, in the same session, as it discovers gaps or failures. |
| Provenance | Partially implicit: `Workflow commit` and `Run type` are captured today (§12.2), satisfying fields 4 and 6 of Section 7. `Provider`, `Model`, and `Execution environment` (fields 1-3) are not currently written anywhere in the Run Record — they are only knowable from the fact that a Claude/Cowork session performed the run. `Schema version` (field 5) is true but implicit, via co-location with `Workflow commit`. This is the concrete gap Section 7 calls out, and the reason its "Implementation status" note recommends adding the three missing fields to the §12.9 template. |

In short: today, every box in this contract is filled by the same single interactive Claude session, with no intermediate interface — which is exactly why the dependency inventory found no code-level abstraction to point to for the content-generation stage itself.

**Decision 4 (production designation) is trivially satisfied today:** Claude/Cowork is the sole implementation in existence, so it is by definition the single designated production implementation described in Section 4 and Section 9's Decision 4 — there is no second implementation yet for the shadow/comparison rule to constrain. The one thing worth flagging transparently: the historical `20260909_20260911_cyberbrief_retrospective` artifact (Section 9, Decision 1's historical note) was produced before this boundary rule existed and does not conform to it; this is a pre-contract exception in the archive, not a gap in Implementation A's current or future compliance.

---

## Minimum capabilities a second provider/runtime would need

To satisfy this contract without changing CyberBrief's outputs or behavior, a second provider/runtime would need, at minimum:

1. **Agentic tool use with real iterative web search** — not a single-shot completion; the ability to search, read results, decide whether evidence is sufficient, and search again (§2.14, and the core capability gap identified in the dependency inventory's prototype work).
2. **Reliable long-instruction-following** — the ability to ingest the full workflow document (hundreds of lines of interacting rules, conditional sections, and explicit prohibitions) each run and execute it faithfully, without a human re-summarizing it into a shorter prompt.
3. **File I/O against the connected filesystem, or an equivalent staging mechanism** — reading the workflow/schema/prior state and writing TXT, candidate JSON, and Run Record to exact paths and filenames.
4. **Schema-exact structured output** — the ability to produce JSON that satisfies `additionalProperties: false` at multiple nesting levels and conditional field requirements (`iad_signal`'s relevance/dimensions rule, `micro_tracking`'s both-fields-required rule) without a human correcting the shape after the fact.
5. **Ability to invoke, and faithfully report the result of, an external validation step it does not control** — running `cyberbrief_validator.py` and treating its verdict as final, including refusing to "fix" a failure by altering the schema or silently repairing output.
6. **Provenance self-reporting** — capturing its own provider/model identity into the Run Record, which today's Claude implementation does not yet do explicitly (Section 7's gap) and any second provider would need to do from day one for the Run Record to remain meaningful across providers.
7. **Timezone-correct date handling** — resolving "today," daily periods, and retrospective range boundaries against `America/Chicago` specifically (Section 1, Section 7), not the runtime's default or host timezone, including correct handling across the CST/CDT transition.
8. **Write-isolation discipline** — the ability to run in an isolated shadow/comparison mode that writes only to a provider-specific test location and never to any production canonical path, tracker, or research-state file, satisfying Section 4's production-designation rule even while under evaluation alongside the production implementation.

Everything below the validation gate — CSV generation, canonical promotion, tracker updates, and the Research Corpus/Discovery/Memory pipeline — requires none of this, since it is already deterministic Python with no dependency on which runtime produced the candidate JSON it consumes.

No implementation performed. This is a draft contract only, not yet referenced anywhere, not committed.
