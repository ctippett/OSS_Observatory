"""
Requirement 13 -- Research Memory V1.

Implements exactly two persistent representations, as derived from the two
completed Requirement 13 functional capability tests and the V1 design
report:

  RESEARCH THREAD  -- a durable, minimal identity for an idea worth tracking
                       across time. Carries NO mutable interpretation, NO
                       confidence score, NO article/model/graphic status.
                       Its only allowed growth is its evidence_anchors list
                       (append-only).

  RESEARCH MEMORY EVENT -- an append-only, immutable, dated record of how
                       evidence changed understanding of one or more threads.
                       New understanding is always a NEW event; nothing is
                       ever edited in place. "Current state" is never stored
                       -- it is always derived by reading the most recently
                       recorded state-affecting event.

This module deliberately does NOT implement: Question, Counterexample,
Explanation, Uncertainty, Next-Evidence, Hypothesis, Model, or Graphic as
separate persistent objects. All of that content lives as narrative and
evidence references inside Research Memory Events -- see
research_workbench/README.md for the reasoning.

This module reads, but never writes, Requirement 11/12 artifacts (Research
Corpus observations, Discovery Candidates, longitudinal claims, case
continuity, External Novelty Assessments, canonical CyberBrief items). It
resolves evidence by reference to those artifacts' own stable identities --
it never duplicates their content.
"""
import json
import os
import sys
import tempfile
import hashlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo-relative paths (mirrors research_corpus/generate_research_corpus.py
# and research_discovery/external_novelty.py's portable path pattern).
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
OSS_OBSERVATORY_ROOT = THIS_FILE.parent.parent          # .../OSS_Observatory
DATA_DIR = OSS_OBSERVATORY_ROOT.parent / "CyberBrief" / "Data"
CORPUS_DIR = DATA_DIR / "research_corpus"
DISCOVERY_DIR = DATA_DIR / "research_discovery"
WORKBENCH_DIR = DATA_DIR / "research_workbench"
THREADS_DIR = WORKBENCH_DIR / "threads"
EVENTS_FILE = WORKBENCH_DIR / "events.jsonl"

# Reuse Requirement 12's existing, already-portable evidence-resolution
# helpers (load_observations, find_candidate, resolve_evidence,
# resolve_candidate_trace, read_assessment) rather than re-implementing a
# second parallel evidence graph.
sys.path.insert(0, str(OSS_OBSERVATORY_ROOT / "research_discovery"))
import external_novelty as en  # noqa: E402


IAD_DIMENSIONS = ["Actors", "Rules-in-Use", "Arena", "Incentives",
                   "Interactions", "Outcomes", "Levers"]

ALLOWED_EVENT_TYPES = {
    "NOTICED", "REINFORCED", "CONTRADICTED", "COUNTEREXAMPLE_ADDED",
    "QUESTION_ADDED", "QUESTION_RESOLVED", "INTERPRETATION_REVISED", "SPLIT",
    "NEXT_EVIDENCE_IDENTIFIED", "NEXT_EVIDENCE_SATISFIED", "STATE_CHANGED",
    "MODEL_POTENTIAL_FLAGGED", "GRAPHIC_POTENTIAL_FLAGGED",
    "DORMANT_MARKED", "SUPERSEDED", "CLOSED",
}

# Event types that reference back to an earlier event by id (resolution /
# closure of something raised earlier).
RESOLVING_EVENT_TYPES = {"QUESTION_RESOLVED", "NEXT_EVIDENCE_SATISFIED"}
OPEN_EVENT_TYPES = {"QUESTION_ADDED": "QUESTION_RESOLVED",
                     "NEXT_EVIDENCE_IDENTIFIED": "NEXT_EVIDENCE_SATISFIED"}

ALLOWED_STATES = {"NEW", "WATCH", "INVESTIGATE", "WEAKENING", "SUPERSEDED",
                   "DORMANT", "CLOSED"}

ALLOWED_ORIGINS = {"researcher-authored", "ai-suggested-researcher-accepted"}

ALLOWED_EVIDENCE_REF_TYPES = {
    "observation", "discovery_candidate", "longitudinal_claim",
    "external_novelty_assessment", "canonical_item",
}

# Event types for which counting multiple "observation"-type evidence
# references as independent support/contradiction is meaningful enough to
# warrant the case-continuity safeguard (Part 11 / acceptance test #21).
INDEPENDENCE_SENSITIVE_EVENT_TYPES = {"REINFORCED", "CONTRADICTED", "COUNTEREXAMPLE_ADDED"}


class ResearchMemoryError(ValueError):
    """Raised for any malformed or unresolvable research-memory operation."""


# =========================================================================
# Small helpers
# =========================================================================

def stable_id(prefix, *parts):
    """Deterministic id, same philosophy as generate_discovery.py's
    stable_id(): a hash of the parts, so identity survives re-derivation
    from the same inputs rather than depending on wall-clock/randomness.
    """
    basis = "||".join(json.dumps(p, sort_keys=True) if not isinstance(p, str) else p
                       for p in parts)
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}__{digest}"


