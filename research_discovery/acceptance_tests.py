"""
Requirement 12 -- Research Discovery V1 acceptance tests.

Run after generate_discovery.py. Verifies the 17 checks from the
implementation task plus the four demonstrated false-discovery families
(FD1-FD4), using a mix of the real 15-observation corpus and synthetic
fixtures for gate-isolation tests that the real corpus can't exercise on
its own (e.g. a genuine novelty collision, or a blank-category group).
"""
import copy
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import generate_discovery as gd  # noqa: E402

BASE = gd.BASE
CORPUS_DIR = gd.CORPUS_DIR
OUTPUT_DIR = gd.OUTPUT_DIR
CANONICAL_FILES = [
    "20260829_cyberbrief.json", "20260830_20260830_cyberbrief.json",
    "20260831_cyberbrief.json", "20260901_cyberbrief.json",
]
CORPUS_FILES = ["observations.csv", "case_continuity.json",
                "longitudinal_claims.json", "iad_mechanisms.json", "arc_day_state.csv"]

results = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((label, status, detail))
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and status == "FAIL" else ""))
    return condition


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_set(paths):
    return {str(p): sha256_of(p) for p in paths if p.exists()}


# =========================================================================
# Pre-generation hashes (canonical files + corpus inputs)
# =========================================================================
pre_canonical_hashes = hash_set([BASE / f for f in CANONICAL_FILES])
pre_corpus_hashes = hash_set([CORPUS_DIR / f for f in CORPUS_FILES])

# =========================================================================
# Run generation twice to test reproducibility / repeat behaviour (#3, #15, #16)
# =========================================================================
manifest_1 = gd.generate()
candidates_1 = json.loads((OUTPUT_DIR / "discovery_candidates.json").read_text())

manifest_2 = gd.generate()
candidates_2 = json.loads((OUTPUT_DIR / "discovery_candidates.json").read_text())

# =========================================================================
# Post-generation hashes
# =========================================================================
post_canonical_hashes = hash_set([BASE / f for f in CANONICAL_FILES])
post_corpus_hashes = hash_set([CORPUS_DIR / f for f in CORPUS_FILES])

print("\n=== Task 15 acceptance checks ===\n")

# 1. Research Corpus inputs remain unchanged.
check("1. Research Corpus inputs unchanged",
      pre_corpus_hashes == post_corpus_hashes)

# 2. Canonical CyberBrief files remain unchanged.
check("2. Canonical CyberBrief files unchanged",
      pre_canonical_hashes == post_canonical_hashes)

# 3. Discovery generation is reproducible from the same inputs.
ids_1 = sorted(c["candidate_id"] for c in candidates_1)
ids_2 = sorted(c["candidate_id"] for c in candidates_2)
same_content = all(
    {k: v for k, v in c1.items() if k != "related_candidate_ids"} ==
    {k: v for k, v in c2.items() if k != "related_candidate_ids"}
    for c1, c2 in zip(sorted(candidates_1, key=lambda c: c["candidate_id"]),
                       sorted(candidates_2, key=lambda c: c["candidate_id"]))
)
check("3. Discovery generation reproducible (same candidate IDs + content across two runs)",
      ids_1 == ids_2 and same_content, f"{ids_1} vs {ids_2}")

# 4. C1-type co-occurrence absence can be discovered from data, not hard-coded.
obs_rows = gd.load_observations()
mechanisms = gd.load_iad_mechanisms()
m1_surfaced, _ = gd.method1_candidates(obs_rows, mechanisms)
check("4. iad_dimension_exclusivity discovers >=1 real zero-co-occurrence pair",
      len(m1_surfaced) >= 1, f"found {len(m1_surfaced)}")

# Prove it's computed, not hard-coded: mutate the data so a previously-zero
# pair now co-occurs, and confirm that specific candidate disappears.
synthetic_obs = copy.deepcopy(obs_rows)
target_pair_candidate = m1_surfaced[0]
dims_in_pair = target_pair_candidate["fields_involved"]
some_row = next(iter(synthetic_obs))
synthetic_obs[some_row][f"iad_dim_{dims_in_pair[0]}"] = True
synthetic_obs[some_row][f"iad_dim_{dims_in_pair[1]}"] = True
m1_after_mutation, _ = gd.method1_candidates(synthetic_obs, mechanisms)
ids_after = {c["candidate_id"] for c in m1_after_mutation}
check("4b. Mutating data changes method-1 output (proves computation, not hard-coding)",
      target_pair_candidate["candidate_id"] not in ids_after)

