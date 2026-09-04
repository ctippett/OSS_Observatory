"""
Requirement 12 -- Research Discovery V1 generator.

Reads the existing Research Corpus V1 (CyberBrief/Data/research_corpus/) as
its analytical input, plus the canonical CyberBrief JSON files (read-only,
used only to resolve evidence -- source_urls -- for traceability). Never
writes to either. Produces additive, downstream Research Discovery V1
artifacts in CyberBrief/Data/research_discovery/:

  - discovery_candidates.json   surfaced candidates, full record
  - suppressed_candidates.json  candidates a hard gate rejected (debug/lineage only)
  - generation_manifest.json    lineage, gate stats, repeat/update diff vs prior run
  - DISCOVERY_BRIEF.md          human-readable ~30-second cards, Strong before Weak

Two discovery methods, computed generically from corpus values (nothing
hard-coded):

  1. iad_dimension_exclusivity   -- IAD dimension pairs that each recur
     often enough to be non-trivial but are never tagged on the same
     observation.
  2. category_dimension_coupling -- a minority categorical field value that
     is tagged with a given IAD dimension at a much higher rate than the
     rest of the corpus.

See research_discovery/README.md for full design rationale, the seven
filtering gates, and known V1 limitations.
"""
import csv
import json
import hashlib
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timezone
from itertools import combinations

BASE = Path("/sessions/quirky-beautiful-fermat/mnt/DoGoodData/CyberBrief/Data")
CORPUS_DIR = BASE / "research_corpus"
OUTPUT_DIR = BASE / "research_discovery"

IAD_DIMENSIONS = ["Actors", "Rules-in-Use", "Arena", "Incentives",
                   "Interactions", "Outcomes", "Levers"]

# Categorical fields eligible for Method 2. Deliberately excludes free-text
# fields (title, surface, domain_original) -- those are not discrete
# categories and Requirement 11 explicitly declined to normalize them.
CATEGORICAL_FIELDS = ["signal_type", "half_life", "ai_impact", "arc_code",
                       "sector_context", "actor_context", "security_discipline"]

# --- V1 thresholds ------------------------------------------------------
# Documented, initial heuristic cutoffs calibrated against the demonstrated
# examples from the Requirement 12 design tests, not statistical-significance
# thresholds. They govern ELIGIBILITY (gate B, non-triviality) and STRENGTH
# (pattern clarity), never novelty (A) or traceability (C), which are
# independent gates.
M1_MIN_DIM_COUNT_ELIGIBLE = 2     # each dimension must recur >=2x to be non-trivial
M1_MIN_DIM_COUNT_STRONG = 3       # both dimensions >=3x -> Strong

M2_MIN_TARGET_POP_ELIGIBLE = 3    # category population must be >=3
M2_MIN_TARGET_POP_STRONG = 4      # >=4 -> eligible for Strong
M2_MAX_TARGET_FRACTION = 0.5      # target group must be a minority of the corpus
M2_MIN_TARGET_RATE = 0.75         # target population must tag the dimension >=75% of the time
M2_MIN_GAP_ELIGIBLE = 0.4         # target_rate - complement_rate >= 0.4 to be eligible
M2_MIN_GAP_STRONG = 0.5           # >=0.5 gap -> eligible for Strong

FORBIDDEN_LANGUAGE = [
    "causes", "cause of", "because", "due to", "leads to", "results in",
    "same case", "same mechanism", "explains why", "as a result of",
    "drives", "triggers", "is responsible for", "proves", "confirms that",
    "demonstrates that", "shows that",
]


# =========================================================================
# Input loading
# =========================================================================

def load_observations():
    """Read observations.csv into typed row dicts, keyed by observation_id."""
    path = CORPUS_DIR / "observations.csv"
    rows = {}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            obs_id = int(r["observation_id"])
            typed = dict(r)
            typed["observation_id"] = obs_id
            for d in IAD_DIMENSIONS:
                key = f"iad_dim_{d}"
                typed[key] = (r[key] == "True")
            # Normalize blank strings to None for categorical fields so
            # "no value" is never treated as if it were a real category.
            for field in CATEGORICAL_FIELDS:
                if typed.get(field, "") == "":
                    typed[field] = None
            rows[obs_id] = typed
    return rows


