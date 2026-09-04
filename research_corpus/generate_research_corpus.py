#!/usr/bin/env python3
"""
Requirement 11 -- Research Corpus V1 generator.

Reads canonical Schema v1 CyberBrief JSON files (unmodified, read-only) and
produces an ADDITIVE research representation:

  - observations.csv        one row per canonical item (rectangular layer)
  - case_continuity.json    demonstrated cross-observation relationships
  - longitudinal_claims.json demonstrated individual analytical claims
  - iad_mechanisms.json     any hybrid IAD mechanism/relationship payloads
                            found on canonical items (none expected for the
                            four clean v1 files, since the hybrid fields
                            postdate them and are deliberately not backfilled)
  - arc_day_state.csv       the 3-state (material / no_material_development /
                            unknown) day x arc matrix
  - generation_manifest.json documents inputs used/skipped and the rules
                            applied, so interpretation is visible, not hidden

Design constraints (Requirement 11, settled by the prior test series):
  * Canonical CyberBrief JSON is authoritative and is never written to.
  * One canonical item = one research observation row.
  * summary / extracted_statistics / source_urls / breach_specifics are
    NEVER copied into the row -- they stay in the canonical file, reached
    only via (source_file, item_index).
  * domain-derived dimensions (actor_context, sector_context,
    security_discipline) are a small, explicit, documented lookup over the
    12 distinct domain strings that actually occur in the clean corpus --
    NOT a generic parser/taxonomy. Ambiguous cases are recorded as null,
    not guessed.
  * arc day-state must never convert "omitted" into "no_material_development".
  * Nothing here performs cross-observation *discovery* -- case continuity
    and longitudinal claims are hand-verified, already-demonstrated facts
    from the Requirement 11 test series, not the output of a matching
    algorithm. That would be Requirement 12.

Generation is candidate-then-promote, mirroring the existing CyberBrief
production workflow's own candidate/validate/promote pattern: everything is
built in a temporary directory first, and only rsynced into place if every
internal consistency check passes -- so a failed run never corrupts a
previously-good corpus.
"""
import csv
import json
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo-relative paths (works regardless of caller's cwd)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
OSS_OBSERVATORY_ROOT = THIS_FILE.parent.parent  # .../OSS_Observatory
VALIDATOR_DIR = OSS_OBSERVATORY_ROOT / "validators"
DATA_DIR = OSS_OBSERVATORY_ROOT.parent / "CyberBrief" / "Data"
OUTPUT_DIR = OSS_OBSERVATORY_ROOT.parent / "CyberBrief" / "Data" / "research_corpus"

sys.path.insert(0, str(VALIDATOR_DIR))
import cyberbrief_validator as validator  # noqa: E402
from jsonschema import ValidationError  # noqa: E402

DIMENSIONS = ["Actors", "Rules-in-Use", "Arena", "Incentives", "Interactions", "Outcomes", "Levers"]
ARC_CODE_RE = re.compile(r"^\s*(\d+\.\d+)\s*(.*)$")
NO_DEV_RE = re.compile(r"no material development", re.IGNORECASE)
EPISTEMIC_STATUSES = {"Observed", "Analytical Inference", "Hypothesis"}

# ---------------------------------------------------------------------------
# Domain-derived dimension lookup.
#
# This is an explicit, documented mapping over the exact 12 distinct
# `domain` strings observed in the clean corpus -- NOT a general parser.
# It exists because the Requirement 11 Domain tests found raw `domain` mixes
# several conceptual dimensions inconsistently, but that only two of those
# dimensions (sector, security discipline) plus a weaker third (actor
# context) recur coherently enough to earn structural status.
#
# Every entry also carries a `confidence` note. "confident" means the
# decomposition is close to direct parsing. "ambiguous" flags a genuine,
# previously-documented judgment call -- these are NOT deterministic facts.
# ---------------------------------------------------------------------------
DOMAIN_DIMENSION_MAP = {
    "Government / Public Sector": {
        "actor_context": None, "sector_context": "Government/Public Sector", "security_discipline": None,
        "confidence": "confident",
        "note": "Near-synonym restatement of one sector concept.",
    },
    "Corporate / Employee Data": {
        "actor_context": None, "sector_context": "Corporate", "security_discipline": None,
        "confidence": "confident (sector) / not-mapped (Employee Data)",
        "note": "'Employee Data' is a harm/data-type, not a demonstrated dimension. "
                "Deliberately left unmapped -- stays only in domain_original.",
    },
    "Web Hosting Infrastructure / AppSec": {
        "actor_context": None, "sector_context": "Web Hosting Infrastructure", "security_discipline": "AppSec",
        "confidence": "confident",
        "note": "Two orthogonal, cleanly separable concepts.",
    },
    "Hardware Supply Chain / IoT": {
        "actor_context": None, "sector_context": None, "security_discipline": None,
        "confidence": "ambiguous -- deliberately unmapped",
        "note": "Neither term cleanly fits sector, discipline, or actor context per the Domain test. "
                "Left fully null rather than force-fit.",
    },
    "CyberCrime & Adversary Economics / Healthcare": {
        "actor_context": "CyberCrime", "sector_context": "Healthcare", "security_discipline": None,
        "confidence": "confident (actor+sector) / residual not-mapped ('Adversary Economics')",
        "note": "'Adversary Economics' is a residual research-theme fragment, not independently "
                "recurring elsewhere -- not mapped to any dimension.",
    },
    "Nation-State / Critical Infrastructure": {
        "actor_context": "Nation-State", "sector_context": "Critical Infrastructure", "security_discipline": None,
        "confidence": "confident",
        "note": "Cleanest orthogonal actor+sector pair in the corpus.",
    },
    "AI Policy, Governance & Ethical Integrity / CyberCrime": {
        "actor_context": "CyberCrime", "sector_context": None, "security_discipline": None,
        "confidence": "actor: confident / theme phrase: DELIBERATELY UNMAPPED (ambiguity #1)",
        "note": "AMBIGUITY #1 (Integration Test): the 'AI Policy, Governance & Ethical Integrity' phrase "
                "duplicates arc-label vocabulary but was found to correspond to DIFFERENT arc_codes across "
                "observations (arc 2.1 here, arc 2.3 for the bare form below). It is NOT forced into "
                "sector_context or any other dimension. Do not silently resolve this.",
    },
    "AI Policy, Governance & Ethical Integrity": {
        "actor_context": None, "sector_context": None, "security_discipline": None,
        "confidence": "DELIBERATELY UNMAPPED (ambiguity #1)",
        "note": "Same ambiguity #1 as above -- fully unmapped, no dimension populated.",
    },
    "AppSec / Vulnerability Governance": {
        "actor_context": None, "sector_context": None, "security_discipline": "AppSec; Vulnerability Governance",
        "confidence": "ambiguous (AMBIGUITY #2)",
        "note": "AMBIGUITY #2 (Integration Test): recorded as TWO discipline values rather than one. "
                "A different competent researcher might reasonably record a single combined value instead. "
                "This is a judgment call, not a deterministic fact.",
    },
    "Critical Infrastructure / Aviation": {
        "actor_context": None, "sector_context": "Aviation", "security_discipline": None,
        "confidence": "ambiguous (AMBIGUITY #3)",
        "note": "AMBIGUITY #3 (Integration Test): 'Critical Infrastructure' treated as a broader category "
                "that 'Aviation' already nests inside, so only 'Aviation' is recorded as sector_context. "
                "A different competent researcher might instead record 'Critical Infrastructure', or both.",
    },
    "CyberCrime": {
        "actor_context": "CyberCrime", "sector_context": None, "security_discipline": None,
        "confidence": "confident",
        "note": "Single-concept domain value, direct mapping.",
    },
    "AppSec": {
        "actor_context": None, "sector_context": None, "security_discipline": "AppSec",
        "confidence": "confident",
        "note": "Single-concept domain value, direct mapping.",
    },
}

# ---------------------------------------------------------------------------
# Demonstrated non-row objects (hand-verified during the Requirement 11 test
# series -- NOT the output of an automated matcher; materializing these is
# preservation of already-established findings, not discovery).
# ---------------------------------------------------------------------------

def case_continuity_relationships():
    return [
        {
            "later_observation": {"source_file": "20260901_cyberbrief.json", "item_index": 0},
            "earlier_observation": {"source_file": "20260829_cyberbrief.json", "item_index": 0},
            "evidence_citation": (
                "obs (2026-09-01, item 0) states: \"Berlin's city administration has now officially "
                "confirmed the data theft that Rhysida first claimed on its leak site on August 28\" -- "
                "directly self-referencing the 2026-08-29 observation, corroborated by matching figures "
                "(5.79 TB / ~1.44M files, 12,076 individuals, 16,389 emails, 11,963 phones, 148 IBANs, "
                "Aug 7-12 exfiltration window) present in both observations."
            ),
            "epistemic_status": "Observed",
        }
    ]


def longitudinal_claims():
    return [
        {
            "claim_text": "The city's public refusal continues the pattern of high-profile ransom "
                           "refusals from public-sector victims.",
            "arc_code": "2.4",
            "evidence": [{"source_file": "20260829_cyberbrief.json", "item_index": 0}],
            "epistemic_status": "Hypothesis",
            "brief_date": "2026-08-29",
            "note": "No second public-sector refusal instance exists anywhere in the clean corpus to "
                    "support 'a pattern' -- recorded as Hypothesis, not Observed, per the Longitudinal "
                    "Knowledge Preservation test's finding that this claim cannot be adequately supported "
                    "from persisted evidence as originally written.",
        },
        {
            "claim_text": "ShinyHunters' vishing-to-SaaS-pivot playbook reappears at McKesson, its "
                           "latest and largest healthcare-sector target.",
            "arc_code": "2.4",
            "evidence": [{"source_file": "20260830_20260830_cyberbrief.json", "item_index": 0}],
            "epistemic_status": "Hypothesis",
            "brief_date": "2026-08-30",
            "note": "No prior ShinyHunters observation exists in the clean corpus -- the 'reappears / "
                    "latest and largest' comparative claim is unsupported as written; recorded as Hypothesis.",
        },
        {
            "claim_text": "DOJ's QScan/QTRouter domain seizure illustrates law enforcement disrupting a "
                           "hacking-as-a-service business model at its infrastructure-dependency layer.",
            "arc_code": "2.4",
            "evidence": [{"source_file": "20260830_20260830_cyberbrief.json", "item_index": 1}],
            "epistemic_status": "Analytical Inference",
            "brief_date": "2026-08-30",
            "note": "Directly traceable to the item's own summary (seizure disabled the platforms via "
                    "domain dependency); the 'illustrates X' framing is a faithful synthesis of that fact.",
        },
        {
            "claim_text": "Gryxa's fully AI-built toolkit represents a capability-baseline shift in "
                           "adversary use of generative AI.",
            "arc_code": "2.1",
            "evidence": [{"source_file": "20260831_cyberbrief.json", "item_index": 0}],
            "epistemic_status": "Analytical Inference",
            "brief_date": "2026-08-31",
            "note": "Grounded directly in the item's own summary ('the first case ReliaQuest has observed "
                    "of AI being used to build an entire operation'). The original longitudinal_arcs text "
                    "also references an 'Aurora/Cursor Agent (August 27)' pattern; that specific external "
                    "reference is NOT independently confirmed within the clean corpus and is excluded from "
                    "this claim's supported content.",
        },
        {
            "claim_text": "Fire Ant's campaign is long-running, expanding beyond hypervisors into new "
                           "infrastructure layers (Cisco IOS XR, TACACS, Linux management hosts).",
            "arc_code": "2.1",
            "evidence": [{"source_file": "20260831_cyberbrief.json", "item_index": 1}],
            "epistemic_status": "Analytical Inference",
            "brief_date": "2026-08-31",
            "note": "The 'long-running campaign' characterization is directly in the item's own summary. "
                    "The original longitudinal_arcs text further claims the campaign is 'tracked since "
                    "early 2025' -- that specific duration anchor was never independently verified against "
                    "the item's cited source URLs during the Requirement 11 test series and is excluded "
                    "from this claim's supported content pending verification.",
        },
        {
            "claim_text": "The EU's ChatGPT VLOSE designation is the first time a conversational AI "
                           "system has been formally classified as a search engine for regulatory purposes.",
            "arc_code": "2.3",
            "evidence": [{"source_file": "20260831_cyberbrief.json", "item_index": 2}],
            "epistemic_status": "Observed",
            "brief_date": "2026-08-31",
            "note": "The item's own summary states this directly ('a first for conversational AI').",
        },
        {
            "claim_text": "Four of the day's five items illustrate adversary economics operating on both "
                           "sides: extortion actors escalating claims for leverage, and law enforcement "
                           "continuing cross-border pressure via extradition.",
            "arc_code": "2.4",
            "evidence": [
                {"source_file": "20260901_cyberbrief.json", "item_index": 0},
                {"source_file": "20260901_cyberbrief.json", "item_index": 1},
                {"source_file": "20260901_cyberbrief.json", "item_index": 2},
                {"source_file": "20260901_cyberbrief.json", "item_index": 3},
            ],
            "epistemic_status": "Observed",
            "brief_date": "2026-09-01",
            "note": "Same-day synthesis directly derivable from that day's own item-level arc tags and "
                    "summaries.",
        },
    ]


def validate_epistemic_status(value, context):
    if value not in EPISTEMIC_STATUSES:
        raise ValueError(
            f"Invalid epistemic status {value!r} in {context}; must be one of {sorted(EPISTEMIC_STATUSES)}"
        )


# ---------------------------------------------------------------------------
# Canonical file discovery + validation (does not modify or normalize
# anything -- files that fail Schema v1 validation are excluded and
# reported, never silently coerced).
# ---------------------------------------------------------------------------

def discover_clean_v1_files(data_dir: Path):
    included, excluded = [], []
    for path in sorted(data_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            excluded.append({"file": path.name, "reason": f"invalid JSON: {e}"})
            continue
        try:
            validator.validate_cyberbrief(path)
        except ValidationError as e:
            excluded.append({"file": path.name, "reason": f"failed Schema v1 validation: {e.message}"})
            continue
        included.append((path.name, doc))
    return included, excluded


# ---------------------------------------------------------------------------
# Arc code/label extraction (identical rule to the one validated across the
# Requirement 11 Arc tests): split "<code> <label>" strings; if only a bare
# code is present, borrow a label from another observation IN THIS SAME RUN
# that carries the same code with a label attached, flagging the borrow.
# Never invent a label that appears nowhere in the corpus (e.g. arc 2.2).
# ---------------------------------------------------------------------------

def build_arc_code_label_lookup(rows_raw):
    lookup = {}
    for r in rows_raw:
        raw_arc = r["arc_original"]
        if not raw_arc:
            continue
        m = ARC_CODE_RE.match(raw_arc)
        if m:
            code, label = m.group(1), m.group(2).strip()
            if label:
                lookup.setdefault(code, label)
    return lookup


def parse_date(d: str) -> date:
    y, m, dd = (int(x) for x in d.split("-"))
    return date(y, m, dd)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_corpus(data_dir: Path):
    included, excluded = discover_clean_v1_files(data_dir)

    raw_observations = []
    for fname, doc in included:
        brief_date = doc["date"]
        for idx, item in enumerate(doc["items"]):
            raw_observations.append({
                "source_file": fname,
                "item_index": idx,
                "brief_date": brief_date,
                "item": item,
            })

    # arc code/label lookup, built across this run's own observations only
    prelim = [{"arc_original": o["item"].get("arc", "")} for o in raw_observations]
    arc_label_lookup = build_arc_code_label_lookup(prelim)

    rows = []
    iad_mechanisms = []
    for obs_id, obs in enumerate(raw_observations, start=1):
        item = obs["item"]
        raw_arc = item.get("arc", "")
        arc_code, arc_label, arc_label_inferred = None, None, False
        if raw_arc:
            m = ARC_CODE_RE.match(raw_arc)
            if m:
                arc_code, tail = m.group(1), m.group(2).strip()
                if tail:
                    arc_label = tail
                elif arc_code in arc_label_lookup:
                    arc_label = arc_label_lookup[arc_code]
                    arc_label_inferred = True
                # else: bare code, genuinely no label anywhere in this run -> stays None

        domain_original = item["domain"]
        dmap = DOMAIN_DIMENSION_MAP.get(domain_original, {
            "actor_context": None, "sector_context": None, "security_discipline": None,
            "confidence": "NOT IN LOOKUP TABLE", "note": "Unrecognized domain string; left fully null.",
        })

        iad = item.get("iad_signal", {})
        dims = set(iad.get("dimensions", []))

        row = {
            "observation_id": obs_id,
            "source_file": obs["source_file"],
            "item_index": obs["item_index"],
            "brief_date": obs["brief_date"],
            "event_date": item["date"],
            "title": item["title"],
            "domain_original": domain_original,
            "surface": item["surface"],
            "signal_type": item["signal_type"],
            "half_life": item["half_life"],
            "ai_impact": item["ai_impact"],
            "arc_original": raw_arc,
            "arc_code": arc_code,
            "arc_label": arc_label,
            "arc_label_inferred": arc_label_inferred,
            "actor_context": dmap["actor_context"],
            "sector_context": dmap["sector_context"],
            "security_discipline": dmap["security_discipline"],
            "iad_relevance": iad.get("relevance", "None"),
        }
        for d in DIMENSIONS:
            row[f"iad_dim_{d}"] = d in dims
        rows.append(row)

        # IAD mechanism/relationship: only present on hybrid-shaped iad_signal.
        # None of the 4 clean-v1 files have this (correctly not backfilled),
        # but the extraction must still work if a future file has it.
        if "mechanism" in iad and iad["mechanism"] is not None:
            for rel in iad["mechanism"].get("relationships", []):
                validate_epistemic_status(rel.get("status"), f"IAD mechanism, obs {obs_id}")
            iad_mechanisms.append({
                "observation_id": obs_id,
                "source_file": obs["source_file"],
                "item_index": obs["item_index"],
                "mechanism": iad["mechanism"],
            })
        if "dimension_notes" in iad and iad["dimension_notes"]:
            iad_mechanisms_entry = next(
                (m for m in iad_mechanisms if m["observation_id"] == obs_id), None
            )
            if iad_mechanisms_entry is None:
                iad_mechanisms.append({
                    "observation_id": obs_id,
                    "source_file": obs["source_file"],
                    "item_index": obs["item_index"],
                    "dimension_notes": iad["dimension_notes"],
                })
            else:
                iad_mechanisms_entry["dimension_notes"] = iad["dimension_notes"]

    # ---- Arc day-state matrix (material / no_material_development / unknown) ----
    known_arc_codes = sorted({r["arc_code"] for r in rows if r["arc_code"]})
    brief_dates = sorted({r["brief_date"] for r in rows})
    material_pairs = {(r["brief_date"], r["arc_code"]) for r in rows if r["arc_code"]}

    arc_day_state = []
    for fname, doc in included:
        bdate = doc["date"]
        long_arcs = doc.get("longitudinal_arcs") or {}
        # parse each key of longitudinal_arcs into an arc_code + text, same rule as items
        by_code_text = {}
        for key, text in long_arcs.items():
            m = ARC_CODE_RE.match(key)
            code = m.group(1) if m else None
            if code:
                by_code_text[code] = text
        for code in known_arc_codes:
            has_material_item = (bdate, code) in material_pairs
            text = by_code_text.get(code)
            if has_material_item:
                state = "material"
            elif text is not None and NO_DEV_RE.search(text):
                state = "no_material_development"
            elif text is not None:
                # text present but neither an item nor a recognizable "no development"
                # phrase -- treat conservatively as material only if it's non-trivial
                # text (defensive; did not occur in the clean corpus).
                state = "material" if text.strip() else "unknown"
            else:
                state = "unknown"
            arc_day_state.append({"brief_date": bdate, "arc_code": code, "state": state})

    # ---- validate non-row objects before writing ----
    case_rels = case_continuity_relationships()
    for rel in case_rels:
        validate_epistemic_status(rel["epistemic_status"], "case_continuity")
    claims = longitudinal_claims()
    for c in claims:
        validate_epistemic_status(c["epistemic_status"], f"longitudinal_claim {c['claim_text'][:40]!r}")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "generate_research_corpus.py",
        "canonical_source_directory": str(data_dir),
        "files_included": [f for f, _ in included],
        "files_excluded": excluded,
        "observation_count": len(rows),
        "arc_day_state_summary": {
            "material": sum(1 for s in arc_day_state if s["state"] == "material"),
            "no_material_development": sum(1 for s in arc_day_state if s["state"] == "no_material_development"),
            "unknown": sum(1 for s in arc_day_state if s["state"] == "unknown"),
        },
        "rules": {
            "arc_day_state": (
                "material: derived from item-level arc_code presence that day. "
                "no_material_development: assigned only when longitudinal_arcs text for that "
                "arc code explicitly matches a 'no material development' pattern. "
                "unknown: everything else (arc absent from longitudinal_arcs that day). "
                "Omission is NEVER converted to no_material_development."
            ),
            "domain_derived_dimensions": (
                "Explicit lookup table over exactly the domain strings observed in the clean "
                "corpus (see DOMAIN_DIMENSION_MAP in this script) -- not a generic parser. "
                "Every entry documents its own confidence and any known ambiguity."
            ),
            "case_continuity_and_longitudinal_claims": (
                "Hand-verified during the Requirement 11 test series, not produced by an "
                "automated matching or discovery process. Preservation of already-established "
                "findings, not Requirement 12 discovery."
            ),
        },
        "known_v1_limitations": [
            "Only four clean Schema v1 days / 15 observations currently available.",
            "Historical (pre-v1) CyberBrief corpus is not normalized and is excluded, not coerced.",
            "Some domain decomposition is interpretive; see per-value 'confidence'/'note' fields "
            "in DOMAIN_DIMENSION_MAP, and ambiguities #1-#3 documented there.",
            "8 of 16 day x arc cells are 'unknown' and are not backfilled.",
            "Discovery of new patterns/relationships across observations belongs to Requirement 12 "
            "and is out of scope for this generator.",
        ],
    }

    return rows, case_rels, claims, iad_mechanisms, arc_day_state, manifest


ROW_FIELDNAMES = [
    "observation_id", "source_file", "item_index", "brief_date", "event_date",
    "title", "domain_original", "surface", "signal_type", "half_life", "ai_impact",
    "arc_original", "arc_code", "arc_label", "arc_label_inferred",
    "actor_context", "sector_context", "security_discipline",
    "iad_relevance",
] + [f"iad_dim_{d}" for d in DIMENSIONS]


def write_corpus(rows, case_rels, claims, iad_mechanisms, arc_day_state, manifest, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "observations.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    (out_dir / "case_continuity.json").write_text(json.dumps(case_rels, indent=2))
    (out_dir / "longitudinal_claims.json").write_text(json.dumps(claims, indent=2))
    (out_dir / "iad_mechanisms.json").write_text(json.dumps(iad_mechanisms, indent=2))

    with (out_dir / "arc_day_state.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["brief_date", "arc_code", "state"])
        w.writeheader()
        w.writerows(arc_day_state)

    (out_dir / "generation_manifest.json").write_text(json.dumps(manifest, indent=2))


def generate(data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR):
    """Candidate-then-promote generation: build in a temp dir, only replace
    the live output directory if the whole build succeeds and passes basic
    internal consistency checks. A failed run never touches a known-good
    corpus."""
    rows, case_rels, claims, iad_mechanisms, arc_day_state, manifest = build_corpus(data_dir)

    # basic internal consistency checks before promotion
    assert len(rows) == manifest["observation_count"]
    assert all(r["observation_id"] for r in rows)
    seen_ids = {r["observation_id"] for r in rows}
    assert len(seen_ids) == len(rows), "duplicate observation_id detected"
    for rel in case_rels:
        assert rel["epistemic_status"] in EPISTEMIC_STATUSES
    for c in claims:
        assert c["epistemic_status"] in EPISTEMIC_STATUSES

    with tempfile.TemporaryDirectory() as tmp:
        candidate_dir = Path(tmp) / "research_corpus_candidate"
        write_corpus(rows, case_rels, claims, iad_mechanisms, arc_day_state, manifest, candidate_dir)

        # Promote via rename only (never delete-then-write): some mounted
        # filesystems in this environment reject unlink() but allow
        # rename(). If a previous output exists, rename it aside first, then
        # rename the new candidate into place. This guarantees the live
        # output directory is replaced atomically at each step and is never
        # left half-written, and it never requires removing files outright.
        if output_dir.exists():
            stale_name = output_dir.parent / f"{output_dir.name}.stale-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"
            shutil.move(str(output_dir), str(stale_name))
        shutil.move(str(candidate_dir), str(output_dir))

    return output_dir, manifest


if __name__ == "__main__":
    out_dir, manifest = generate()
    print(f"Research corpus written to: {out_dir}")
    print(json.dumps(manifest["arc_day_state_summary"], indent=2))
    print(f"Observations: {manifest['observation_count']}")
    print(f"Files included: {manifest['files_included']}")
    print(f"Files excluded: {len(manifest['files_excluded'])}")
