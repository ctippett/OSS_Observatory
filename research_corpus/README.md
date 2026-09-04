# CyberBrief Research Corpus (Requirement 11, V1)

## Purpose

The Research Corpus is an **additive analytical representation** of canonical CyberBrief
observations, built to support reproducible quantitative and qualitative Observatory research
without altering, replacing, or duplicating the canonical evidence record.

It exists because canonical CyberBrief JSON — while a faithful, evidence-preserving daily
record — is not itself shaped for cross-observation analysis: dates, arc labels, and domain
strings are represented inconsistently enough (demonstrated across the Requirement 11 test
series) that naive aggregation over the raw files produces fragmented or misleading results.
The Research Corpus resolves exactly the fragmentation problems that were *demonstrated*
during that test series — nothing more, and nothing speculative.

## Canonical vs. derived: the non-negotiable boundary

**Canonical CyberBrief JSON (`CyberBrief/Data/*.json`) remains the sole authoritative
evidence record.** The Research Corpus is generated *from* it, never replaces it, and the
generator (`generate_research_corpus.py`) never writes to `CyberBrief/Data/*.json` — it only
reads those files and writes new output into `CyberBrief/Data/research_corpus/`, a separate,
clearly-labeled, fully regenerable directory.

Every research observation carries `(source_file, item_index)` — enough to resolve back to
the exact original canonical item. `summary`, `extracted_statistics`, `source_urls`, and
`breach_specifics` are **never** copied into the research corpus. If you need them, you follow
the pointer back to the canonical file. This is deliberate: duplicating that content would
create a second, driftable copy of evidence that claims no special authority over the original.

## Grain: one canonical item = one research observation

Every row in `observations.csv` corresponds to exactly one item in exactly one canonical
CyberBrief file. There is no merging, deduplication, or case-collapsing at the row level —
even the one demonstrated same-case pair (Berlin/Rhysida) remains two separate rows, linked
only through a separate case-continuity record (see below), never fused into one.

## Deterministic vs. interpretive fields

Not everything in the corpus is produced the same way, and the corpus does not pretend
otherwise:

**Deterministic (verbatim copy or direct computation, no judgment involved):**
`observation_id`, `source_file`, `item_index`, `brief_date`, `event_date`, `title`,
`domain_original`, `surface`, `signal_type`, `half_life`, `ai_impact`, `arc_original`,
`iad_relevance`, all seven `iad_dim_*` booleans.

**Interpretive (a documented judgment call was required):**
`arc_code` / `arc_label` (mostly mechanical, with one soft spot: inferring a label for a bare
arc code from a sibling observation in the same run — flagged via `arc_label_inferred`),
`actor_context` / `sector_context` / `security_discipline` (derived from a small, explicit,
hand-built lookup table over the domain strings that actually occur in the clean corpus — see
"Domain-derived dimensions" below), and every entry in `case_continuity.json` and
`longitudinal_claims.json` (hand-verified during the Requirement 11 test series, not the
output of an automated matcher).

A second competent researcher, given the four canonical files and this document, would
reproduce the deterministic fields exactly, and would very likely reproduce most of the
interpretive fields — but a handful of genuinely ambiguous cases are named explicitly below,
and this corpus does not hide that ambiguity behind a false claim of mechanical normalization.

## Evidence traceability

Every structured result in the corpus traces back through its row(s) to the canonical
observation(s) and from there to the original `source_urls`. This chain was tested explicitly
during acceptance testing (see `acceptance_tests.py`, checks P1–P3) for one IAD-related, one
domain-derived, and one arc-related result, and held in all three cases.

## Arc normalization

`arc_original` preserves the item's raw `arc` string exactly. `arc_code` and `arc_label` are
split from it: if the original string already contains a label (`"2.4 CyberCrime & Adversary
Economics"`), that label is used directly. If only a bare code is present (`"2.4"`) and
*another* observation *in this same corpus* carries the same code with a label attached, that
label is borrowed and `arc_label_inferred` is set to `true` — this flag exists specifically so
a borrowed label is never mistaken for one the analyst actually wrote for that item. Arc code
`2.2` has no label anywhere in the current corpus and is **not** invented — `arc_label` stays
empty for it. No-arc observations (`arc_original == ""`) remain valid, first-class rows.

## Domain-derived dimensions