def load_iad_mechanisms():
    path = CORPUS_DIR / "iad_mechanisms.json"
    return json.loads(path.read_text()) if path.exists() else []


def load_longitudinal_claims():
    path = CORPUS_DIR / "longitudinal_claims.json"
    return json.loads(path.read_text()) if path.exists() else []


def load_case_continuity():
    path = CORPUS_DIR / "case_continuity.json"
    return json.loads(path.read_text()) if path.exists() else []


_canonical_cache = {}


def resolve_evidence(obs, base_dir=BASE):
    """observation row -> canonical item -> source_urls. Read-only."""
    fname = obs["source_file"]
    idx = int(obs["item_index"])
    if fname not in _canonical_cache:
        _canonical_cache[fname] = json.loads((base_dir / fname).read_text())
    doc = _canonical_cache[fname]
    item = doc["items"][idx]
    return {
        "source_file": fname,
        "item_index": idx,
        "title": item.get("title"),
        "source_urls": list(item.get("source_urls", [])),
    }


# =========================================================================
# Gate A -- novelty
# =========================================================================

def dims_already_linked_in_mechanisms(dim_a, dim_b, mechanisms):
    """Structural novelty check: does any persisted IAD mechanism already
    state a from/to relationship between these two dimensions (either
    direction)? This is mechanical (exact dimension-name match against
    mechanism.relationships), not semantic -- see README known limitations.
    """
    for mech in mechanisms:
        for rel in mech.get("relationships", []):
            pair = {rel.get("from"), rel.get("to")}
            if pair == {dim_a, dim_b}:
                return True
    return False


# =========================================================================
# Gate G / F -- language safety
# =========================================================================

def language_violation(text):
    lowered = text.lower()
    for phrase in FORBIDDEN_LANGUAGE:
        if phrase in lowered:
            return phrase
    return None


# =========================================================================
# Method 1: IAD dimension exclusivity
# =========================================================================

def method1_candidates(obs_rows, mechanisms):
    surfaced, suppressed = [], []
    total = len(obs_rows)
    dim_true_rows = {
        d: sorted(oid for oid, o in obs_rows.items() if o[f"iad_dim_{d}"])
        for d in IAD_DIMENSIONS
    }
    dim_counts = {d: len(v) for d, v in dim_true_rows.items()}

    for dim_a, dim_b in combinations(IAD_DIMENSIONS, 2):
        count_a, count_b = dim_counts[dim_a], dim_counts[dim_b]
        # Gate B (non-triviality), enforced structurally: a dimension that
        # almost never appears makes "never co-occurs with X" vacuous.
        if count_a < M1_MIN_DIM_COUNT_ELIGIBLE or count_b < M1_MIN_DIM_COUNT_ELIGIBLE:
            continue
        joint = sorted(set(dim_true_rows[dim_a]) & set(dim_true_rows[dim_b]))
        if joint:
            continue  # they do co-occur -- not this pattern

        supporting = sorted(set(dim_true_rows[dim_a]) | set(dim_true_rows[dim_b]))
        strength = ("Strong" if count_a >= M1_MIN_DIM_COUNT_STRONG
                    and count_b >= M1_MIN_DIM_COUNT_STRONG else "Weak")

        statement = (
            f"In the {total}-observation corpus, the IAD dimensions "
            f"'{dim_a}' ({count_a} observations) and '{dim_b}' ({count_b} "
            f"observations) are never tagged on the same observation "
            f"(0 co-occurrences)."
        )
        why = (
            "Two independently recurring institutional dimensions never "
            "appearing together may reflect a real analytical distinction "
            "between them, or may simply reflect a tagging convention -- "
            "worth checking before treating either dimension's presence as "
            "informative about the other."
        )
        limitations = (
            f"Based on {count_a} and {count_b} observations respectively, "
            f"out of {total} total in the corpus. Does not establish that "
            f"the two dimensions are substantively incompatible with one "
            f"another, or explain why they never appear together -- only "
            f"that this corpus has never tagged them on the same "
            f"observation."
        )

        candidate = {
            "method": "iad_dimension_exclusivity",
            "candidate_id": stable_id("iad-exclusivity", sorted([dim_a, dim_b])),
            "statement": statement,
            "supporting_observation_ids": supporting,
            "fields_involved": sorted([dim_a, dim_b]),
            "why_it_may_matter": why,
            "limitations": limitations,
            "strength": strength,
            "_stats": {"count_a": count_a, "count_b": count_b, "joint": 0, "total": total},
        }
        surfaced.append(candidate) if _passes_hard_gates(candidate, mechanisms, obs_rows, surfaced_flag=True) \
            else suppressed.append(candidate)
    return surfaced, suppressed


