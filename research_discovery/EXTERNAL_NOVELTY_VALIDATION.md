# External Novelty Validation V1

Requirement 12 addition. Downstream of Research Discovery V1 (`generate_discovery.py`),
which is unchanged by this document. Never modifies Discovery Candidates, the
Research Corpus, or canonical CyberBrief files; only reads them.

```
Discovery Candidate (Req 12)  -->  External Novelty Assessment (this addition)
```

## 1. Three distinct levels

This methodology exists because a Discovery Candidate passing Research
Discovery's novelty gate (Gate A) only establishes the first of three
distinct, non-implying levels:

**A. Internal Novelty** -- new to the Observatory's own accumulated encoded
knowledge. Already produced by Gate A: not a duplicate of an existing
`iad_mechanism` relationship, `longitudinal_claim`, or `case_continuity`
link. A claim about the Observatory's memory, nothing else.

**B. External Novelty** -- after a bounded, source-scoped, dated search, no
substantially equivalent articulation of the *same underlying relationship*
was found in the external knowledge reviewed. A claim about search coverage
and result. Never a claim about the state of human knowledge.

**C. Original Contribution** -- a researcher judgment, made *during
investigation*, that something adds genuine analytical value: a new
mechanism, boundary condition, context/application, synthesis, measurement,
or operational model.

**Internal Novelty ≠ External Novelty ≠ Original Contribution. None
automatically implies another.** A candidate can be internally novel and
externally well-known (still possibly worth investigating for a new
application). A candidate can be externally unfound and still not be an
original contribution (nobody may have looked because nobody cares). A
candidate can be externally well-known and still yield an original
contribution (see Task 9 / Section 6 below).

## 2. Standing writing rule

**Absence of found evidence is not evidence of absence.**

Never write, and never let an assessment imply:

- "novel"
- "first"
- "nobody has studied this"

solely because a search found no equivalent. The only defensible language is
search-scoped and dated:

> "No directly equivalent articulation was identified in the N sources
> reviewed across [families] as of [date]."

or, when partial coverage exists:

> "Existing literature addresses X and Y independently; the specific
> relationship connecting them, as surfaced by the Observatory, was not
> identified in the reviewed sources."

This rule governs every External Novelty Assessment record without
exception -- it is enforced by the required outcome vocabulary (Section 6)
and checked by the acceptance test, not left to per-assessment discipline
alone.

## 3. When validation runs

```
Discovery Candidate
    v
Internal Novelty (Gate A, already implemented)
    v
IGNORE / WATCH / INVESTIGATE   (researcher disposition)
    v
Researcher explicitly selects a candidate for external validation
    v
External Novelty Assessment
    v
Research Investigation
```

Rules:

- **IGNORE -> no external validation.** Spending search effort on a
  discarded candidate is waste.
- **WATCH -> normally no external validation.** Premature; more corpus
  evidence may resolve the pattern in either direction before it is worth a
  literature check.
- **INVESTIGATE -> eligible for external validation**, but eligibility is
  not automatic execution. The researcher still explicitly triggers the
  assessment for a specific candidate ID.
- **Strong candidate status alone does not trigger validation.** Strength
  measures corpus pattern clarity (Research Discovery's own scale), which is
  orthogonal to whether the pattern is worth checking against the external
  literature. A Strong candidate can be pure tagging-convention noise; a
  Weak one can be exactly the seed worth chasing.

`recommended_action` in `discovery_candidates.json` is Research Discovery's
own non-binding suggestion, not the researcher's disposition. The actual
gate is the researcher choosing to run this process for a given candidate
ID -- that invocation is itself the record of the decision; no new field on
the Discovery Candidate is required.

No scheduler, trigger mechanism, or automated candidate-triggered validation
is introduced. This is a manual, researcher-invoked, per-candidate process.

## 4. Source selection (candidate-driven)

Available source families:

- peer-reviewed academic literature
- conference proceedings
- preprints (important for recent, fast-moving topics -- see Section 7E)
- government / policy research
- standards bodies
- cybersecurity industry / vendor research
- think-tank / institutional research
- existing conceptual frameworks / models (e.g. the IAD framework itself)

**Not every family is searched for every candidate.** The methodology
normally selects 2-4 relevant families per candidate, driven by two
questions asked of the candidate itself:

1. Is this candidate about the **framework's own methodology** (e.g. an IAD
   dimension-tagging pattern) or about a **substantive real-world
   mechanism** (e.g. a claim about how cybersecurity events actually
   behave)? Framework-methodology candidates prioritize IAD/institutional-
   theory literature; substantive candidates prioritize the domain the
   underlying observations belong to.