`domain_original` is preserved exactly, unmodified. Three additional, sparse, nullable fields
are derived from it — `actor_context`, `sector_context`, `security_discipline` — using an
explicit lookup table (`DOMAIN_DIMENSION_MAP` in `generate_research_corpus.py`) built over the
exact 12 distinct domain strings observed in the clean corpus. **This is not a generic parser
or a taxonomy** — it is a small, fully-inspectable, individually-justified mapping, and every
entry documents its own confidence.

Three ambiguities are explicitly preserved rather than silently resolved, per the Requirement
11 Integration Test's findings:

1. **The "AI Policy, Governance & Ethical Integrity" phrase** (appearing in 3 domain values)
   duplicates longitudinal-arc-label vocabulary but was found to correspond to *different*
   arc codes across observations (2.1 for one occurrence, 2.3 for another). It is deliberately
   left unmapped to any dimension rather than guessed.
2. **`AppSec / Vulnerability Governance`** (one observation) is recorded as two discipline
   values rather than one. A different competent researcher might reasonably record a single
   combined value instead.
3. **`Critical Infrastructure / Aviation`** (one observation) is recorded with `sector_context
   = "Aviation"` only, treating "Critical Infrastructure" as a broader category Aviation
   already nests inside. A different competent researcher might record "Critical
   Infrastructure," or both.

Two observations (`Hardware Supply Chain / IoT` and bare `AI Policy, Governance & Ethical
Integrity`) legitimately populate **none** of the three dimensions — this is the correct,
evidenced outcome for domain content that resists this model, not a defect to be forced shut.

## IAD integration

`iad_relevance` and the seven `iad_dim_*` booleans are copied directly from each item's
existing `iad_signal.relevance` / `.dimensions`. The hybrid IAD fields
(`dimension_notes`, `mechanism`, `relationships`, and their `Observed` / `Analytical
Inference` / `Hypothesis` epistemic statuses) were implemented separately (see
`schemas/cyberbrief.schema.json`) and are **not redesigned here**. When present on a canonical
item, they are extracted into `iad_mechanisms.json` rather than flattened into the
observation row, because they are sparse, variable-shaped, and sometimes entirely absent.
**None of the four current clean files have hybrid IAD content** — the hybrid fields postdate
them and were deliberately not backfilled — so `iad_mechanisms.json` is currently empty. The
generator supports reading it correctly if and when a future observation populates it.

## Case continuity

`case_continuity.json` holds relationships between two observations that describe the same
underlying real-world case at different points in time. The minimum demonstrated
representation is used: a reference to the later observation, a reference to the earlier
observation, an evidence citation quoting the specific text that establishes the connection,
and an epistemic status. There is **no Case object and no synthetic case ID** — relationships
point directly at `(source_file, item_index)` pairs, and neither canonical observation is
modified by the relationship's existence.