# =========================================================================
# Method 2: category x dimension coupling
# =========================================================================

def method2_candidates(obs_rows, mechanisms):
    surfaced, suppressed = [], []
    total = len(obs_rows)

    for field in CATEGORICAL_FIELDS:
        groups = {}
        for oid, o in obs_rows.items():
            val = o.get(field)
            if val is None:  # gate D: never group on "missing" as a category
                continue
            groups.setdefault(val, []).append(oid)

        for value, member_ids in groups.items():
            n = len(member_ids)
            if n < M2_MIN_TARGET_POP_ELIGIBLE:
                continue
            if n / total > M2_MAX_TARGET_FRACTION:
                continue  # majority/default value -- not a distinguishing subgroup

            complement_ids = [oid for oid in obs_rows if oid not in member_ids]
            comp_total = len(complement_ids)
            if comp_total == 0:
                continue

            for dim in IAD_DIMENSIONS:
                target_tagged = [oid for oid in member_ids if obs_rows[oid][f"iad_dim_{dim}"]]
                target_rate = len(target_tagged) / n
                if target_rate < M2_MIN_TARGET_RATE:
                    continue
                comp_tagged = [oid for oid in complement_ids if obs_rows[oid][f"iad_dim_{dim}"]]
                comp_rate = len(comp_tagged) / comp_total
                gap = target_rate - comp_rate
                if gap < M2_MIN_GAP_ELIGIBLE:
                    continue

                strength = ("Strong" if n >= M2_MIN_TARGET_POP_STRONG
                            and gap >= M2_MIN_GAP_STRONG else "Weak")

                statement = (
                    f"{len(target_tagged)}/{n} ({target_rate:.0%}) observations "
                    f"where {field}='{value}' tag the '{dim}' IAD dimension, "
                    f"versus {len(comp_tagged)}/{comp_total} ({comp_rate:.0%}) "
                    f"among the remaining observations."
                )
                why = (
                    f"A markedly higher tagging rate for '{dim}' among "
                    f"{field}='{value}' observations than elsewhere in the "
                    f"corpus may reflect a genuine institutional relationship "
                    f"between them, or may be a coincidence of a small "
                    f"corpus -- worth testing as more observations "
                    f"accumulate."
                )
                limitations = (
                    f"Based on a target population of {n} observations "
                    f"(of {total} total); complement population is "
                    f"{comp_total}. Reflects only this corpus's own "
                    f"classification choices, not a general claim about "
                    f"{field} or '{dim}'. Does not establish causation."
                )

                candidate = {
                    "method": "category_dimension_coupling",
                    "candidate_id": stable_id("cat-dim-coupling", [field, str(value), dim]),
                    "statement": statement,
                    "supporting_observation_ids": sorted(member_ids),
                    "fields_involved": sorted([field, dim]),
                    "why_it_may_matter": why,
                    "limitations": limitations,
                    "strength": strength,
                    "_stats": {
                        "field": field, "value": value, "dimension": dim,
                        "target_n": n, "target_rate": target_rate,
                        "complement_n": comp_total, "complement_rate": comp_rate,
                        "gap": gap,
                    },
                }
                if _passes_hard_gates(candidate, mechanisms, obs_rows, surfaced_flag=True):
                    surfaced.append(candidate)
                else:
                    suppressed.append(candidate)
    return surfaced, suppressed


# =========================================================================
# Gate pipeline (shared)
# =========================================================================

def stable_id(prefix, parts):
    key = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(key.encode()).hexdigest()[:12]
    slug = "-".join(str(p).lower().replace(" ", "_").replace("/", "_") for p in parts)
    return f"{prefix}__{slug}__{digest}"