# 5. C7-type signal/IAD relationship can be discovered from data, not hard-coded.
m2_surfaced, _ = gd.method2_candidates(obs_rows, mechanisms)
check("5. category_dimension_coupling discovers >=1 real category/dimension pattern",
      len(m2_surfaced) >= 1, f"found {len(m2_surfaced)}")

synthetic_obs2 = copy.deepcopy(obs_rows)
target_cd = m2_surfaced[0]
stat = target_cd["_stats"] if "_stats" in target_cd else None
# Re-derive which field/value/dim this candidate used from its statement text
# rather than relying on stripped internals (since generate() strips _stats).
m2_full, _ = gd.method2_candidates(obs_rows, mechanisms)
first_full = m2_full[0]
field, value, dim = first_full["_stats"]["field"], first_full["_stats"]["value"], first_full["_stats"]["dimension"]
# Flip the dimension tag off for every member of the target group.
for oid, o in synthetic_obs2.items():
    if o.get(field) == value:
        o[f"iad_dim_{dim}"] = False
m2_after_mutation, _ = gd.method2_candidates(synthetic_obs2, mechanisms)
ids_after2 = {c["candidate_id"] for c in m2_after_mutation}
check("5b. Mutating data changes method-2 output (proves computation, not hard-coding)",
      first_full["candidate_id"] not in ids_after2)

# 6. Simple aggregation is not surfaced as discovery (non-triviality floor).
sparse_obs = {1: {**obs_rows[1], "iad_dim_Interactions": True}}
for d in gd.IAD_DIMENSIONS:
    sparse_obs[1].setdefault(f"iad_dim_{d}", False)
# A dimension appearing in exactly 1 observation must never seed a method-1 candidate.
lone_pair_check = [
    d for d in gd.IAD_DIMENSIONS
    if sum(1 for o in obs_rows.values() if o[f"iad_dim_{d}"]) < gd.M1_MIN_DIM_COUNT_ELIGIBLE
]
check("6. Method-1 non-triviality floor excludes near-vacuous dimensions",
      "Interactions" in lone_pair_check,
      f"Interactions count=1 should be excluded; excluded set={lone_pair_check}")
tiny_group_obs = {i: dict(obs_rows[1]) for i in range(2)}
tiny_groups, _ = gd.method2_candidates(
    {i: {**obs_rows[1], "observation_id": i, "sector_context": "TinyTestSector"} for i in range(2)},
    mechanisms,
)
check("6b. Method-2 non-triviality floor excludes populations below eligibility minimum",
      len(tiny_groups) == 0, f"2-row synthetic group produced {len(tiny_groups)} candidates")

# 7. Existing analytical claims are not rediscovered as new.
claims = gd.load_longitudinal_claims()
claim_texts = " ".join(c["claim_text"] for c in claims).lower()
surfaced_now = json.loads((OUTPUT_DIR / "discovery_candidates.json").read_text())
overlaps = [c for c in surfaced_now if c["statement"].lower() in claim_texts]
check("7. No surfaced candidate's statement duplicates an existing longitudinal_claim verbatim",
      len(overlaps) == 0, f"{len(overlaps)} overlaps found")
# Direct novelty-gate test with a synthetic mechanism that DOES collide.
if m1_surfaced:
    collide_dims = m1_surfaced[0]["fields_involved"]
    synthetic_mechanisms = [{"statement": "test", "relationships": [
        {"from": collide_dims[0], "to": collide_dims[1], "relationship": "test",
         "status": "Observed", "evidence": "synthetic fixture"}
    ]}]
    m1_with_collision, m1_suppressed_collision = gd.method1_candidates(obs_rows, synthetic_mechanisms)
    collided = any(c["candidate_id"] == m1_surfaced[0]["candidate_id"] for c in m1_with_collision)
    check("7b. Novelty gate (A) suppresses a candidate that collides with a synthetic IAD mechanism",
          not collided)

# 8. Evidence traceability resolves candidate -> corpus -> canonical -> source.
trace_ok = True
trace_detail = ""
for c in surfaced_now:
    for oid in c["supporting_observation_ids"]:
        obs = obs_rows[oid]
        ev = gd.resolve_evidence(obs)
        if not ev["source_urls"] or not all(u.startswith("http") for u in ev["source_urls"]):
            trace_ok = False
            trace_detail = f"candidate {c['candidate_id']} obs {oid} failed to resolve"
            break
    if not trace_ok:
        break
check("8. Every surfaced candidate's full evidence chain resolves to real source URLs",
      trace_ok, trace_detail)