V1 contains exactly one relationship: the Berlin/Rhysida pair (2026-09-01's confirmation
observation pointing back to 2026-08-29's initial claim), classified `Observed` because the
later observation's own text directly states the connection, corroborated by matching figures
in both observations.

This relationship was identified by hand during the Requirement 11 test series, not by an
automated matcher — discovering *additional*, not-yet-identified case relationships is
Requirement 12's job, not this corpus's.

## Longitudinal analytical claims

`longitudinal_claims.json` holds individual analytical claims — not whole `longitudinal_arcs`
paragraphs — each with claim text, an `arc_code`, one or more evidence pointers, an epistemic
status, and a brief date inherited from its parent brief. There is no claim graph and no
claim-to-claim relationship field, because no genuine instance of one claim reinforcing,
revising, or extending an earlier one was found anywhere in the four clean briefs.

V1 contains the seven claims identified and epistemically classified during the Longitudinal
Analytical Knowledge tests — two classified `Hypothesis` (claims that generalized to "a
pattern" or "the latest in a series" without a second supporting instance anywhere in the
clean corpus), three `Analytical Inference` (claims grounded in, but not directly quoted from,
a canonical item's own summary), and two `Observed` (claims the canonical item's own text
states directly). These seven are the complete set demonstrated during testing — this
generator does not run an automated claim-extraction process over `longitudinal_arcs` text,
because determining where one claim ends and another begins inside a bundled paragraph is
itself an interpretive act that was done by hand and verified, not automated.

## Arc day-state semantics: unknown ≠ zero

For every (brief date, arc code) pair, the corpus records one of three states:

- **`material`** — derived automatically from whether any item that day carries that arc code.
  Never separately stored as a flag, since it is always redundant with information already in
  `observations.csv`.
- **`no_material_development`** — assigned only when that day's `longitudinal_arcs` text for
  that arc code explicitly states there was no material development. This is a deliberate,
  positive statement in the source data, not an absence.
- **`unknown`** — everything else. An arc absent from a day's `longitudinal_arcs` is recorded
  as unknown, **never** silently treated as a confirmed zero.

The current four-file corpus produces exactly **6 material, 2 no_material_development, 8
unknown** cells (out of 16 = 4 arcs × 4 days). Treating those 8 unknown cells as zeros would
manufacture false data affecting half the matrix — this was demonstrated concretely during the
Arc Day-State Resolution Test (arc activity rates, apparent dormancy, and duration-between-
developments would all be distorted). **The 8 unknown cells are not backfilled, and never
will be for these four historical files** — only future CyberBrief runs that explicitly record
a per-arc status every day (see "Production discipline change," below) can turn future unknown
cells into confirmed material or no-material-development states.

## Production discipline change (for future CyberBrief runs)

To prevent *future* day×arc cells from being unknown by default, future CyberBrief production
should explicitly represent every tracked arc in `longitudinal_arcs` every day — recording
either the material development, or an explicit no-material-development statement (extending
the practice the 2026-08-29 brief already demonstrated is possible within the existing
schema). **This requires no schema change** — `longitudinal_arcs` already accepts an arbitrary
per-arc-code text entry; it is a production-workflow discipline change, not implemented here
(implementing a workflow-instruction edit was out of scope for this V1; this document only
states the smallest demonstrated remediation, per the Arc Day-State Resolution Test).

## Regeneration

Run `python3 research_corpus/generate_research_corpus.py` from anywhere; paths are resolved
relative to the script's own location. The generator:

1. Scans `CyberBrief/Data/*.json`, validates every file against Schema v1
   (`cyberbrief_validator.py` / `cyberbrief.schema.json`), and includes only files that pass —
   files that fail (malformed JSON, non-v1 shape, or genuine validation errors) are excluded
   and reported in `generation_manifest.json`, never silently coerced or normalized.
2. Builds `observations.csv`, `arc_day_state.csv`, `case_continuity.json`,
   `longitudinal_claims.json`, and `iad_mechanisms.json` in a temporary candidate directory.
3. Runs internal consistency checks (row-count match, no duplicate observation IDs, valid
   epistemic status values).
4. Promotes the candidate directory into place using directory renames only — if a previous
   output exists, it is renamed aside (never deleted outright) before the new output is renamed
   into place. A failed run (a raised exception at any point before promotion) never touches a
   previously-generated, known-good corpus.

Acceptance tests: `python3 research_corpus/acceptance_tests.py` — regenerates the corpus and
checks observation count, grain, date preservation, evidence-pointer resolution, arc
normalization, domain-dimension population, IAD frequencies, cross-tabulations, case
continuity, claim retrieval, the exact 6/2/8 day-state split, canonical-file non-mutation, and
five failure-safety scenarios (malformed input, a simulated failed run, ambiguous values
staying null, evidence-pointer resolution, and invalid epistemic status rejection).

## Known V1 limitations

- Only four clean Schema v1 days / 15 observations currently exist; every count and
  cross-tabulation in this corpus is a demonstration that the *representation* works, not a
  claim about a trend.
- The historical (pre-v1) CyberBrief corpus is not normalized. Non-v1 files are excluded from
  the Research Corpus, not coerced into it.
- Domain decomposition into `actor_context` / `sector_context` / `security_discipline` is
  interpretive for a documented minority of values (see "Domain-derived dimensions" above) —
  it is not presented as a deterministic fact.
- The 8 historical "unknown" arc day-states are permanent for these four files; they are never
  backfilled, regardless of what later evidence might suggest.
- Discovery of new patterns, relationships, clusters, or previously-unidentified case links
  across the corpus is Requirement 12's job and is explicitly out of scope here. This corpus
  preserves and structures what CyberBrief has already produced; it does not go looking for
  anything new.
