# Research Discovery V1

Requirement 12: Research Discovery. Downstream and additive to Requirement 11's
Research Corpus V1. Never modifies canonical CyberBrief files or Research
Corpus V1 output; only reads them.

```
Canonical CyberBrief  -->  Research Corpus (Req 11)  -->  Research Discovery (Req 12)
```

## What Discovery is

**Discovery Candidate** = a relationship, recurrence, contrast, anomaly, or gap
surfaced across observations that was not already explicitly encoded (as a
canonical statement, an IAD mechanism, a case-continuity link, or a
longitudinal analytical claim) and that creates a worthwhile question for
investigation.

Discovery does **not** establish that a relationship is true, causal,
statistically significant, or generalizable. A Discovery Candidate is a
**workflow object** ("noticed, not yet evaluated"), not an epistemic
conclusion. It never carries an Observed / Analytical Inference / Hypothesis
status -- those are earned later, by a person, if the candidate is
investigated.

### The boundary

| Category | What it is | Example |
|---|---|---|
| Observation | What happened in one item | "Rhysida claimed Berlin's network on 8/28." |
| Aggregation | A count/cross-tab of existing fields | "7 of 15 observations carry arc 2.4." |
| Existing analytical claim | Something CyberBrief/Requirement 11 already concluded and preserved | A `longitudinal_claim`, an `iad_mechanism` relationship, a `case_continuity` link. |
| **Discovery Candidate** | A relationship *implied* by the corpus but never stated by anything above | "Dimensions X and Y are each common but never tagged on the same observation." |
| Hypothesis | A proposed *explanation* for a discovery candidate | "...because analysts only tag one institutional lens per item." |
| Model | A durable, generalizable explanatory structure | Out of scope for Requirement 12 entirely. |

Discovery names the pattern. Hypothesis proposes why it exists. Requirement 12
V1 stops at naming -- it does not generate, hold, or store hypothesis text.

## Discovery Candidate record (7 elements)

1. **statement** -- what was noticed, in descriptive (non-causal) language.
2. **supporting observation IDs** -- which Research Corpus rows this rests on.
3. **fields/dimensions involved** -- which columns produced the pattern.
4. **evidence path** -- candidate -> corpus row(s) -> canonical item(s) -> source URL(s).
5. **why it may matter** -- one hedged, templated sentence framing the open question.
6. **limitations** -- free text that *must* state the sample size and known sparsity/coverage constraints.
7. **strength** -- `Strong` / `Weak` / `Not a Discovery`. Measures clarity of the
   pattern, not statistical confidence. `Not a Discovery` is used internally
   for candidates that reached construction but were suppressed by a gate;
   it never appears on a surfaced candidate.

No confidence score, no statistical-significance field, no epistemic-status
field, no hypothesis field, no model field, no numeric ranking. Implementation
metadata needed for reproducibility (a stable candidate ID, generation
lineage, gate-pass bookkeeping) may exist in the stored JSON without
expanding this seven-element researcher-facing record.

## The seven filtering gates

| Gate | Question | Type |
|---|---|---|
| A. Novelty | Already explicitly represented in canonical text / IAD mechanisms / case continuity / longitudinal claims? | Hard |
| B. Non-triviality | More than a restated count? | Hard |
| C. Evidence traceability | Resolves to specific corpus rows and canonical evidence? | Hard |
| D. Missingness/uncertainty safety | Does it treat unknown/null as false/zero/absence? | Hard |
| E. Sample-size/sparsity safety | Resting on very few observations? | **Qualification only** |
| F. Category-vs-relationship safety | Shared classification mistaken for shared case/mechanism? | Hard |
| G. Causality safety | Co-occurrence presented as causation/mechanism? | Hard |

E never suppresses a candidate by itself -- a small but genuinely clear
pattern (demonstrated by the manual case-evolution test, C8) must still
surface, just heavily caveated. The other six can suppress or force a
candidate to be reworded before it is ever shown.

## Discovery methods implemented in V1

V1 implements exactly two, chosen because they were the ones demonstrated to
work cleanly on real corpus data during the design tests, computed generically
(no finding is hard-coded):

1. **`iad_dimension_exclusivity`** -- for every pair of IAD dimensions that
   each independently recur often enough to be non-trivial, checks whether
   they are ever tagged on the same observation. Surfaces pairs with zero
   co-occurrence.
2. **`category_dimension_coupling`** -- for every categorical field
   (`signal_type`, `half_life`, `ai_impact`, `arc_code`, `sector_context`,
   `actor_context`, `security_discipline`) and each of its populated,
   minority (non-default) values, checks whether observations carrying that
   value tag a given IAD dimension at a much higher rate than the rest of
   the corpus.

Both are corpus-wide statistical comparisons over fields Requirement 11
already preserves. Neither claims a mechanism; both only claim a pattern.

## What V1 does not attempt

Hypothesis generation beyond one hedged framing sentence, hypothesis testing,
model development, visualization, dashboards, a Research Workbench, an
interactive query interface, embeddings, clustering, a vector database, a
knowledge graph, database/cloud infrastructure, automated research writing,
and historical normalization. All of these remain out of scope for
Requirement 12 (several belong to Requirement 13).

## Regenerating

```
python3 research_discovery/generate_discovery.py
```

No arguments. Reads the current `CyberBrief/Data/research_corpus/` output and
the canonical `CyberBrief/Data/*.json` files (read-only, for evidence
resolution). Writes `CyberBrief/Data/research_discovery/`. Deterministic:
identical inputs produce identical output, including candidate IDs. Failure
during generation leaves the last known-good output in place (candidate
directory is validated, then promoted by rename -- never a delete-then-write).

## Known V1 limitations

- The novelty check (gate A) is **structural, not semantic**: it can detect
  that a discovered dimension-pair relationship already exists as an explicit
  `iad_mechanism` relationship, but it cannot detect that a human analyst's
  free-text `longitudinal_claim` or item `summary` already said something
  equivalent in prose. Catching that requires a person reading the surfaced
  candidate, which the IGNORE/WATCH/INVESTIGATE decision point already
  provides for.
- `security_discipline` and `sector_context` are too sparse in the current
  4-file corpus to produce any `category_dimension_coupling` candidates --
  not a defect, just a sample-size ceiling documented per the design tests.
- Only two discovery modes are implemented. Case-evolution comparison
  (demonstrated as C8 in the design tests) is not automated in V1 -- it
  requires comparing dimension tags across a `case_continuity` link, which
  the corpus currently contains exactly one instance of; not enough to
  justify a general method yet.
- Related-candidate flagging is a plain shared-field/shared-dimension check,
  not similarity detection -- by design.
- During implementation, computing these methods directly from corpus data
  caught a data-reading error in the earlier manual design test: observation
  4 (ZBT router backdoors) does not tag the `Levers` dimension (it tags
  `Interactions` instead). The manually-authored "C7" candidate from the
  prior design test therefore overstated the pattern as 4/4 Structural Shift
  observations tagging Levers; the code-verified figure is 3/4 (75%), still
  a clear pattern against an 9% complement rate, but the corrected number.
  This is reported transparently rather than silently reproduced.