def check_novelty(candidate, mechanisms):
    if candidate["method"] != "iad_dimension_exclusivity":
        return True  # method 2 has no mechanism-relationship analogue to check
    dims = [f for f in candidate["fields_involved"] if f in IAD_DIMENSIONS]
    if len(dims) != 2:
        return True
    return not dims_already_linked_in_mechanisms(dims[0], dims[1], mechanisms)


def check_evidence_traceability(candidate, obs_rows):
    try:
        for oid in candidate["supporting_observation_ids"]:
            obs = obs_rows[oid]
            ev = resolve_evidence(obs)
            if not ev["source_urls"]:
                return False
        return True
    except Exception:
        return False


def check_language_safety(candidate):
    # Gate G/F apply to the claim itself (the "statement" field). The
    # why-it-may-matter and limitations fields are expected to *discuss and
    # disclaim* causation/mechanism ("does not establish causation") -- that
    # is their job, and banning causal vocabulary there would block the
    # disclaimers this design relies on. Only the statement must stay purely
    # descriptive.
    return language_violation(candidate["statement"]) is None


def _passes_hard_gates(candidate, mechanisms, obs_rows, surfaced_flag=False):
    reasons = []
    if not check_novelty(candidate, mechanisms):
        reasons.append("A:novelty -- relationship already stated in an IAD mechanism")
    if not check_evidence_traceability(candidate, obs_rows):
        reasons.append("C:evidence_traceability -- could not resolve full chain to source")
    if not check_language_safety(candidate):
        reasons.append("F/G:language_safety -- statement used causal/category-conflation language")
    candidate["_gate_result"] = "pass" if not reasons else "suppressed"
    candidate["_suppression_reasons"] = reasons
    if reasons:
        candidate["strength"] = "Not a Discovery"
    return not reasons


# =========================================================================
# Related candidates (Task 12) -- plain shared-field/shared-dimension check
# =========================================================================

def annotate_related(candidates):
    for c in candidates:
        c["related_candidate_ids"] = []
    for i, a in enumerate(candidates):
        for b in candidates[i + 1:]:
            if set(a["fields_involved"]) & set(b["fields_involved"]):
                a["related_candidate_ids"].append(b["candidate_id"])
                b["related_candidate_ids"].append(a["candidate_id"])
    for c in candidates:
        c["related_candidate_ids"] = sorted(set(c["related_candidate_ids"]))


# =========================================================================
# Attention output (Task 10) -- workflow aid only, not epistemic
# =========================================================================

def attention_recommendation(strength):
    return {"Strong": "INVESTIGATE", "Weak": "WATCH"}.get(strength, "IGNORE")


# =========================================================================
# Repeat / update safety (Task 11)
# =========================================================================

def diff_against_prior(current_ids):
    prior_manifest_path = OUTPUT_DIR / "generation_manifest.json"
    if not prior_manifest_path.exists():
        return {"new_candidate_ids": sorted(current_ids),
                "repeated_candidate_ids": [],
                "no_longer_holding_ids": [],
                "prior_run_found": False}
    try:
        prior = json.loads(prior_manifest_path.read_text())
        prior_ids = set(prior.get("surfaced_candidate_ids", []))
    except Exception:
        prior_ids = set()
    current = set(current_ids)
    return {
        "new_candidate_ids": sorted(current - prior_ids),
        "repeated_candidate_ids": sorted(current & prior_ids),
        "no_longer_holding_ids": sorted(prior_ids - current),
        "prior_run_found": True,
    }


# =========================================================================
# Human-readable brief (Task 14)
# =========================================================================

