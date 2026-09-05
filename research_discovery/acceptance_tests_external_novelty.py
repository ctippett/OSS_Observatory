"""
Requirement 12 -- External Novelty Validation V1 acceptance tests.

Covers the 20 checks from the implementation task.

IMPORTANT: checks 15 and 16 re-run the *existing* Research Discovery V1 and
Requirement 11 acceptance suites as a regression check. Both of those
suites call their generator's generate() function against real data by
default, and both generators discover their canonical-file input by
scanning CyberBrief/Data/ directly (generate_research_corpus.py) or by
reading whatever is currently promoted in CyberBrief/Data/research_corpus/
(generate_discovery.py). Running them against the *live* shared data plane
would regenerate and overwrite real Requirement 11/12 output with results
reflecting whatever canonical CyberBrief files happen to exist *today*
(which, after ordinary CyberBrief production runs, is more than the four
files these suites were originally built and pinned against) -- silently
changing already-committed-against artifacts as a side effect of running a
test.

To avoid that, checks 15 and 16 copy only the exact inputs each suite was
originally built against into an isolated temporary directory (plain /tmp,
outside the connected CyberBrief folder), monkeypatch each generator
module's path *attributes in memory only* to point at that copy, and run
the suites there via runpy so the real, unmodified generator logic executes
unchanged -- just against a private, disposable copy of its inputs. Nothing
on the real CyberBrief/Data/research_corpus or research_discovery directories
is touched by this file. This is verified directly by bracketing the entire
run with before/after hashes of both (checks 17-19), computed at the very
start and very end of this script.
"""
import hashlib
import json
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_novelty as en  # noqa: E402

THIS_DIR = Path(__file__).resolve().parent
OSS_OBSERVATORY_ROOT = THIS_DIR.parent
DATA_DIR = en.DATA_DIR
CORPUS_DIR = en.CORPUS_DIR
DISCOVERY_DIR = en.DISCOVERY_DIR
ASSESSMENT_DIR = en.ASSESSMENT_DIR
METHODOLOGY_PATH = THIS_DIR / "EXTERNAL_NOVELTY_VALIDATION.md"

REAL_CANDIDATE_ID = "cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac"

# The exact four-file, fifteen-observation snapshot both existing suites
# were built and pinned against (see research_corpus/acceptance_tests.py's
# own CANONICAL_FILES / hardcoded expectations, and research_corpus's own
# generation_manifest.json "known_v1_limitations": "Only four clean Schema
# v1 days / 15 observations currently available.").
PINNED_CANONICAL_FILES = [
    "20260829_cyberbrief.json", "20260830_20260830_cyberbrief.json",
    "20260831_cyberbrief.json", "20260901_cyberbrief.json",
]
CORPUS_FILES = ["observations.csv", "case_continuity.json",
                "longitudinal_claims.json", "iad_mechanisms.json", "arc_day_state.csv"]
DISCOVERY_FILES = ["discovery_candidates.json", "suppressed_candidates.json",
                    "generation_manifest.json", "DISCOVERY_BRIEF.md"]

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


print("\n=== Pre-check hashes (real canonical + corpus + discovery artifacts) ===\n")
pre_canonical = hash_set([DATA_DIR / f for f in PINNED_CANONICAL_FILES])
pre_corpus = hash_set([CORPUS_DIR / f for f in CORPUS_FILES])
pre_discovery = hash_set([DISCOVERY_DIR / f for f in DISCOVERY_FILES])

print("\n=== Checks 1-14: methodology, artifact, record contract, traceability ===\n")

# 1. Methodology file exists.
check("1. Methodology file exists (EXTERNAL_NOVELTY_VALIDATION.md)",
      METHODOLOGY_PATH.exists())

# 2. Assessment artifact exists for the real candidate.
assessment_path = ASSESSMENT_DIR / f"{REAL_CANDIDATE_ID}.json"
check("2. Assessment artifact exists for the real candidate",
      assessment_path.exists(), str(assessment_path))

record = json.loads(assessment_path.read_text()) if assessment_path.exists() else {}

# 3. Assessment references a real Discovery Candidate ID (non-empty, matches filename).
check("3. Assessment references a real Discovery Candidate ID",
      record.get("discovery_candidate_id") == REAL_CANDIDATE_ID,
      str(record.get("discovery_candidate_id")))

# 4. Candidate ID resolves to existing discovery output.
resolved_candidate = en.find_candidate(REAL_CANDIDATE_ID)
check("4. Candidate ID resolves to an existing entry in discovery_candidates.json",
      resolved_candidate is not None)

# 5. Required ten fields all exist (and no extras).
field_errors = en.validate_assessment(record)
check("5. All ten required fields present, no unexpected fields",
      not any("missing" in e or "unexpected" in e for e in field_errors),
      str(field_errors))

# 6. Outcome is one of the four allowed values.
check("6. external_novelty_outcome is one of the four allowed values",
      record.get("external_novelty_outcome") in en.ALLOWED_OUTCOMES,
      str(record.get("external_novelty_outcome")))