2. What real-world domain do the underlying observations belong to
   (cybercrime, AI policy, OSS governance, critical infrastructure, ...)?
   That domain picks the applied family (government/policy, industry
   research, standards).

No crawler, standing literature index, or literature database is built.
Source selection and search are performed per-candidate, by a person (with
LLM research assistance), the same way any other research task in this
Observatory is performed.

## 5. Conceptual equivalence

External novelty cannot depend on exact terminology. The governing question
is **"has this underlying relationship already been substantially
articulated?"**, not "does anyone use our phrase?"

For every external validation:

1. Restate the candidate in plain English, stripped of Observatory jargon.
2. Generate synonyms and neighboring concepts from adjacent disciplines
   (institutional economics, systems theory, organizational behavior,
   regulatory studies, etc.) -- the system may do this.
3. Search using those concepts, not only the Observatory's own vocabulary.
4. For each retrieved source, ask two questions: does it describe the same
   underlying relationship regardless of vocabulary, and does it describe
   the same direction/context, or only a structurally similar but distinct
   one?
5. Place the source on this spectrum:

   - **exact terminology match**
   - **conceptual equivalent** -- different vocabulary, same underlying
     relationship
   - **partial overlap** -- covers part of the relationship, not the
     specific combination/direction/context
   - **adjacent** -- same broader topic, different specific relationship
   - **genuinely different relationship**

The **final conceptual-equivalence judgment above "exact match" is always
human-reviewed** (Section 9). No embeddings, vector search, or similarity
scoring are used -- equivalence is established by reading and paraphrase
comparison, a process discipline rather than infrastructure.

## 6. Outcome states

Exactly four allowed outcomes. **`NOVEL` is never a valid outcome.**

- **KNOWN** -- the same underlying relationship is already substantially
  articulated externally (same relationship, same or closely analogous
  context, credible cited source).
- **PARTIALLY KNOWN** -- relevant concepts, mechanisms, or adjacent
  relationships exist, but the candidate retains a potentially distinct
  context, application, mechanism, boundary condition, or operational
  framing. This state must never collapse into KNOWN merely because
  *something* related was found (Section 8, false-novelty safeguard G).
- **NOT FOUND** -- a disciplined, bounded search did not identify a
  substantially equivalent articulation. **Worded only as a claim about the
  search performed** -- never as global novelty.
- **INDETERMINATE** -- available evidence or search coverage is
  insufficient for a responsible assessment (e.g. authoritative sources
  inaccessible, the topic is too recent for reliable coverage, or the
  candidate itself is too thin/singular -- e.g. a single-instance
  `case_continuity` link -- to formulate a well-scoped search).

## 7. False-novelty safeguards

| # | Failure mode | Minimum safeguard |
|---|---|---|
| A | Terminology novelty mistaken for conceptual novelty | Mandatory plain-English decomposition + synonym list (Section 5) before judging outcome |
| B | Search-engine absence mistaken for novelty | Outcome vocabulary bans "novel"; `source_families_searched` + `limitations` make the claim's bounds visible in the record itself |
| C | Academic-only search misses practitioner work | Source-family selection (Section 4) is candidate-driven and must name which families were and were not searched, making a one-sided search visible |
| D | Practitioner-only search misses academic work | Same field, opposite direction; framework-methodology candidates specifically prioritize academic/institutional-theory literature |
| E | Publication lag (recent concept absent from peer-reviewed literature) | Preprints included as a standing source family; if the underlying event/technology is recent, default to INDETERMINATE rather than NOT FOUND on peer-reviewed absence alone |
| F | Same mechanism in another discipline, different terminology | Synonym-generation step (Section 5) explicitly casts across institutional economics, systems theory, organizational behavior -- not only cyber-labeled sources |
| G | Partial overlap misclassified as full equivalence | PARTIALLY KNOWN is mandatory and non-collapsible; `relationship_to_prior_work` must name what is present vs. absent relative to the candidate |
| H | Prior work found, therefore a useful new context/mechanism/application is wrongly discarded | Section 9's hard rule: KNOWN never automatically means discard |