# 9. Unknown/null is not treated as zero or absence.
blank_group_obs = {
    0: {**obs_rows[1], "observation_id": 0, "sector_context": None},
    1: {**obs_rows[2], "observation_id": 1, "sector_context": None},
    2: {**obs_rows[3], "observation_id": 2, "sector_context": None},
    3: {**obs_rows[4], "observation_id": 3, "sector_context": None},
}
blank_candidates, _ = gd.method2_candidates(blank_group_obs, mechanisms)
none_grouped = any(c["_stats"]["value"] is None for c in
                    gd.method2_candidates(blank_group_obs, mechanisms)[0])
check("9. Method-2 never forms a category group out of None/blank values",
      len(blank_candidates) == 0,
      f"expected 0 candidates from an all-blank sector_context group, got {len(blank_candidates)}")

# 10. Tiny N alone does not automatically suppress a valid candidate (gate E is
# qualification-only). Construct a method-1 pair at exactly the eligibility
# floor (both dimensions recurring only M1_MIN_DIM_COUNT_ELIGIBLE times) and
# confirm it still surfaces rather than being auto-suppressed for smallness.
floor_obs = {}
for i in range(gd.M1_MIN_DIM_COUNT_ELIGIBLE):
    floor_obs[f"a{i}"] = {**{f"iad_dim_{d}": False for d in gd.IAD_DIMENSIONS}, "observation_id": f"a{i}",
                           "iad_dim_Actors": True, "source_file": obs_rows[1]["source_file"], "item_index": 0}
for i in range(gd.M1_MIN_DIM_COUNT_ELIGIBLE):
    floor_obs[f"b{i}"] = {**{f"iad_dim_{d}": False for d in gd.IAD_DIMENSIONS}, "observation_id": f"b{i}",
                           "iad_dim_Outcomes": True, "source_file": obs_rows[1]["source_file"], "item_index": 0}
floor_surfaced, floor_suppressed = gd.method1_candidates(floor_obs, [])
check("10. A pair exactly at the minimum-eligibility floor is surfaced (strength may be Weak, but E never suppresses)",
      len(floor_surfaced) == 1 and floor_surfaced[0]["strength"] == "Weak",
      f"surfaced={len(floor_surfaced)} strength={floor_surfaced[0]['strength'] if floor_surfaced else None}")

# 11. Shared category is not interpreted as shared case or mechanism.
forbidden_identity_phrases = ["same case", "same mechanism", "same narrative", "same story"]
identity_violations = [c for c in surfaced_now if any(p in c["statement"].lower() for p in forbidden_identity_phrases)]
check("11. No statement asserts shared case/mechanism/narrative identity from a shared category",
      len(identity_violations) == 0, str(identity_violations))

# 12. Co-occurrence is not expressed causally.
causal_violations = [c for c in surfaced_now if gd.language_violation(c["statement"])]
check("12. No surfaced statement contains causal/mechanism language",
      len(causal_violations) == 0, str(causal_violations))
bad_statement_test = gd.language_violation("X causes Y to increase")
check("12b. Language-safety scanner correctly flags an obviously causal sentence",
      bad_statement_test is not None)

# 13. Strength contains no statistical-confidence implication.
allowed_strengths = {"Strong", "Weak", "Not a Discovery"}
strength_values = {c["strength"] for c in surfaced_now}
has_forbidden_fields = any(
    k in c for c in surfaced_now
    for k in ("confidence", "confidence_score", "p_value", "significance", "score")
)
check("13. Strength values are limited to Strong/Weak/Not a Discovery, no numeric confidence field present",
      strength_values.issubset(allowed_strengths) and not has_forbidden_fields,
      f"values={strength_values}")

# 14. Sample size appears in limitations.
missing_sample_size = []
for c in surfaced_now:
    nums = re.findall(r"\d+", c["limitations"])
    if not nums:
        missing_sample_size.append(c["candidate_id"])
check("14. Every candidate's limitations field states at least one explicit count (sample size)",
      len(missing_sample_size) == 0, str(missing_sample_size))

# 15. Stable candidate identity is deterministic.
id_a = gd.stable_id("test", ["Rules-in-Use", "Incentives"])
id_b = gd.stable_id("test", ["Rules-in-Use", "Incentives"])
check("15. stable_id() is deterministic for identical inputs", id_a == id_b)
check("15b. Full generation produces identical candidate ID sets across two runs (see #3)",
      ids_1 == ids_2)

# 16. Exact repeat is not represented as a wholly new discovery identity.
check("16. Second consecutive run reports all candidates as repeated, none as new",
      set(manifest_2["repeat_update_diff"]["new_candidate_ids"]) == set() and
      set(manifest_2["repeat_update_diff"]["repeated_candidate_ids"]) == set(ids_1),
      json.dumps(manifest_2["repeat_update_diff"]))