# 7. No NOVEL outcome exists anywhere, and no forbidden novelty-claim language.
novel_outcome_used = record.get("external_novelty_outcome") == "NOVEL"
language_errors = [e for e in field_errors if "forbidden novelty-claim" in e]
check("7. No 'NOVEL' outcome and no forbidden novelty-claim language ('novel'/'first'/'nobody has studied this')",
      not novel_outcome_used and not language_errors, str(language_errors))

# 8. Validation date exists and is non-empty.
check("8. validation_date present and non-empty",
      bool(str(record.get("validation_date", "")).strip()))

# 9. Multiple source families are documented.
families = record.get("source_families_searched", [])
check("9. Multiple (>=2) source families documented",
      isinstance(families, list) and len(families) >= 2, str(families))

# 10. Citations/evidence are present, each with a URL.
citations = record.get("evidence_and_citations", [])
citations_have_urls = bool(citations) and all(
    isinstance(c, dict) and str(c.get("url", "")).startswith("http") for c in citations
)
check("10. Citations/evidence present, each with an http(s) URL",
      citations_have_urls, str(citations))

# 11. relationship_to_prior_work uses the conceptual-equivalence spectrum,
# not a vague yes/no.
spectrum_terms = ["exact", "conceptual equivalent", "partial overlap", "adjacent",
                   "genuinely different"]
rel_text = str(record.get("relationship_to_prior_work", "")).lower()
spectrum_hits = [t for t in spectrum_terms if t in rel_text]
check("11. relationship_to_prior_work names at least one equivalence-spectrum term",
      len(spectrum_hits) >= 1, f"hits={spectrum_hits}")

# 12. Limitations present and substantive (not a placeholder).
limitations_text = str(record.get("limitations", ""))
check("12. limitations present and substantive (>40 chars, non-placeholder)",
      len(limitations_text.strip()) > 40)

# 13. Traceability: assessment -> candidate -> corpus observations -> canonical evidence.
trace = en.resolve_candidate_trace(REAL_CANDIDATE_ID)
trace_ok = (
    trace is not None
    and len(trace["observation_evidence"]) == len(resolved_candidate["supporting_observation_ids"])
    and all(ev["source_urls"] and all(u.startswith("http") for u in ev["source_urls"])
            for ev in trace["observation_evidence"])
)
check("13. Traceability chain (assessment -> candidate -> corpus -> canonical) resolves",
      trace_ok, str(trace))

# 14. Traced observation IDs match the candidate's own recorded
# supporting_observation_ids exactly.
trace_obs_ids = sorted(ev["observation_id"] for ev in trace["observation_evidence"]) if trace else []
check("14. Traced observation IDs match the candidate's supporting_observation_ids exactly",
      trace_obs_ids == sorted(resolved_candidate["supporting_observation_ids"]),
      f"{trace_obs_ids} vs {sorted(resolved_candidate['supporting_observation_ids'])}")

print("\n=== Check 20: scope check (no forbidden infrastructure in the implementation) ===\n")

# Scan only executable code, not this module's own docstring/comments -- like
# research_discovery/acceptance_tests.py's own check #17, which excludes
# itself and the README because both legitimately *name* forbidden concepts
# in order to assert their absence. external_novelty.py's module docstring
# and inline comments do the same (documenting what is deliberately NOT
# built), so strip comments and the leading module docstring before scanning.
forbidden_terms = ["crawler", "dashboard", "workbench", "embedding", "cluster",
                   "vector_db", "vectordb", "knowledge_graph", "knowledgegraph",
                   "visualiz", "d3.js", "chart.js", "plotly", "sql", "sqlite",
                   "flask", "fastapi", "scheduler", "cron"]
raw_text = (THIS_DIR / "external_novelty.py").read_text()
no_docstrings = re.sub(r'""".*?"""', "", raw_text, flags=re.DOTALL)
no_comments = re.sub(r"#.*", "", no_docstrings)
scope_hits = [t for t in forbidden_terms if t in no_comments.lower()]
check("20. No forbidden-infrastructure terms found in external_novelty.py's actual code "
      "(docstrings/comments excluded, since they legitimately name these terms to assert absence)",
      len(scope_hits) == 0, str(scope_hits))

print("\n=== Checks 15-16: regression against existing suites (isolated temp copies) ===\n")


def make_isolated_corpus_input(tmp_root):
    """Copy exactly the pinned 4-file canonical snapshot into an isolated
    temp CyberBrief/Data/ layout, read-only from the real files. Never
    writes into the real connected folder.
    """
    data_dir = tmp_root / "CyberBrief" / "Data"
    data_dir.mkdir(parents=True)
    for fname in PINNED_CANONICAL_FILES:
        shutil.copy2(DATA_DIR / fname, data_dir / fname)
    return data_dir