def render_brief(surfaced, generated_at):
    lines = [
        "# Research Discovery V1 -- Candidate Brief",
        "",
        f"Generated: {generated_at}",
        "",
        "Each candidate is a workflow object -- something noticed, not an "
        "established finding. Strength reflects pattern clarity, not "
        "statistical confidence. Recommended action is a workflow aid, not "
        "an epistemic status.",
        "",
    ]
    order = {"Strong": 0, "Weak": 1}
    for c in sorted(surfaced, key=lambda c: order.get(c["strength"], 2)):
        lines += [
            f"## [{c['strength']}] {c['candidate_id']}",
            "",
            f"**Statement:** {c['statement']}",
            "",
            f"**Why it may matter:** {c['why_it_may_matter']}",
            "",
            f"**Evidence:** observations {', '.join(str(o) for o in c['supporting_observation_ids'])}",
        ]
        for oid in c["supporting_observation_ids"]:
            pass
        lines += [
            f"**Limitations:** {c['limitations']}",
            "",
            f"**Recommended action:** {attention_recommendation(c['strength'])}",
        ]
        if c["related_candidate_ids"]:
            lines.append(f"**Related candidates:** {', '.join(c['related_candidate_ids'])}")
        lines += ["", "---", ""]
    return "\n".join(lines)


# =========================================================================
# Generation orchestration (candidate-then-promote, rename-only -- mirrors
# the FUSE-safe pattern established in the Research Corpus generator)
# =========================================================================

def generate():
    obs_rows = load_observations()
    mechanisms = load_iad_mechanisms()

    m1_surfaced, m1_suppressed = method1_candidates(obs_rows, mechanisms)
    m2_surfaced, m2_suppressed = method2_candidates(obs_rows, mechanisms)
    surfaced = m1_surfaced + m2_surfaced
    suppressed = m1_suppressed + m2_suppressed

    annotate_related(surfaced)
    for c in surfaced:
        c["recommended_action"] = attention_recommendation(c["strength"])
        c.pop("_stats", None)
        c.pop("_gate_result", None)
        c.pop("_suppression_reasons", None)
    for c in suppressed:
        c.pop("_stats", None)

    generated_at = datetime.now(timezone.utc).isoformat()
    diff = diff_against_prior([c["candidate_id"] for c in surfaced])

    manifest = {
        "generated_at": generated_at,
        "input_corpus_dir": str(CORPUS_DIR),
        "input_observation_count": len(obs_rows),
        "methods": ["iad_dimension_exclusivity", "category_dimension_coupling"],
        "gate_model": {
            "hard_gates": ["A_novelty", "B_non_triviality", "C_evidence_traceability",
                           "D_missingness_safety", "F_category_vs_relationship_safety",
                           "G_causality_safety"],
            "qualification_only_gates": ["E_sample_size_safety"],
        },
        "surfaced_count": len(surfaced),
        "suppressed_count": len(suppressed),
        "strong_count": sum(1 for c in surfaced if c["strength"] == "Strong"),
        "weak_count": sum(1 for c in surfaced if c["strength"] == "Weak"),
        "surfaced_candidate_ids": sorted(c["candidate_id"] for c in surfaced),
        "repeat_update_diff": diff,
    }

    candidate_dir = OUTPUT_DIR.parent / "research_discovery.candidate"
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir, ignore_errors=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    (candidate_dir / "discovery_candidates.json").write_text(json.dumps(surfaced, indent=2))
    (candidate_dir / "suppressed_candidates.json").write_text(json.dumps(suppressed, indent=2))
    (candidate_dir / "generation_manifest.json").write_text(json.dumps(manifest, indent=2))
    (candidate_dir / "DISCOVERY_BRIEF.md").write_text(render_brief(surfaced, generated_at))

    # Validate candidate directory before promoting.
    for fname in ["discovery_candidates.json", "suppressed_candidates.json",
                  "generation_manifest.json", "DISCOVERY_BRIEF.md"]:
        assert (candidate_dir / fname).exists(), f"candidate output missing {fname}"
    json.loads((candidate_dir / "discovery_candidates.json").read_text())  # must parse

    # Promote: rename existing good output aside (never delete-then-write),
    # then rename candidate into place. Same FUSE-safe pattern as Req 11.
    if OUTPUT_DIR.exists():
        stale = OUTPUT_DIR.parent / f"research_discovery.stale-{uuid.uuid4().hex[:12]}"
        shutil.move(str(OUTPUT_DIR), str(stale))
    shutil.move(str(candidate_dir), str(OUTPUT_DIR))

    return manifest


if __name__ == "__main__":
    result = generate()
    print(json.dumps(result, indent=2))
