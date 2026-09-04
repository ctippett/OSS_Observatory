#!/usr/bin/env python3
"""
Requirement 11 -- Research Corpus V1 acceptance tests.

Covers Task 9 (A-Q) and Task 10 (failure safety) from the V1 implementation
request. Read-only against the real canonical corpus; failure-safety tests
run against a throwaway temp copy, never against real CyberBrief/Data.

Run: python3 acceptance_tests.py
Exits non-zero on any failure.
"""
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_research_corpus as grc  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def load_output(out_dir: Path):
    rows = list(csv.DictReader((out_dir / "observations.csv").open()))
    case_rels = json.loads((out_dir / "case_continuity.json").read_text())
    claims = json.loads((out_dir / "longitudinal_claims.json").read_text())
    arc_state = list(csv.DictReader((out_dir / "arc_day_state.csv").open()))
    manifest = json.loads((out_dir / "generation_manifest.json").read_text())
    return rows, case_rels, claims, arc_state, manifest


def canonical_lookup(row, data_dir: Path):
    doc = json.loads((data_dir / row["source_file"]).read_text())
    return doc["items"][int(row["item_index"])]


def main():
    data_dir = grc.DATA_DIR
    out_dir, manifest = grc.generate(data_dir)
    rows, case_rels, claims, arc_state, manifest = load_output(out_dir)

    # snapshot canonical file hashes before/after, to prove no mutation (Q)
    canonical_files = ["20260829_cyberbrief.json", "20260830_20260830_cyberbrief.json",
                        "20260831_cyberbrief.json", "20260901_cyberbrief.json"]
    import hashlib
    before = {f: hashlib.sha256((data_dir / f).read_bytes()).hexdigest() for f in canonical_files}

    # ---- A. Observation count = 15 ----
    check("A. Observation count == 15", len(rows) == 15, f"got {len(rows)}")

    # ---- B. One item = one row (row count == sum of items across included files) ----
    total_items = sum(len(json.loads((data_dir / f).read_text())["items"]) for f in manifest["files_included"])
    check("B. One item == one row", len(rows) == total_items, f"rows={len(rows)} items={total_items}")

    # ---- C. Both brief_date and event_date preserved, and can differ ----
    has_both = all(r["brief_date"] and r["event_date"] for r in rows)
    can_differ = any(r["brief_date"] != r["event_date"] for r in rows)
    check("C. brief_date and event_date both present", has_both)
    check("C. brief_date and event_date are independent (at least one differs)", can_differ)

    # ---- D. source_file + item_index resolves back to correct canonical observation ----
    resolves = True
    for r in rows:
        try:
            item = canonical_lookup(r, data_dir)
            if item["title"] != r["title"]:
                resolves = False
                break
        except Exception:
            resolves = False
            break
    check("D. Evidence pointer resolves to correct canonical observation", resolves)

    # ---- E. Arc normalization reproduces demonstrated results ----
    arc22 = next(r for r in rows if r["arc_code"] == "2.2")
    check("E. Arc 2.2 has no invented label", arc22["arc_label"] == "", f"got {arc22['arc_label']!r}")
    bare24 = next(r for r in rows if r["source_file"] == "20260829_cyberbrief.json" and r["item_index"] == "0")
    check("E. Bare arc 2.4 label inferred from sibling", bare24["arc_label_inferred"] == "True",
          f"got {bare24['arc_label_inferred']!r}")
    check("E. Inferred label text correct", bare24["arc_label"] == "CyberCrime & Adversary Economics")

    # ---- F. Domain-derived population reproduces demonstrated sparse representation ----
    pop_actor = sum(1 for r in rows if r["actor_context"])
    pop_sector = sum(1 for r in rows if r["sector_context"])
    pop_discipline = sum(1 for r in rows if r["security_discipline"])
    check("F. actor_context population == 6", pop_actor == 6, f"got {pop_actor}")
    check("F. sector_context population == 8", pop_sector == 8, f"got {pop_sector}")
    check("F. security_discipline population == 3", pop_discipline == 3, f"got {pop_discipline}")
    none_populated = sum(1 for r in rows if not r["actor_context"] and not r["sector_context"] and not r["security_discipline"])
    check("F. Exactly 2 observations populate none of the three dims", none_populated == 2, f"got {none_populated}")
    obs10 = next(r for r in rows if r["source_file"] == "20260831_cyberbrief.json" and r["item_index"] == "3")
    check("F. obs10 documented two-value discipline ambiguity preserved",
          obs10["security_discipline"] == "AppSec; Vulnerability Governance")

    # ---- G. IAD dimension frequencies reproduce demonstrated counts ----
    dim_counts = {d: sum(1 for r in rows if r[f"iad_dim_{d}"] == "True") for d in grc.DIMENSIONS}
    expected = {"Actors": 10, "Rules-in-Use": 6, "Arena": 3, "Incentives": 3,
                "Interactions": 1, "Outcomes": 7, "Levers": 4}
    check("G. IAD dimension frequencies match", dim_counts == expected, f"got {dim_counts}")

    # ---- H. Signal Type x Half-Life reproduces prior result ----
    from collections import Counter
    sthl = Counter((r["signal_type"], r["half_life"]) for r in rows)
    check("H. Structural Shift always Long", sthl[("Structural Shift", "Long")] == 4 and
          all(k[1] != "Long" or k[0] == "Structural Shift" for k in sthl if sthl[k]))
    check("H. Incident Short=6 Medium=4", sthl[("Incident", "Short")] == 6 and sthl[("Incident", "Medium")] == 4)

    # ---- I. AI Impact x Signal Type reproduces prior result ----
    aist = Counter((r["ai_impact"], r["signal_type"]) for r in rows)
    check("I. AI impact distribution matches",
          aist[("Amplifying", "Structural Shift")] == 1 and
          aist[("Governing", "Policy Evolution")] == 1 and
          aist[("Targeted", "Incident")] == 1)

    # ---- J. Arc x Signal/Half-Life queries work ----
    arc24_rows = [r for r in rows if r["arc_code"] == "2.4"]
    check("J. Arc 2.4 has 7 members", len(arc24_rows) == 7, f"got {len(arc24_rows)}")

    # ---- K. Domain cross-dimensional queries work ----
    crit_infra_long = [r for r in rows if r["sector_context"] == "Critical Infrastructure" and r["half_life"] == "Long"]
    check("K. Critical Infrastructure sector has 2 Long half-life obs", len(crit_infra_long) == 2,
          f"got {len(crit_infra_long)}")

    # ---- L. Berlin/Rhysida case continuity reconstructable ----
    check("L. Exactly one case-continuity relationship", len(case_rels) == 1)
    rel = case_rels[0]
    check("L. Relationship points from 09-01 obs0 back to 08-29 obs0",
          rel["later_observation"]["source_file"] == "20260901_cyberbrief.json" and
          rel["earlier_observation"]["source_file"] == "20260829_cyberbrief.json")
    check("L. Relationship epistemic status is Observed", rel["epistemic_status"] == "Observed")

    # ---- M. Longitudinal claims retrievable by arc, date, evidence, status ----
    arc24_claims = [c for c in claims if c["arc_code"] == "2.4"]
    check("M. 4 claims filed under arc 2.4", len(arc24_claims) == 4, f"got {len(arc24_claims)}")
    by_status = Counter(c["epistemic_status"] for c in claims)
    check("M. Claims span all three epistemic statuses",
          by_status["Observed"] > 0 and by_status["Analytical Inference"] > 0 and by_status["Hypothesis"] > 0,
          f"got {dict(by_status)}")
    check("M. Every claim has at least one evidence pointer", all(len(c["evidence"]) >= 1 for c in claims))

    # ---- N. Day x arc state == 6/2/8 exactly ----
    state_counts = Counter(r["state"] for r in arc_state)
    check("N. material=6 no_material_development=2 unknown=8",
          state_counts["material"] == 6 and state_counts["no_material_development"] == 2 and
          state_counts["unknown"] == 8, f"got {dict(state_counts)}")

    # ---- O. No unknown silently converted to no_material_development ----
    # cross-check: every 'unknown' cell must correspond to a day where longitudinal_arcs
    # has no matching key AND no item with that arc_code
    ok = True
    for row in arc_state:
        if row["state"] == "unknown":
            doc = json.loads((data_dir / next(f for f in manifest["files_included"]
                                                if json.loads((data_dir / f).read_text())["date"] == row["brief_date"])).read_text())
            long_arcs = doc.get("longitudinal_arcs") or {}
            has_key = any(k.split()[0] == row["arc_code"] for k in long_arcs)
            has_item = any(it.get("arc", "").split()[0:1] == [row["arc_code"]] for it in doc["items"])
            if has_key or has_item:
                ok = False
    check("O. Every 'unknown' cell genuinely has no longitudinal_arcs entry or item", ok)

    # ---- P. Three structured results trace to canonical evidence ----
    p1 = next(r for r in rows if r["source_file"] == "20260830_20260830_cyberbrief.json" and r["item_index"] == "1")
    p1_canon = canonical_lookup(p1, data_dir)
    check("P1 (IAD). obs6 traces to canonical QTFY item with source_urls",
          p1_canon["title"].startswith("DOJ and FBI Seize") and len(p1_canon["source_urls"]) >= 1)
    p2 = next(r for r in rows if r["sector_context"] == "Aviation")
    p2_canon = canonical_lookup(p2, data_dir)
    check("P2 (domain). Aviation-sector obs traces to canonical Manchester item with source_urls",
          "Manchester" in p2_canon["title"] and len(p2_canon["source_urls"]) >= 1)
    p3 = next(r for r in rows if r["arc_code"] == "2.4" and r["source_file"] == "20260830_20260830_cyberbrief.json"
              and r["item_index"] == "0")
    p3_canon = canonical_lookup(p3, data_dir)
    check("P3 (arc). Arc 2.4 Healthcare-sector obs traces to canonical McKesson item with source_urls",
          "McKesson" in p3_canon["title"] and len(p3_canon["source_urls"]) >= 1)

    # ---- Q. No canonical CyberBrief JSON modified ----
    after = {f: hashlib.sha256((data_dir / f).read_bytes()).hexdigest() for f in canonical_files}
    check("Q. No canonical file hash changed", before == after)

    # ================= Task 10: failure safety =================
    print("\n--- Failure safety tests ---")

    # 10.1 malformed/non-v1 input does not silently enter corpus
    with tempfile.TemporaryDirectory() as tmp:
        tmp_data = Path(tmp) / "Data"
        tmp_data.mkdir()
        for f in manifest["files_included"]:
            shutil.copy(data_dir / f, tmp_data / f)
        (tmp_data / "malformed.json").write_text("{not valid json")
        (tmp_data / "non_v1_shape.json").write_text(json.dumps({"totally": "wrong shape"}))
        _, test_manifest = grc.generate(tmp_data, Path(tmp) / "out")
        excluded_names = {e["file"] for e in test_manifest["files_excluded"]}
        check("10.1 Malformed JSON excluded, not silently included", "malformed.json" in excluded_names)
        check("10.1 Non-v1-shaped JSON excluded, not silently included", "non_v1_shape.json" in excluded_names)
        check("10.1 The 4 genuinely clean files still included",
              set(test_manifest["files_included"]) == set(manifest["files_included"]))

    # 10.2 generation failure does not overwrite a known-good corpus
    with tempfile.TemporaryDirectory() as tmp:
        tmp_data = Path(tmp) / "Data"
        tmp_data.mkdir()
        for f in manifest["files_included"]:
            shutil.copy(data_dir / f, tmp_data / f)
        good_out = Path(tmp) / "out"
        grc.generate(tmp_data, good_out)
        good_snapshot = (good_out / "observations.csv").read_text()
        # simulate a failure: corrupt the source data enough that validation raises inside build,
        # but do it in a way that raises BEFORE write_corpus is called (build_corpus itself doesn't
        # write anything -- only generate()'s promotion step touches disk), by monkeypatching
        # case_continuity_relationships to return an invalid status and confirm the assertion
        # inside generate() raises without touching good_out.
        orig = grc.case_continuity_relationships
        grc.case_continuity_relationships = lambda: [{"later_observation": {}, "earlier_observation": {},
                                                        "evidence_citation": "x", "epistemic_status": "INVALID"}]
        raised = False
        try:
            grc.generate(tmp_data, good_out)
        except (ValueError, AssertionError):
            raised = True
        finally:
            grc.case_continuity_relationships = orig
        check("10.2 Invalid epistemic status raises instead of writing bad output", raised)
        check("10.2 Known-good corpus untouched after failed run",
              (good_out / "observations.csv").read_text() == good_snapshot)

    # 10.3 missing/ambiguous derived values remain null, not invented
    unmapped = [r for r in rows if r["domain_original"] in
                ("Hardware Supply Chain / IoT", "AI Policy, Governance & Ethical Integrity")]
    check("10.3 Ambiguous domains remain unpopulated, not guessed",
          all(not r["actor_context"] and not r["sector_context"] and not r["security_discipline"]
              for r in unmapped))

    # 10.4 evidence pointers resolve correctly (already covered by D, re-affirm)
    check("10.4 Evidence pointers resolve (same as D)", resolves)

    # 10.5 invalid epistemic status rejected
    try:
        grc.validate_epistemic_status("Definitely Confirmed", "test")
        rejected = False
    except ValueError:
        rejected = True
    check("10.5 Invalid epistemic status value rejected", rejected)

    print(f"\n{len(FAILURES)} failing check(s)" if FAILURES else "\nALL CHECKS PASSED")
    if FAILURES:
        for f in FAILURES:
            print("  FAILED:", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