# 15. Existing Research Discovery V1 acceptance tests pass, run against an
# isolated copy of the pinned corpus (never the live one).
rd_pass = None
rd_detail = ""
tmp_root_rd = Path(tempfile.mkdtemp(prefix="req12_regression_rd_"))
try:
    isolated_data_dir = make_isolated_corpus_input(tmp_root_rd)
    isolated_corpus_dir = isolated_data_dir / "research_corpus"
    isolated_corpus_dir.mkdir()
    for fname in CORPUS_FILES:
        shutil.copy2(CORPUS_DIR / fname, isolated_corpus_dir / fname)
    isolated_output_dir = isolated_data_dir / "research_discovery"

    import generate_discovery as gd  # noqa: E402
    gd.BASE = isolated_data_dir
    gd.CORPUS_DIR = isolated_corpus_dir
    gd.OUTPUT_DIR = isolated_output_dir
    # generate_discovery.py has a pre-existing, unrelated bug (out of scope to
    # fix per this task's constraints): resolve_evidence(obs, base_dir=BASE)
    # binds its base_dir default at module-import time, so reassigning the
    # gd.BASE attribute alone does not redirect calls that rely on the
    # default (evidence-traceability gate C, and any test that calls
    # resolve_evidence without an explicit base_dir). Override the bound
    # default itself, the same technique already required for
    # generate_research_corpus.generate()'s output_dir default below.
    gd.resolve_evidence.__defaults__ = (isolated_data_dir,)
    try:
        runpy.run_path(str(THIS_DIR / "acceptance_tests.py"), run_name="__main__")
        rd_pass = True
    except SystemExit as e:
        rd_pass = (e.code in (0, None))
        rd_detail = f"exit code {e.code}"
except Exception as e:
    rd_pass = False
    rd_detail = f"{type(e).__name__}: {e}"
finally:
    shutil.rmtree(tmp_root_rd, ignore_errors=True)

check("15. Existing Research Discovery V1 acceptance tests pass, run against an isolated "
      "copy of the pinned corpus (real CyberBrief/Data/research_discovery is never touched)",
      rd_pass is True, rd_detail)

# 16. Requirement 11 (Research Corpus) acceptance tests pass, run against an
# isolated copy of the pinned canonical files (never the live data plane,
# which now also contains later, legitimately-valid canonical files this
# suite's hardcoded expectations were never updated to expect).
r11_pass = None
r11_detail = ""
tmp_root_r11 = Path(tempfile.mkdtemp(prefix="req12_regression_r11_"))
try:
    isolated_data_dir = tmp_root_r11 / "CyberBrief" / "Data"
    isolated_data_dir.mkdir(parents=True)
    for fname in PINNED_CANONICAL_FILES:
        shutil.copy2(DATA_DIR / fname, isolated_data_dir / fname)
    isolated_output_dir = isolated_data_dir / "research_corpus"

    sys.path.insert(0, str(OSS_OBSERVATORY_ROOT / "research_corpus"))
    import generate_research_corpus as grc  # noqa: E402
    grc.DATA_DIR = isolated_data_dir
    grc.OUTPUT_DIR = isolated_output_dir
    # generate()'s default parameter values were already bound at import
    # time to the real paths; research_corpus/acceptance_tests.py's main()
    # calls generate(grc.DATA_DIR) explicitly (so the patched attribute
    # above covers data_dir), but never passes output_dir, so that default
    # must be corrected directly.
    grc.generate.__defaults__ = (isolated_data_dir, isolated_output_dir)
    try:
        runpy.run_path(str(OSS_OBSERVATORY_ROOT / "research_corpus" / "acceptance_tests.py"),
                        run_name="__main__")
        r11_pass = True
    except SystemExit as e:
        r11_pass = (e.code in (0, None))
        r11_detail = f"exit code {e.code}"
except Exception as e:
    r11_pass = False
    r11_detail = f"{type(e).__name__}: {e}"
finally:
    shutil.rmtree(tmp_root_r11, ignore_errors=True)

check("16. Requirement 11 (Research Corpus V1) acceptance tests pass, run against an "
      "isolated copy of the pinned canonical snapshot (real CyberBrief/Data/research_corpus "
      "is never touched)",
      r11_pass is True, r11_detail)

print("\n=== Checks 17-19: this addition (and running its regression checks) mutated nothing real ===\n")

post_canonical = hash_set([DATA_DIR / f for f in PINNED_CANONICAL_FILES])
post_corpus = hash_set([CORPUS_DIR / f for f in CORPUS_FILES])
post_discovery = hash_set([DISCOVERY_DIR / f for f in DISCOVERY_FILES])

check("17. Canonical CyberBrief files unchanged by this addition and its verification",
      pre_canonical == post_canonical)
check("18. Research Corpus V1 unchanged by this addition and its verification",
      pre_corpus == post_corpus)
check("19. Existing discovery candidate artifacts unchanged by this addition and its verification",
      pre_discovery == post_discovery)

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