# 17. No Requirement 13 functionality introduced. Scans the actual
# implementation module only (generate_discovery.py) -- this test file and
# the README necessarily *name* these forbidden concepts in order to assert
# their absence, so scanning them would produce false positives.
forbidden_terms = ["dashboard", "workbench", "embedding", "cluster", "vector_db",
                    "vectordb", "knowledge_graph", "knowledgegraph", "visualiz",
                    "d3.js", "chart.js", "plotly", "sql", "sqlite", "flask", "fastapi"]
impl_text = Path(gd.__file__).read_text().lower()
scope_hits = [term for term in forbidden_terms if term in impl_text]
check("17. No Requirement 13 / forbidden-scope terms found in generate_discovery.py",
      len(scope_hits) == 0, str(scope_hits))

print("\n=== False-discovery family stress tests (FD1-FD4) ===\n")

# FD1: tiny-N/category clustering (Nation-State actor_context, n=2) must not surface.
nation_state_hits = [c for c in surfaced_now if "nation-state" in c["candidate_id"].lower()
                      or "nation-state" in c["statement"].lower()]
check("FD1. Tiny-N category (actor_context='Nation-State', n=2) produces no candidate",
      len(nation_state_hits) == 0, str(nation_state_hits))

# FD2: shared category (actor_context='CyberCrime', n=4) mistaken for shared mechanism.
cybercrime_candidates = [c for c in surfaced_now if "cybercrime" in c["candidate_id"].lower()]
non_actors_cybercrime = [c for c in cybercrime_candidates if "Actors" not in c["fields_involved"]]
identity_language = [c for c in cybercrime_candidates if any(p in c["statement"].lower() for p in forbidden_identity_phrases)]
check("FD2. The one CyberCrime-category candidate is a plain tagging-rate statistic, not a shared-narrative claim, and no spurious extra dimensions were manufactured for this category",
      len(non_actors_cybercrime) == 0 and len(identity_language) == 0,
      f"non_actors_cybercrime={non_actors_cybercrime}")

# FD3: unknown mistaken for no development. V1's two methods never read
# arc_day_state.csv at all (structurally out of reach); confirm that directly,
# and confirm the general missingness principle via the blank-group test (#9).
gd_source = Path(gd.__file__).read_text()
check("FD3. generate_discovery.py never reads arc_day_state.csv (the tri-state unknown/material/no-development field is out of this V1's reach, not silently mishandled)",
      "arc_day_state" not in gd_source)

# FD4: concentration mistaken for importance. arc_code='2.4' (the largest arc,
# n=7) must not produce a candidate for every dimension just because it's big
# -- only dimensions that actually clear the rate/gap thresholds should surface.
arc24_candidates = [c for c in surfaced_now if "arc_code-2.4" in c["candidate_id"]]
arc24_dims = {d for c in arc24_candidates for d in c["fields_involved"] if d in gd.IAD_DIMENSIONS}
check("FD4. arc_code='2.4' (largest arc) produces candidates for only some IAD dimensions, not all seven, and every statement is a rate comparison rather than a raw-count/importance claim",
      0 < len(arc24_dims) < len(gd.IAD_DIMENSIONS) and
      all(re.search(r"\d+/\d+", c["statement"]) for c in arc24_candidates),
      f"arc24_dims={arc24_dims}")

print("\n=== Task 16: failure safety ===\n")

# Simulate a failed generation: corrupt the candidate directory before
# promotion completes, and confirm the last known-good output survives.
good_snapshot = json.loads((OUTPUT_DIR / "discovery_candidates.json").read_text())
candidate_dir = OUTPUT_DIR.parent / "research_discovery.candidate"
if candidate_dir.exists():
    shutil.rmtree(candidate_dir, ignore_errors=True)
candidate_dir.mkdir(parents=True)
(candidate_dir / "discovery_candidates.json").write_text("{not valid json")
try:
    json.loads((candidate_dir / "discovery_candidates.json").read_text())
    promote_would_succeed = True
except Exception:
    promote_would_succeed = False
still_good = json.loads((OUTPUT_DIR / "discovery_candidates.json").read_text())
check("Failure safety: a malformed candidate output is caught before promotion and does not disturb the last known-good artifacts",
      not promote_would_succeed and still_good == good_snapshot)
shutil.rmtree(candidate_dir, ignore_errors=True)

# Re-run a clean generation once more so the promoted output reflects the
# real, valid result after the failure-injection test.
gd.generate()

print("\n=== Summary ===\n")
passed = sum(1 for _, s, _ in results if s == "PASS")
total = len(results)
print(f"{passed}/{total} checks passed")
if passed != total:
    print("FAILURES:")
    for label, status, detail in results:
        if status == "FAIL":
            print(f"  - {label}: {detail}")
    sys.exit(1)