def _slug(label):
    return "".join(c if c.isalnum() else "-" for c in label.lower()).strip("-")


def _atomic_write_new(path, record):
    """Write a brand-new file. Refuses if the path already exists -- thread
    creation must never silently overwrite an existing thread.
    """
    if path.exists():
        raise ResearchMemoryError(f"{path.name} already exists -- refusing to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _atomic_extend_thread(path, old_record, new_record):
    """Replace a thread file only if new_record is a strict, allowed
    extension of old_record: same identity fields, evidence_anchors list
    only grown (old anchors all still present, in the same order, as a
    prefix of the new list).
    """
    for field in ("thread_id", "label", "created_date", "created_by"):
        if old_record.get(field) != new_record.get(field):
            raise ResearchMemoryError(
                f"refusing to change thread field {field!r} -- threads carry no mutable "
                f"interpretive state; only evidence_anchors may grow"
            )
    old_anchors = old_record.get("evidence_anchors", [])
    new_anchors = new_record.get("evidence_anchors", [])
    if new_anchors[:len(old_anchors)] != old_anchors:
        raise ResearchMemoryError(
            "append-only violation: new evidence_anchors do not strictly extend the prior list"
        )
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(new_record, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _append_jsonl_atomic(path, record):
    """Append one JSON object as a new line, enforcing structurally (not
    merely by convention) that the resulting file is a strict superset of
    the prior file: the old content must be an exact prefix of the new
    content. Rejects re-appending a record whose event_id already exists
    (events are immutable once persisted). Writes via temp file + atomic
    rename so a crash mid-write can never leave a partially-written file in
    place -- either the old file survives untouched, or the fully-written
    new file is installed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    old_content = path.read_text() if path.exists() else ""
    old_lines = old_content.splitlines()
    for line in old_lines:
        if not line.strip():
            continue
        existing = json.loads(line)
        if existing.get("event_id") == record.get("event_id"):
            raise ResearchMemoryError(
                f"event {record['event_id']} already exists -- events are immutable; "
                f"a changed understanding must be a NEW event, never a rewrite"
            )
    new_line = json.dumps(record, sort_keys=True)
    new_content = old_content + (new_line + "\n")
    if not new_content.startswith(old_content):
        raise ResearchMemoryError("append-only violation: new content does not extend prior content")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-events-", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(new_content)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _read_all_events(events_file=None):
    path = Path(events_file) if events_file else EVENTS_FILE
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


# =========================================================================
# Evidence reference validation + resolution (reads Req 11/12 data only)
# =========================================================================

def load_longitudinal_claims(corpus_dir=None):
    path = (Path(corpus_dir) if corpus_dir else CORPUS_DIR) / "longitudinal_claims.json"
    return json.loads(path.read_text()) if path.exists() else []


def load_case_continuity(corpus_dir=None):
    path = (Path(corpus_dir) if corpus_dir else CORPUS_DIR) / "case_continuity.json"
    return json.loads(path.read_text()) if path.exists() else []


def find_longitudinal_claim(claim_text, corpus_dir=None):
    matches = [c for c in load_longitudinal_claims(corpus_dir) if c["claim_text"] == claim_text]
    return matches[0] if len(matches) == 1 else None


_canonical_cache = {}


def resolve_canonical_item(source_file, item_index, data_dir=None):
    dd = Path(data_dir) if data_dir else DATA_DIR
    cache_key = (str(dd), source_file)
    if cache_key not in _canonical_cache:
        path = dd / source_file
        if not path.exists():
            raise ResearchMemoryError(f"canonical file not found: {source_file}")
        _canonical_cache[cache_key] = json.loads(path.read_text())
    doc = _canonical_cache[cache_key]
    items = doc.get("items", [])
    if not (0 <= item_index < len(items)):
        raise ResearchMemoryError(f"item_index {item_index} out of range for {source_file}")
    item = items[item_index]
    iad = item.get("iad_signal", {}) or {}
    return {
        "source_file": source_file,
        "item_index": item_index,
        "title": item.get("title"),
        "event_date": item.get("date"),
        "signal_type": item.get("signal_type"),
        "arc": item.get("arc"),
        "ai_impact": item.get("ai_impact"),
        "iad_dims": list(iad.get("dimensions", [])),
        "iad_relevance": iad.get("relevance"),
        "source_urls": list(item.get("source_urls", [])),
    }


def _validate_evidence_ref(ref, corpus_dir=None, discovery_dir=None, data_dir=None):
    if not isinstance(ref, dict) or "type" not in ref:
        raise ResearchMemoryError(f"malformed evidence reference: {ref!r}")
    t = ref["type"]
    if t not in ALLOWED_EVIDENCE_REF_TYPES:
        raise ResearchMemoryError(f"unknown evidence reference type: {t!r}")
    if t == "observation":
        obs = en.load_observations()
        if ref.get("observation_id") not in obs:
            raise ResearchMemoryError(f"unresolvable observation reference: {ref}")
    elif t == "discovery_candidate":
        if en.find_candidate(ref.get("candidate_id")) is None:
            raise ResearchMemoryError(f"unresolvable discovery_candidate reference: {ref}")
    elif t == "longitudinal_claim":
        if find_longitudinal_claim(ref.get("claim_text"), corpus_dir) is None:
            raise ResearchMemoryError(f"unresolvable longitudinal_claim reference: {ref}")
    elif t == "external_novelty_assessment":
        try:
            en.read_assessment(ref.get("candidate_id"))
        except Exception as exc:
            raise ResearchMemoryError(f"unresolvable external_novelty_assessment reference: {ref}") from exc
    elif t == "canonical_item":
        resolve_canonical_item(ref.get("source_file"), ref.get("item_index"), data_dir)


def resolve_evidence_reference(ref):
    """Resolve one evidence reference back through the existing,
    unmodified Requirement 11/12 lineage. Never duplicates their content --
    always reads it fresh.
    """
    _validate_evidence_ref(ref)
    t = ref["type"]
    if t == "observation":
        obs = en.load_observations()[ref["observation_id"]]
        evidence = en.resolve_evidence(obs)
        tags = [d for d in IAD_DIMENSIONS if obs.get(f"iad_dim_{d}") == "True"]
        return {
            "type": t, "observation_id": ref["observation_id"],
            "signal_type": obs.get("signal_type"), "iad_dims": tags,
            **evidence,
        }
    if t == "discovery_candidate":
        candidate = en.find_candidate(ref["candidate_id"])
        trace = en.resolve_candidate_trace(ref["candidate_id"])
        return {"type": t, "candidate": candidate, "trace": trace}
    if t == "longitudinal_claim":
        claim = find_longitudinal_claim(ref["claim_text"])
        resolved_evidence = [resolve_canonical_item(e["source_file"], e["item_index"])
                              for e in claim.get("evidence", [])]
        return {"type": t, "claim": claim, "resolved_evidence": resolved_evidence}
    if t == "external_novelty_assessment":
        return {"type": t, "assessment": en.read_assessment(ref["candidate_id"])}
    if t == "canonical_item":
        return {"type": t, **resolve_canonical_item(ref["source_file"], ref["item_index"])}
    raise ResearchMemoryError(f"unhandled evidence reference type: {t!r}")  # pragma: no cover


def _check_independent_evidence_safeguard(evidence_references, event_type):
    """Refuse to log a REINFORCED/CONTRADICTED/COUNTEREXAMPLE_ADDED event
    that treats two 'observation' references as independent evidence when
    case_continuity.json shows they are the same underlying case.
    """
    if event_type not in INDEPENDENCE_SENSITIVE_EVENT_TYPES:
        return
    obs_refs = [r for r in evidence_references if r.get("type") == "observation"]
    if len(obs_refs) < 2:
        return
    obs_rows = en.load_observations()
    continuity = load_case_continuity()
    if not continuity:
        return
    keyed = {}
    for r in obs_refs:
        row = obs_rows[r["observation_id"]]
        keyed[r["observation_id"]] = (row["source_file"], int(row["item_index"]))
    ids = list(keyed)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = keyed[ids[i]], keyed[ids[j]]
            for link in continuity:
                earlier = (link["earlier_observation"]["source_file"], link["earlier_observation"]["item_index"])
                later = (link["later_observation"]["source_file"], link["later_observation"]["item_index"])
                if {a, b} == {earlier, later}:
                    raise ResearchMemoryError(
                        f"observations {ids[i]} and {ids[j]} are the same underlying case "
                        f"per case_continuity.json -- cannot be logged as independent "
                        f"{event_type} evidence in a single event"
                    )


# =========================================================================
# Research Thread
# =========================================================================

def create_thread(label, created_date, created_by, evidence_anchors=None, thread_id=None):
    """Explicitly create a new Research Thread. created_by must record
    whether this is a researcher decision or an AI suggestion the
    researcher accepted (ALLOWED_ORIGINS-style string, free text is fine
    here since this is provenance prose, not a controlled vocabulary).
    """
    THREADS_DIR.mkdir(parents=True, exist_ok=True)
    tid = thread_id or stable_id("thread", label)
    anchors = list(evidence_anchors or [])
    for ref in anchors:
        _validate_evidence_ref(ref)
    record = {
        "thread_id": tid,
        "label": label,
        "created_date": created_date,
        "created_by": created_by,
        "evidence_anchors": anchors,
    }
    _atomic_write_new(THREADS_DIR / f"{tid}.json", record)
    return record


def get_thread(thread_id):
    path = THREADS_DIR / f"{thread_id}.json"
    if not path.exists():
        raise ResearchMemoryError(f"unknown thread_id: {thread_id}")
    return json.loads(path.read_text())


def list_threads():
    if not THREADS_DIR.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(THREADS_DIR.glob("*.json"))]


def add_evidence_anchor(thread_id, ref):
    """Append-only growth of a thread's evidence anchors. Idempotent: if
    the anchor is already present, returns the thread unchanged rather than
    duplicating it.
    """
    old = get_thread(thread_id)
    _validate_evidence_ref(ref)
    if ref in old["evidence_anchors"]:
        return old
    new_record = dict(old, evidence_anchors=old["evidence_anchors"] + [ref])
    _atomic_extend_thread(THREADS_DIR / f"{thread_id}.json", old, new_record)
    return new_record


# =========================================================================
# Research Memory Event
# =========================================================================

def _get_event_by_id(event_id):
    for e in _read_all_events():
        if e["event_id"] == event_id:
            return e
    raise ResearchMemoryError(f"unknown event_id: {event_id}")


def append_event(thread_ids, event_type, event_date, narrative,
                  evidence_references=None, resulting_state=None,
                  origin="researcher-authored", resolves_event_id=None):
    if isinstance(thread_ids, str):
        thread_ids = [thread_ids]
    thread_ids = list(thread_ids)
    if not thread_ids:
        raise ResearchMemoryError("an event must reference at least one thread")
    for tid in thread_ids:
        get_thread(tid)  # raises ResearchMemoryError if unknown

    if event_type not in ALLOWED_EVENT_TYPES:
        raise ResearchMemoryError(f"unknown event_type: {event_type!r}")
    if resulting_state is not None and resulting_state not in ALLOWED_STATES:
        raise ResearchMemoryError(f"unknown resulting_state: {resulting_state!r}")
    if origin not in ALLOWED_ORIGINS:
        raise ResearchMemoryError(f"unknown origin: {origin!r}")
    if not narrative or not str(narrative).strip():
        raise ResearchMemoryError("narrative must not be empty")

    evidence_references = list(evidence_references or [])
    for ref in evidence_references:
        _validate_evidence_ref(ref)  # raises on malformed/unresolvable reference

    if resolves_event_id is not None:
        _get_event_by_id(resolves_event_id)  # raises if unknown

    _check_independent_evidence_safeguard(evidence_references, event_type)

    event_id = stable_id(
        "evt", sorted(thread_ids), event_type, event_date, narrative,
        evidence_references, resulting_state, resolves_event_id,
    )
    record = {
        "event_id": event_id,
        "event_date": event_date,
        "thread_ids": thread_ids,
        "event_type": event_type,
        "narrative": narrative,
        "evidence_references": evidence_references,
        "resulting_state": resulting_state,
        "origin": origin,
        "resolves_event_id": resolves_event_id,
    }
    _append_jsonl_atomic(EVENTS_FILE, record)
    return record


def get_thread_events(thread_id, events=None):
    """Full event history for one thread, in the order they were recorded
    (append order == the true sequence in which understanding evolved).
    """
    all_events = events if events is not None else _read_all_events()
    return [e for e in all_events if thread_id in e["thread_ids"]]


def derive_state(thread_id, as_of_date=None, events=None):
    """Current (or as-of-date) state, derived from the most recently
    recorded state-affecting event -- never a separately stored field.
    """
    history = get_thread_events(thread_id, events=events)
    if as_of_date is not None:
        history = [e for e in history if e["event_date"] <= as_of_date]
    state_events = [e for e in history if e.get("resulting_state")]
    if not state_events:
        return "NEW"
    return state_events[-1]["resulting_state"]


def _open_items(thread_id, opening_type, closing_type, events=None):
    history = get_thread_events(thread_id, events=events) if thread_id else (events or _read_all_events())
    opened = [e for e in history if e["event_type"] == opening_type]
    resolved_ids = {e["resolves_event_id"] for e in history
                    if e["event_type"] == closing_type and e.get("resolves_event_id")}
    return [e for e in opened if e["event_id"] not in resolved_ids]


def list_open_questions(thread_id=None, events=None):
    return _open_items(thread_id, "QUESTION_ADDED", "QUESTION_RESOLVED", events=events)


def list_unresolved_next_evidence(thread_id=None, events=None):
    return _open_items(thread_id, "NEXT_EVIDENCE_IDENTIFIED", "NEXT_EVIDENCE_SATISFIED", events=events)


# =========================================================================
# Mode support: Investigation / Daily / Catch-up all read the SAME memory
# =========================================================================

def investigate(thread_id):
    """Everything Investigation Mode needs for one thread: full history,
    derived state, resolved evidence per event, open questions, unresolved
    next-evidence, and a coarse supporting/contradicting split.
    """
    thread = get_thread(thread_id)
    history = get_thread_events(thread_id)
    resolved_history = []
    for e in history:
        resolved_history.append(dict(e, resolved_evidence=[resolve_evidence_reference(r)
                                                             for r in e["evidence_references"]]))
    supporting_types = {"NOTICED", "REINFORCED"}
    contradicting_types = {"CONTRADICTED", "COUNTEREXAMPLE_ADDED"}
    return {
        "thread": thread,
        "current_state": derive_state(thread_id),
        "history": resolved_history,
        "supporting_events": [e for e in history if e["event_type"] in supporting_types],
        "contradicting_events": [e for e in history if e["event_type"] in contradicting_types],
        "open_questions": list_open_questions(thread_id),
        "unresolved_next_evidence": list_unresolved_next_evidence(thread_id),
        "evidence_anchors_resolved": [resolve_evidence_reference(a) for a in thread["evidence_anchors"]],
    }


def catch_up(window_start, window_end):
    """Reflection/Catch-up Mode: events inside the missed window, PLUS the
    full prior history of every thread touched in that window (this is
    what lets a stale claim from before the window -- e.g. Gryxa -- surface
    even though its own event predates the window).
    """
    all_events = _read_all_events()
    in_window = [e for e in all_events if window_start <= e["event_date"] <= window_end]
    affected_thread_ids = sorted({tid for e in in_window for tid in e["thread_ids"]})

    threads_report = {}
    for tid in affected_thread_ids:
        full_history = get_thread_events(tid, events=all_events)
        prior_context = [e for e in full_history if e["event_date"] < window_start]
        threads_report[tid] = {
            "thread": get_thread(tid),
            "events_in_window": [e for e in full_history if window_start <= e["event_date"] <= window_end],
            "prior_context_outside_window": prior_context,
            "current_state": derive_state(tid, events=all_events),
            "open_questions": list_open_questions(tid, events=all_events),
            "unresolved_next_evidence": list_unresolved_next_evidence(tid, events=all_events),
        }

    all_thread_ids = {t["thread_id"] for t in list_threads()}
    untouched = sorted(all_thread_ids - set(affected_thread_ids))

    return {
        "window": (window_start, window_end),
        "events_in_window": in_window,
        "affected_threads": threads_report,
        "untouched_threads": untouched,
    }


def suggest_thread_relevance(new_evidence_refs, threads=None):
    """Daily Research Mode support: given today's new evidence references,
    return plain suggestions of how they might relate to existing threads
    (via their discovery_candidate anchors) and to any open next-evidence
    needs. This is a deliberately simple, explicitly-labeled heuristic --
    string/tag matching against real Discovery Candidate structure and
    plain keyword matching against next-evidence narrative -- not a
    natural-language interface. It NEVER persists anything; the caller
    (researcher) decides whether to turn a suggestion into an
    append_event() call.
    """
    threads = threads if threads is not None else list_threads()
    suggestions = []
    for ref in new_evidence_refs:
        resolved = resolve_evidence_reference(ref)
        tags = resolved.get("iad_dims", [])
        signal_type = resolved.get("signal_type")
        for thread in threads:
            for anchor in thread["evidence_anchors"]:
                if anchor.get("type") != "discovery_candidate":
                    continue
                candidate = en.find_candidate(anchor["candidate_id"])
                if candidate is None:
                    continue
                method = candidate["method"]
                fields = candidate["fields_involved"]
                if method == "iad_dimension_exclusivity":
                    d1, d2 = fields
                    if d1 in tags and d2 in tags:
                        suggestions.append({
                            "thread_id": thread["thread_id"],
                            "evidence_ref": ref,
                            "suggested_event_type": "CONTRADICTED",
                            "reason": (f"new evidence tags both {d1!r} and {d2!r}, which candidate "
                                       f"{candidate['candidate_id']} asserts never co-occur"),
                        })
                elif method == "category_dimension_coupling":
                    dims_in_fields = [f for f in fields if f in IAD_DIMENSIONS]
                    cat_fields = [f for f in fields if f not in IAD_DIMENSIONS]
                    if dims_in_fields and cat_fields and signal_type:
                        dim = dims_in_fields[0]
                        normalized_value = signal_type.lower().replace(" ", "_")
                        if normalized_value in candidate["candidate_id"]:
                            if dim in tags:
                                suggestions.append({
                                    "thread_id": thread["thread_id"],
                                    "evidence_ref": ref,
                                    "suggested_event_type": "REINFORCED",
                                    "reason": (f"new {signal_type!r} evidence also tags {dim!r}, "
                                               f"consistent with candidate {candidate['candidate_id']}"),
                                })
                            else:
                                suggestions.append({
                                    "thread_id": thread["thread_id"],
                                    "evidence_ref": ref,
                                    "suggested_event_type": "COUNTEREXAMPLE_ADDED",
                                    "reason": (f"new {signal_type!r} evidence does NOT tag {dim!r}, "
                                               f"a candidate counterexample for {candidate['candidate_id']}"),
                                })
            for need in list_unresolved_next_evidence(thread["thread_id"]):
                text = need["narrative"].lower()
                if "without levers" in text and signal_type == "Structural Shift" and "Levers" not in tags:
                    suggestions.append({
                        "thread_id": thread["thread_id"],
                        "evidence_ref": ref,
                        "suggested_event_type": "NEXT_EVIDENCE_SATISFIED",
                        "resolves_event_id": need["event_id"],
                        "reason": "new Structural Shift evidence without a Levers tag answers this open need",
                    })
    return suggestions
