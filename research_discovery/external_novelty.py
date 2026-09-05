"""
Requirement 12 -- External Novelty Validation V1.

Downstream of Research Discovery V1 (generate_discovery.py), which this
module never imports, modifies, or re-executes. Reads Research Discovery's
existing output (discovery_candidates.json) and the same read-only corpus /
canonical evidence chain it already resolves, purely to verify a candidate
ID exists and its evidence still traces cleanly. Writes exactly one new kind
of artifact: a small, human-readable External Novelty Assessment JSON file
per researcher-selected candidate.

See research_discovery/EXTERNAL_NOVELTY_VALIDATION.md for the full
methodology this module implements the record contract for. This module
performs no search itself -- search, synonym generation, and conceptual-
equivalence judgment are a person's (with LLM assistance) responsibility,
exercised once per researcher-selected candidate. This module only
validates, resolves traceability, and writes/reads the resulting record
safely.

No crawler, literature database, embeddings, vector search, knowledge
graph, scheduler, or automated candidate-triggered validation is
implemented here -- see EXTERNAL_NOVELTY_VALIDATION.md Section 12.
"""
import csv
import json
import os
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo-relative paths (works regardless of caller's cwd or sandbox identity --
# mirrors research_corpus/generate_research_corpus.py's portable pattern).
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
OSS_OBSERVATORY_ROOT = THIS_FILE.parent.parent          # .../OSS_Observatory
DATA_DIR = OSS_OBSERVATORY_ROOT.parent / "CyberBrief" / "Data"
CORPUS_DIR = DATA_DIR / "research_corpus"
DISCOVERY_DIR = DATA_DIR / "research_discovery"
ASSESSMENT_DIR = DISCOVERY_DIR / "external_novelty"

REQUIRED_FIELDS = [
    "discovery_candidate_id",
    "validation_date",
    "relationship_or_research_question",
    "search_concepts_and_synonyms",
    "source_families_searched",
    "strongest_related_prior_work",
    "relationship_to_prior_work",
    "external_novelty_outcome",
    "limitations",
    "evidence_and_citations",
]

ALLOWED_OUTCOMES = {"KNOWN", "PARTIALLY KNOWN", "NOT FOUND", "INDETERMINATE"}

# Language the standing writing rule (EXTERNAL_NOVELTY_VALIDATION.md Section 2)
# forbids anywhere in a persisted assessment: absence of found evidence must
# never be reported as proof of novelty.
FORBIDDEN_NOVELTY_LANGUAGE = ["novel", "first to", "nobody has studied",
                              "no one has studied", "unprecedented"]


# =========================================================================
# Read-only resolution against existing Research Discovery / Corpus output
# =========================================================================

def load_discovery_candidates():
    """Read the existing, unmodified discovery_candidates.json."""
    path = DISCOVERY_DIR / "discovery_candidates.json"
    return json.loads(path.read_text())


def find_candidate(candidate_id):
    """Return the surfaced Discovery Candidate dict for this ID, or None."""
    for c in load_discovery_candidates():
        if c["candidate_id"] == candidate_id:
            return c
    return None


def load_observations():
    """Minimal, portable read of observations.csv, keyed by observation_id.
    Independent of generate_discovery.py's module-level BASE constant so
    this module works regardless of that pre-existing path's portability.
    """
    path = CORPUS_DIR / "observations.csv"
    rows = {}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            rows[int(r["observation_id"])] = r
    return rows


_canonical_cache = {}


def resolve_evidence(observation_row):
    """observation row -> canonical item -> source_urls. Read-only."""
    fname = observation_row["source_file"]
    idx = int(observation_row["item_index"])
    if fname not in _canonical_cache:
        _canonical_cache[fname] = json.loads((DATA_DIR / fname).read_text())
    item = _canonical_cache[fname]["items"][idx]
    return {
        "source_file": fname,
        "item_index": idx,
        "title": item.get("title"),
        "source_urls": list(item.get("source_urls", [])),
    }


def resolve_candidate_trace(candidate_id):
    """Full traceability check for one candidate: candidate -> corpus
    observations -> canonical evidence. Returns None if the candidate ID
    does not resolve. Raises if any supporting observation's evidence chain
    is broken (this should never happen for a candidate Research Discovery
    already surfaced -- it re-verifies, it does not re-derive).
    """
    candidate = find_candidate(candidate_id)
    if candidate is None:
        return None
    obs_rows = load_observations()
    trace = []
    for oid in candidate["supporting_observation_ids"]:
        obs = obs_rows[oid]
        trace.append({"observation_id": oid, **resolve_evidence(obs)})
    return {"candidate": candidate, "observation_evidence": trace}


# =========================================================================
# Assessment record validation
# =========================================================================

def validate_assessment(record):
    """Return a list of validation error strings; empty list == valid.
    Never raises on a malformed record -- callers decide what to do with
    the error list (write_assessment_atomic refuses to write on any error).
    """
    errors = []

    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        errors.append(f"missing required field(s): {missing}")

    extra = [k for k in record if k not in REQUIRED_FIELDS]
    if extra:
        errors.append(f"unexpected field(s) beyond the ten-field contract: {extra}")

    if "external_novelty_outcome" in record:
        outcome = record["external_novelty_outcome"]
        if outcome not in ALLOWED_OUTCOMES:
            errors.append(
                f"external_novelty_outcome {outcome!r} is not one of {sorted(ALLOWED_OUTCOMES)}"
            )

    if "discovery_candidate_id" in record:
        if find_candidate(record["discovery_candidate_id"]) is None:
            errors.append(
                f"discovery_candidate_id {record['discovery_candidate_id']!r} "
                f"does not resolve to a candidate in discovery_candidates.json"
            )

    if "source_families_searched" in record:
        if not isinstance(record["source_families_searched"], list) or not record["source_families_searched"]:
            errors.append("source_families_searched must be a non-empty list")

    if "evidence_and_citations" in record:
        if not isinstance(record["evidence_and_citations"], list):
            errors.append("evidence_and_citations must be a list")

    if "limitations" in record and not str(record["limitations"]).strip():
        errors.append("limitations must not be empty")

    # Standing writing rule: absence must never be reported as proof of
    # novelty, anywhere in the free-text fields.
    text_fields = ["strongest_related_prior_work", "relationship_to_prior_work", "limitations"]
    for field in text_fields:
        if field in record:
            lowered = str(record[field]).lower()
            for phrase in FORBIDDEN_NOVELTY_LANGUAGE:
                if phrase in lowered:
                    errors.append(
                        f"field {field!r} contains forbidden novelty-claim language: {phrase!r}"
                    )

    return errors


# =========================================================================
# Safe write (Task 14: do not overwrite a known-good assessment with
# malformed or incomplete output). Simplest safe pattern: validate first,
# then write to a temp file in the same directory and atomically replace --
# no promotion pipeline, no candidate-directory rename dance; this is a
# single small file, not a multi-file generation batch like Research
# Discovery's own output.
# =========================================================================

def write_assessment_atomic(candidate_id, record, assessment_dir=None):
    """Validate `record`, then atomically write it to
    <assessment_dir>/<candidate_id>.json. Raises ValueError (and writes
    nothing) if validation fails -- an existing good file for this
    candidate, if any, is left untouched.
    """
    errors = validate_assessment(record)
    if errors:
        raise ValueError(f"refusing to write invalid assessment: {errors}")

    target_dir = Path(assessment_dir) if assessment_dir else ASSESSMENT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / f"{candidate_id}.json"

    fd, tmp_path = tempfile.mkstemp(dir=str(target_dir), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, final_path)  # atomic on the same filesystem
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return final_path


def read_assessment(candidate_id, assessment_dir=None):
    target_dir = Path(assessment_dir) if assessment_dir else ASSESSMENT_DIR
    path = target_dir / f"{candidate_id}.json"
    return json.loads(path.read_text())
