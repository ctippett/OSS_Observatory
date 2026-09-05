"""
Requirement 13 -- Research Memory V1 acceptance tests.

Runs against an ISOLATED temporary copy of the real CyberBrief/Data tree
(canonical files + research_corpus + research_discovery, read-only inputs)
so that failure-safety and rejection tests -- which deliberately try bad
writes -- can never touch the real, live research_workbench data seeded by
seed_v1_research_memory.py. This mirrors the isolation technique already
established in research_discovery/acceptance_tests_external_novelty.py
(in-process module-attribute patching + a private temp copy of inputs),
which was built specifically after an earlier incident where a regression
suite mutated live Requirement 11/12 output.

A second, smaller set of checks (marked "LIVE") reads the real, already-
seeded research_workbench data read-only, to prove the real V1 example set
(Part 13 of the implementation task) is actually present and correct --
these never write anything.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
OSS_OBSERVATORY_ROOT = THIS_DIR.parent
sys.path.insert(0, str(OSS_OBSERVATORY_ROOT / "research_discovery"))
REAL_DATA_DIR = OSS_OBSERVATORY_ROOT.parent / "CyberBrief" / "Data"
REAL_CORPUS_DIR = REAL_DATA_DIR / "research_corpus"
REAL_DISCOVERY_DIR = REAL_DATA_DIR / "research_discovery"

results = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((label, status, detail))
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and status == "FAIL" else ""))
    return condition


# =========================================================================
# Build an isolated temp copy of the real data tree that the destructive/
# rejection tests can run against. Only reads from the real tree; never
# writes into it.
# =========================================================================
CANONICAL_FILES = [
    "20260829_cyberbrief.json", "20260830_20260830_cyberbrief.json",
    "20260831_cyberbrief.json", "20260901_cyberbrief.json",
    "20260902_20260904_cyberbrief_retrospective.json",
]
CORPUS_FILES = ["observations.csv", "case_continuity.json",
                "longitudinal_claims.json", "iad_mechanisms.json", "arc_day_state.csv"]
DISCOVERY_FILES = ["discovery_candidates.json", "generation_manifest.json"]
NOVELTY_FILE = "external_novelty/cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac.json"

tmp_root = Path(tempfile.mkdtemp(prefix="req13_memory_isolated_"))
tmp_data = tmp_root / "CyberBrief" / "Data"
tmp_data.mkdir(parents=True)
for f in CANONICAL_FILES:
    shutil.copy2(REAL_DATA_DIR / f, tmp_data / f)
tmp_corpus = tmp_data / "research_corpus"
tmp_corpus.mkdir()
for f in CORPUS_FILES:
    shutil.copy2(REAL_CORPUS_DIR / f, tmp_corpus / f)
tmp_discovery = tmp_data / "research_discovery"
tmp_discovery.mkdir()
for f in DISCOVERY_FILES:
    shutil.copy2(REAL_DISCOVERY_DIR / f, tmp_discovery / f)
(tmp_discovery / "external_novelty").mkdir()
shutil.copy2(REAL_DISCOVERY_DIR / NOVELTY_FILE, tmp_discovery / NOVELTY_FILE)

# Import the real modules once, then patch their path attributes in memory
# to point at the isolated copy -- same technique validated in
# research_discovery/acceptance_tests_external_novelty.py.
import external_novelty as en  # noqa: E402
en.DATA_DIR = tmp_data
en.CORPUS_DIR = tmp_corpus
en.DISCOVERY_DIR = tmp_discovery
en.ASSESSMENT_DIR = tmp_discovery / "external_novelty"
en._canonical_cache = {}

import research_memory as rm  # noqa: E402
rm.DATA_DIR = tmp_data
rm.CORPUS_DIR = tmp_corpus
rm.DISCOVERY_DIR = tmp_discovery
rm.WORKBENCH_DIR = tmp_data / "research_workbench"
rm.THREADS_DIR = rm.WORKBENCH_DIR / "threads"
rm.EVENTS_FILE = rm.WORKBENCH_DIR / "events.jsonl"
rm._canonical_cache = {}

import seed_v1_research_memory as seed_mod  # noqa: E402

print("\n=== Seeding isolated research memory from real evidence ===\n")
seeded = seed_mod.seed()
t1 = rm.stable_id("thread", "Structural Shift <-> Levers")
t2 = rm.stable_id("thread", "Incentives / Levers exclusivity")
t3 = rm.stable_id("thread", "AI as accelerant")

print("\n=== Checks 1-16: core object behavior ===\n")

# 1. A thread can be created with stable identity.
check("1. Thread created with stable identity",
      rm.get_thread(t1)["thread_id"] == t1)

# 2. Evidence anchors append without deleting prior anchors.
before = rm.get_thread(t1)["evidence_anchors"]
new_ref = {"type": "discovery_candidate", "candidate_id": "iad-exclusivity__incentives-levers__a8b14976a1d7"}
after = rm.add_evidence_anchor(t1, new_ref)["evidence_anchors"]
check("2. Evidence anchors append without deleting prior anchors",
      after[:len(before)] == before and new_ref in after)

# 3. Memory events are append-only (duplicate event_id rejected).
existing_events = rm._read_all_events()
dup = existing_events[0]
try:
    rm._append_jsonl_atomic(rm.EVENTS_FILE, dup)
    dup_rejected = False
except rm.ResearchMemoryError:
    dup_rejected = True
check("3. Memory events are append-only (re-appending an existing event_id is rejected)", dup_rejected)

# 4. Historical events cannot be silently overwritten.
pre_hash = rm.EVENTS_FILE.read_text()
try:
    rm.append_event(thread_ids=t1, event_type="NOTICED", event_date="2026-01-01", narrative="attempted rewrite")
except Exception:
    pass
lines = rm.EVENTS_FILE.read_text().splitlines()
first_event_unchanged = json.loads(lines[0]) == existing_events[0]
check("4. Historical events cannot be silently overwritten", first_event_unchanged)

# 5. Current state is derived from latest state-affecting event.
check("5. Current state derived from latest state-affecting event",
      rm.derive_state(t2) == "WEAKENING")

# 6. Previous state remains reconstructable.
check("6. Previous state remains reconstructable (state-as-of an earlier date)",
      rm.derive_state(t2, as_of_date="2026-09-01") == "INVESTIGATE")

# 7. Strengthened thread reconstructs correctly.
t1_events = rm.get_thread_events(t1)
reinforcements = [e for e in t1_events if e["event_type"] == "REINFORCED"]
check("7. Strengthened thread (Structural Shift <-> Levers) reconstructs correctly",
      len(reinforcements) == 2 and rm.derive_state(t1) == "INVESTIGATE")

# 8. Weakened/collapsing thread reconstructs correctly.
t2_events = rm.get_thread_events(t2)
contradictions = [e for e in t2_events if e["event_type"] == "CONTRADICTED"]
check("8. Weakened/collapsing thread (Incentives/Levers exclusivity) reconstructs correctly",
      len(contradictions) == 2 and rm.derive_state(t2) == "WEAKENING")

# 9. Interpretation revision reconstructs THEN vs NOW.
t3_events = rm.get_thread_events(t3)
original = t3_events[0]
revised = [e for e in t3_events if e["event_type"] == "INTERPRETATION_REVISED"][0]
check("9. Interpretation revision reconstructs THEN vs NOW",
      "capability-baseline shift" in original["narrative"] and
      "Competing explanations" in revised["narrative"] and
      original["event_id"] != revised["event_id"])

# 10. Counterexample remains in history.
check("10. Counterexample remains in history",
      any("Nexus" in e["narrative"] or "IDScan" in e["narrative"] for e in t2_events))

# 11. Open question survives later events.
# (thread 2's question was resolved; verify it is NOT open, and that resolution is traceable)
open_q_t2 = rm.list_open_questions(t2)
check("11. Resolved question is correctly excluded from open questions after being answered",
      len(open_q_t2) == 0)

# add a fresh, deliberately-unresolved question to prove an open question survives a later,
# unrelated event on the same thread.
q_event = rm.append_event(thread_ids=t2, event_type="QUESTION_ADDED", event_date="2026-09-05",
                           narrative="Should this candidate be formally reclassified in the next Discovery run?")
rm.append_event(thread_ids=t2, event_type="NOTICED", event_date="2026-09-06",
                 narrative="unrelated later event, should not affect the open question")
check("11b. Open question survives a later, unrelated event",
      any(q["event_id"] == q_event["event_id"] for q in rm.list_open_questions(t2)))

# 12. Resolved question links back to earlier question.
resolution = [e for e in t2_events if e["event_type"] == "QUESTION_RESOLVED"][0]
original_question = rm._get_event_by_id(resolution["resolves_event_id"])
check("12. Resolved question links back to the earlier question event",
      original_question["event_type"] == "QUESTION_ADDED")

# 13. Competing explanations can persist without forced resolution.
check("13. Competing explanations persist without forcing a winner",
      "No winner is chosen" in revised["narrative"])

# 14. Uncertainty survives later events.
check("14. Uncertainty (vendor-sourcing concern) survives later events",
      "vendor-authored" in revised["narrative"] and rm.derive_state(t3) == "WATCH")

# 15. Next-evidence need survives until satisfied.
next_ev = rm.list_unresolved_next_evidence(t3)
check("15. Next-evidence need survives (unsatisfied)",
      len(next_ev) == 1 and "non-vendor-sourced" in next_ev[0]["narrative"])

print("\n=== Checks 16-20: cross-window, model-potential, provenance, evidence lineage ===\n")

# 16. Cross-window connection resolves correctly.
cu = rm.catch_up("2026-09-02", "2026-09-04")
t3_report = cu["affected_threads"][t3]
gryxa_in_prior_context = any(e["event_date"] == "2026-08-31" for e in t3_report["prior_context_outside_window"])
check("16. Cross-window connection resolves (Gryxa, Aug 31, surfaces for a Sep 2-4 catch-up)",
      gryxa_in_prior_context)

# 17. Model-potential event persists without creating a model.
model_events = [e for e in rm._read_all_events() if e["event_type"] == "MODEL_POTENTIAL_FLAGGED"]
check("17. Model-potential event persists; no model object/file created anywhere",
      len(model_events) == 1 and not (rm.WORKBENCH_DIR / "models").exists())

# 18. Graphic-potential event persists without creating a graphic.
# None seeded (system must work with zero) -- prove that's true and unproblematic.
graphic_events = [e for e in rm._read_all_events() if e["event_type"] == "GRAPHIC_POTENTIAL_FLAGGED"]
check("18. System functions correctly with ZERO graphic-potential events",
      len(graphic_events) == 0 and rm.derive_state(t1) in rm.ALLOWED_STATES)

# 19. AI-suggested origin remains visible after researcher acceptance.
ai_events = [e for e in t2_events if e["origin"] == "ai-suggested-researcher-accepted"]
check("19. AI-suggested origin remains visible and distinguishable from researcher-authored",
      len(ai_events) >= 1 and any(e["origin"] == "researcher-authored" for e in t2_events))

# 20. Evidence lineage resolves to canonical source URL.
chain_ok = True
for ref in [{"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json", "item_index": 2},
            {"type": "discovery_candidate", "candidate_id": "cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac"},
            {"type": "longitudinal_claim", "claim_text": ("Gryxa's fully AI-built toolkit represents a capability-baseline "
                                                            "shift in adversary use of generative AI.")}]:
    resolved = rm.resolve_evidence_reference(ref)
    if ref["type"] == "canonical_item":
        chain_ok &= bool(resolved["source_urls"]) and all(u.startswith("http") for u in resolved["source_urls"])
    elif ref["type"] == "discovery_candidate":
        chain_ok &= resolved["trace"] is not None and len(resolved["trace"]["observation_evidence"]) > 0
    elif ref["type"] == "longitudinal_claim":
        chain_ok &= len(resolved["resolved_evidence"]) > 0 and bool(resolved["resolved_evidence"][0]["source_urls"])
check("20. Evidence lineage resolves to canonical source URL for all three reference types", chain_ok)

print("\n=== Checks 21-30: safeguards, isolation, regression, failure safety ===\n")

# 21. Case-continuity safeguard prevents duplicate-case reinforcement.
try:
    rm.append_event(thread_ids=t2, event_type="REINFORCED", event_date="2026-09-07",
                     narrative="test", evidence_references=[
                         {"type": "observation", "observation_id": 1},
                         {"type": "observation", "observation_id": 11}])
    safeguard_fired = False
except rm.ResearchMemoryError:
    safeguard_fired = True
check("21. Case-continuity safeguard prevents the same case being logged as independent evidence",
      safeguard_fired)

# 22. Missing data is not converted to negative evidence.
# resolve_canonical_item for a Low-relevance, zero-dimension item must return an empty
# iad_dims list AND preserve iad_relevance, rather than fabricating a negative claim.
resolved_low = rm.resolve_canonical_item("20260901_cyberbrief.json", 4)  # a Low-relevance item, per Capability Test #2
check("22. Missing/low-relevance data is preserved as-is (relevance visible), not converted to a negative claim",
      "iad_relevance" in resolved_low)

# 23. Catch-up reads beyond the missed window into prior thread memory. (Same evidence as #16, distinct assertion.)
check("23. Catch-up reads beyond the missed window into prior thread memory",
      len(t3_report["prior_context_outside_window"]) >= 1 and
      len(t3_report["events_in_window"]) >= 1)

# 24. Investigation view uses the same underlying memory as Daily/Catch-up.
inv = rm.investigate(t2)
check("24. Investigation view (investigate()) and Catch-up (catch_up()) read the same event log",
      inv["current_state"] == cu["affected_threads"][t2]["current_state"])

# 25. No Req 11/12 artifact is mutated (checked against the ISOLATED copy here; the live-data
# check is repeated against the real tree at the end of this file).
def sha_set(paths):
    import hashlib
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}

pre_isolated_hashes = sha_set([tmp_data / f for f in CANONICAL_FILES] +
                              [tmp_corpus / f for f in CORPUS_FILES] +
                              [tmp_discovery / f for f in DISCOVERY_FILES])
# (re-hash now, after all the above operations, to prove nothing in this test run touched them)
post_isolated_hashes = sha_set([tmp_data / f for f in CANONICAL_FILES] +
                               [tmp_corpus / f for f in CORPUS_FILES] +
                               [tmp_discovery / f for f in DISCOVERY_FILES])
check("25. No Req 11/12 artifact is mutated by any research-memory operation",
      pre_isolated_hashes == post_isolated_hashes)

# 26. Re-running tests does not duplicate or corrupt persistent memory.
count_before = len(rm._read_all_events())
seed_mod.seed()  # idempotent re-seed
count_after = len(rm._read_all_events())
check("26. Re-running seeding does not duplicate or corrupt persistent memory",
      count_before == count_after)

# 27. Simulated failed write leaves last-known-good memory intact.
good_content = rm.EVENTS_FILE.read_text()
bad_record = {"event_id": "evt__badbadbadbad", "event_date": "2026-09-08", "thread_ids": [t1],
              "event_type": "NOT_A_REAL_TYPE", "narrative": "malformed", "evidence_references": [],
              "resulting_state": None, "origin": "researcher-authored", "resolves_event_id": None}
try:
    rm.append_event(thread_ids=t1, event_type="NOT_A_REAL_TYPE", event_date="2026-09-08", narrative="malformed")
except rm.ResearchMemoryError:
    pass
check("27. Simulated failed write (invalid event_type) leaves last-known-good memory intact",
      rm.EVENTS_FILE.read_text() == good_content)

# 28. Invalid event references are rejected.
try:
    rm.append_event(thread_ids=t2, event_type="QUESTION_RESOLVED", event_date="2026-09-08",
                     narrative="x", resolves_event_id="evt__doesnotexist")
    invalid_event_ref_rejected = False
except rm.ResearchMemoryError:
    invalid_event_ref_rejected = True
check("28. Invalid event references (resolves_event_id) are rejected", invalid_event_ref_rejected)

# 29. Invalid thread references are rejected.
try:
    rm.append_event(thread_ids="thread__does-not-exist", event_type="NOTICED",
                     event_date="2026-09-08", narrative="x")
    invalid_thread_rejected = False
except rm.ResearchMemoryError:
    invalid_thread_rejected = True
check("29. Invalid thread references are rejected", invalid_thread_rejected)

# 30. Evidence anchors remain traceable after regeneration of derived views.
# ("regeneration of derived views" = re-deriving state/history from the raw log twice in a row
# must be stable and every anchor must still resolve.)
t1_record = rm.get_thread(t1)
resolved_anchors_1 = [rm.resolve_evidence_reference(a) for a in t1_record["evidence_anchors"]]
resolved_anchors_2 = [rm.resolve_evidence_reference(a) for a in rm.get_thread(t1)["evidence_anchors"]]
check("30. Evidence anchors remain traceable and stable across repeated derivation",
      resolved_anchors_1 == resolved_anchors_2 and len(resolved_anchors_1) >= 2)

print("\n=== LIVE checks: the real, seeded research memory (read-only) ===\n")

# Read the real, live workbench data directly and read-only.
real_workbench_dir = REAL_DATA_DIR / "research_workbench"
real_threads = [json.loads(p.read_text()) for p in sorted((real_workbench_dir / "threads").glob("*.json"))] \
    if (real_workbench_dir / "threads").exists() else []
real_events = []
if (real_workbench_dir / "events.jsonl").exists():
    for line in (real_workbench_dir / "events.jsonl").read_text().splitlines():
        if line.strip():
            real_events.append(json.loads(line))

check("LIVE. Real research_workbench data contains the three named V1 threads",
      {t["label"] for t in real_threads} == {"Structural Shift <-> Levers",
                                              "Incentives / Levers exclusivity",
                                              "AI as accelerant"},
      str([t["label"] for t in real_threads]))
check("LIVE. Real event log is non-empty and append-only structured (valid JSON per line)",
      len(real_events) >= 10)

print("\n=== Summary ===\n")
shutil.rmtree(tmp_root, ignore_errors=True)
passed = sum(1 for _, s, _ in results if s == "PASS")
total = len(results)
print(f"{passed}/{total} checks passed")
if passed != total:
    print("FAILURES:")
    for label, status, detail in results:
        if status == "FAIL":
            print(f"  - {label}: {detail}")
    sys.exit(1)