## 8. Original contribution safeguard

**KNOWN does not automatically mean discard.** Even a KNOWN outcome
requires the researcher to consider, before setting a candidate aside,
whether the Observatory's version still adds:

- a new cybersecurity context
- a new OSS-governance context
- a new mechanism
- a new boundary condition
- a new measurement
- a new operationalization
- a new explanatory model

**PARTIALLY KNOWN** is the state most likely to support an original
contribution, precisely because it names what is *not yet* covered.

**The External Novelty Assessment must never decide whether an original
contribution exists.** That decision remains downstream researcher
judgment, exercised during investigation -- not something this process, or
any outcome it produces, resolves on the researcher's behalf.

## 9. Human review boundary

**SYSTEM MAY:**
- formulate search concepts from the candidate
- generate synonyms and neighboring concepts
- search external knowledge
- retrieve related work
- summarize conceptual overlap
- propose an outcome (KNOWN / PARTIALLY KNOWN / NOT FOUND / INDETERMINATE)

**RESEARCHER DECIDES:**
- whether the search coverage was adequate
- whether two concepts are genuinely equivalent
- whether the candidate remains worth investigating
- whether an original contribution exists
- whether to formulate a hypothesis, build a model, or write

**Any system-proposed outcome remains a draft until researcher review.**
Nothing produced by this process is final without a person reading and
accepting or editing it.

## 10. The record

Each External Novelty Assessment is one small, human-readable JSON file,
keyed by the stable Discovery Candidate ID, stored at:

```
CyberBrief/Data/research_discovery/external_novelty/<candidate_id>.json
```

Exactly ten fields -- nothing added beyond what this design demonstrated as
necessary:

1. `discovery_candidate_id` -- join key back to `discovery_candidates.json`.
2. `validation_date` -- scopes the search in time (publication-lag safety).
3. `relationship_or_research_question` -- the plain-English decomposition
   (Section 5, step 1), distinct from the candidate's own statement.
4. `search_concepts_and_synonyms` -- what was actually searched (Section 5,
   step 2) -- makes a terminology-only search visible after the fact.
5. `source_families_searched` -- which of Section 4's families were used,
   and implicitly which were not.
6. `strongest_related_prior_work` -- prose synthesis of the most relevant
   material found, if any.
7. `relationship_to_prior_work` -- the equivalence-spectrum judgment
   (Section 5, step 5) plus reasoning; where PARTIALLY KNOWN, names what is
   present vs. absent.
8. `external_novelty_outcome` -- one of KNOWN / PARTIALLY KNOWN / NOT FOUND
   / INDETERMINATE.
9. `limitations` -- what was not checked, what could not be assessed, and,
   for NOT FOUND, an explicit restatement that absence is search-scoped.
10. `evidence_and_citations` -- URLs/references for the material named in
    field 6, mirroring the `source_urls` discipline already used throughout
    this Observatory.

No confidence score, no numeric ranking, no `NOVEL` outcome, no database
schema. This is a plain JSON record, not a database.

## 11. Traceability

```
External Novelty Assessment
    -> external sources reviewed         (field 10)
    -> Discovery Candidate                (field 1, joins discovery_candidates.json)
    -> Research Corpus observations       (already resolved by the candidate's own
                                            supporting_observation_ids -- not duplicated)
    -> canonical CyberBrief evidence      (already resolved by Research Discovery's
                                            existing evidence chain -- not duplicated)
```

The two chains (external-validation and internal-evidence) meet at exactly
one join point -- the candidate ID -- and neither duplicates the other's
internals. From an assessment record alone, a researcher can reconstruct:
what the Observatory noticed (the candidate's own statement/evidence, via
field 1), what external knowledge was checked (fields 3-5), what related
prior work was found (fields 6, 10), why the outcome was assigned (fields
7-9), and which underlying observations produced the candidate (already
preserved by Research Discovery, unchanged).

## 12. What this addition is not

No crawler. No standing literature index or database. No embeddings, vector
search, or knowledge graph. No automated candidate-triggered validation, no
scheduler. No dashboard or visualization. No Research Workbench, hypothesis
generator, hypothesis tester, model generator, or auto-writing system. All
of these remain out of scope for Requirement 12 (several belong to
Requirement 13).
