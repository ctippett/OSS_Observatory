"""
Requirement 13 -- seeds the smallest legitimate V1 research-memory set,
using only real material from the two completed Requirement 13 functional
capability tests (the Discovery Candidate investigation test, and the 3-Day
Incremental Research Reflection test). No fabricated observations, no
invented candidate IDs, no rewritten canonical evidence.

Idempotent: safe to re-run. If a thread or event already exists (by its
deterministic id), creation/append is skipped rather than duplicated or
overwritten.

Three threads are created, exactly matching the three real, named examples
carried through both prior Requirement 13 reports:

  1. Structural Shift <-> Levers            (strengthening)
  2. Incentives / Levers exclusivity        (weakening / collapsing)
  3. AI as accelerant                       (split, vendor-sourcing
                                              uncertainty, cross-window
                                              connection back to Aug 31)

A fourth, small event set on thread 2 also demonstrates a resolved research
question, and one MODEL_POTENTIAL_FLAGGED event (the ai_impact typology
observation) is attached to threads 1 and 3 jointly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_memory as rm  # noqa: E402


def _thread_id_for(label):
    return rm.stable_id("thread", label)


def ensure_thread(label, created_date, created_by, evidence_anchors):
    tid = _thread_id_for(label)
    try:
        return rm.get_thread(tid)
    except rm.ResearchMemoryError:
        return rm.create_thread(label, created_date, created_by, evidence_anchors, thread_id=tid)


def ensure_event(**kwargs):
    thread_ids = kwargs["thread_ids"]
    probe_id = rm.stable_id(
        "evt", sorted([thread_ids] if isinstance(thread_ids, str) else thread_ids),
        kwargs["event_type"], kwargs["event_date"], kwargs["narrative"],
        kwargs.get("evidence_references", []), kwargs.get("resulting_state"),
        kwargs.get("resolves_event_id"),
    )
    try:
        return rm._get_event_by_id(probe_id)
    except rm.ResearchMemoryError:
        return rm.append_event(**kwargs)


def seed():
    created = {"threads": [], "events": []}

    # ---------------------------------------------------------------
    # THREAD 1: Structural Shift <-> Levers (strengthening)
    # ---------------------------------------------------------------
    t1_label = "Structural Shift <-> Levers"
    t1 = ensure_thread(
        t1_label, "2026-09-05", "researcher-authored",
        evidence_anchors=[
            {"type": "discovery_candidate",
             "candidate_id": "cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac"},
            {"type": "external_novelty_assessment",
             "candidate_id": "cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac"},
        ],
    )
    created["threads"].append(t1["thread_id"])

    e = ensure_event(
        thread_ids=t1["thread_id"], event_type="NOTICED", event_date="2026-09-01",
        narrative=("Discovery surfaced a Strong candidate: 3/4 (75%) Structural Shift "
                   "observations tag the Levers IAD dimension vs. 9% elsewhere. External "
                   "Novelty Assessment: PARTIALLY KNOWN -- the general pairing of structural "
                   "change with an identifiable leverage/intervention point is established in "
                   "Meadows / punctuated-equilibrium / IAD literature; this corpus's specific "
                   "applied measurement is not."),
        evidence_references=[
            {"type": "discovery_candidate",
             "candidate_id": "cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac"},
            {"type": "external_novelty_assessment",
             "candidate_id": "cat-dim-coupling__signal_type-structural_shift-levers__d8f13af4e9ac"},
        ],
        resulting_state="INVESTIGATE", origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t1["thread_id"], event_type="REINFORCED", event_date="2026-09-02",
        narrative=("Unit 42's AI-agent intrusion case (Structural Shift) tags Levers, with an "
                   "explicit mechanism note: branch-protection controls were the one control "
                   "that held against the agents' backdoor-planting attempt -- a clean, "
                   "concrete match to the Meadows systemic-intervention-point sense of "
                   "'Levers,' the first time this corpus has recorded an explicit rationale "
                   "for a Levers tag."),
        evidence_references=[{"type": "canonical_item",
                               "source_file": "20260902_20260904_cyberbrief_retrospective.json",
                               "item_index": 2}],
        resulting_state="INVESTIGATE", origin="ai-suggested-researcher-accepted",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t1["thread_id"], event_type="REINFORCED", event_date="2026-09-04",
        narrative=("Project Watershed 250 (Structural Shift, critical-infrastructure/water-sector "
                   "OT defense initiative) also tags Levers -- a second, cross-domain "
                   "reinforcement within 3 days, from a completely different context (policy "
                   "partnership vs. AI-driven intrusion) than the Sep 2 instance. Its Levers "
                   "tag itself carries no dimension_notes rationale, unlike Unit 42's -- "
                   "inconsistent annotation persists even in this better-annotated period."),
        evidence_references=[{"type": "canonical_item",
                               "source_file": "20260902_20260904_cyberbrief_retrospective.json",
                               "item_index": 5}],
        resulting_state="INVESTIGATE", origin="ai-suggested-researcher-accepted",
    )
    created["events"].append(e["event_id"])

    # ---------------------------------------------------------------
    # THREAD 2: Incentives / Levers exclusivity (weakening / collapsing)
    # ---------------------------------------------------------------
    t2_label = "Incentives / Levers exclusivity"
    t2 = ensure_thread(
        t2_label, "2026-09-01", "researcher-authored",
        evidence_anchors=[
            {"type": "discovery_candidate",
             "candidate_id": "iad-exclusivity__incentives-levers__a8b14976a1d7"},
        ],
    )
    created["threads"].append(t2["thread_id"])

    e = ensure_event(
        thread_ids=t2["thread_id"], event_type="NOTICED", event_date="2026-09-01",
        narrative=("Discovery surfaced a Strong candidate: Incentives (3 obs) and Levers (4 obs) "
                   "never co-occur (0/7) in the 15-observation corpus."),
        evidence_references=[{"type": "discovery_candidate",
                               "candidate_id": "iad-exclusivity__incentives-levers__a8b14976a1d7"}],
        resulting_state="INVESTIGATE", origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t2["thread_id"], event_type="CONTRADICTED", event_date="2026-09-02",
        narrative=("Two new observations on the same day each independently tag both Incentives "
                   "and Levers: the IDScan.net/'Nexus' dark-web marketplace item, and the Unit 42 "
                   "AI-agent intrusion item. If merged into the corpus, the 0/7 exclusivity would "
                   "already be broken by two unrelated counterexamples."),
        evidence_references=[
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 0},
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 2},
        ],
        origin="ai-suggested-researcher-accepted",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t2["thread_id"], event_type="QUESTION_ADDED", event_date="2026-09-02",
        narrative="Are these two co-occurrences genuine, deliberate tagging, or a coding-scheme artifact from this looser-annotated period?",
        evidence_references=[
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 0},
        ],
        origin="researcher-authored",
    )
    q1 = e
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t2["thread_id"], event_type="CONTRADICTED", event_date="2026-09-03",
        narrative=("A third, unrelated observation -- Group-IB's 'BraZetsu' AI-enhanced "
                   "initial-access-broker report -- also tags both Incentives and Levers, with "
                   "an explicit dimension_note explaining the Incentives tag (AI-driven pricing "
                   "of compromised hosts as a graded commercial product). Three independent "
                   "counterexamples in two days."),
        evidence_references=[{"type": "canonical_item",
                               "source_file": "20260902_20260904_cyberbrief_retrospective.json",
                               "item_index": 3}],
        resulting_state="WEAKENING", origin="ai-suggested-researcher-accepted",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t2["thread_id"], event_type="QUESTION_RESOLVED", event_date="2026-09-04",
        narrative=("Reviewed BraZetsu's tagging rationale directly: the dimension_note is specific "
                   "and well-justified (AI-driven triage turning raw access into a graded "
                   "commercial product), not an arbitrary or careless co-tag. Judgment: the "
                   "co-occurrences look like genuine, deliberate tagging rather than a coding "
                   "artifact -- the original 0/7 finding looks like a small-N artifact of the "
                   "narrower original corpus, not a durable property. Reclassifying the "
                   "candidate itself is a Requirement 12 regeneration action, outside this "
                   "memory's scope."),
        evidence_references=[{"type": "canonical_item",
                               "source_file": "20260902_20260904_cyberbrief_retrospective.json",
                               "item_index": 3}],
        resolves_event_id=q1["event_id"], origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    # ---------------------------------------------------------------
    # THREAD 3: AI as accelerant (split; vendor-sourcing uncertainty;
    # cross-window connection back to a pre-existing Aug 31 claim)
    # ---------------------------------------------------------------
    t3_label = "AI as accelerant"
    t3 = ensure_thread(
        t3_label, "2026-08-31", "researcher-authored",
        evidence_anchors=[
            {"type": "longitudinal_claim",
             "claim_text": ("Gryxa's fully AI-built toolkit represents a capability-baseline shift "
                             "in adversary use of generative AI.")},
        ],
    )
    created["threads"].append(t3["thread_id"])

    e = ensure_event(
        thread_ids=t3["thread_id"], event_type="NOTICED", event_date="2026-08-31",
        narrative=("Gryxa (first threat toolkit built entirely by an AI coding agent) recorded as "
                   "an Analytical Inference: a capability-baseline shift in adversary use of "
                   "generative AI."),
        evidence_references=[{"type": "longitudinal_claim",
                               "claim_text": ("Gryxa's fully AI-built toolkit represents a "
                                               "capability-baseline shift in adversary use of "
                                               "generative AI.")}],
        resulting_state="WATCH", origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t3["thread_id"], event_type="REINFORCED", event_date="2026-09-02",
        narrative=("Unit 42's AI-agent case is a second, independent instance: AI agents "
                   "compressed a ~2-week intrusion into under 10 hours by chaining 50+ known "
                   "techniques, with no new exploit -- extends the Gryxa claim from a single "
                   "hedged inference toward a real, if still small, pattern."),
        evidence_references=[{"type": "canonical_item",
                               "source_file": "20260902_20260904_cyberbrief_retrospective.json",
                               "item_index": 2}],
        origin="ai-suggested-researcher-accepted",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t3["thread_id"], event_type="SPLIT", event_date="2026-09-03",
        narrative=("BraZetsu (Exilware's AI-enhanced initial-access-broker marketplace) is a "
                   "third instance, but of a meaningfully different kind: Gryxa and Unit 42 are "
                   "about AI accelerating INTRUSION EXECUTION; BraZetsu is about AI accelerating "
                   "CRIMINAL MONETIZATION/TRIAGE after access is already achieved. The thread "
                   "should be read as two related but distinct sub-themes, not one uniform "
                   "pattern."),
        evidence_references=[{"type": "canonical_item",
                               "source_file": "20260902_20260904_cyberbrief_retrospective.json",
                               "item_index": 3}],
        origin="ai-suggested-researcher-accepted",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t3["thread_id"], event_type="INTERPRETATION_REVISED", event_date="2026-09-04",
        narrative=(
            "Current interpretation, three instances in: real enough to keep watching, not yet "
            "solid. Competing explanations -- "
            "(A) genuine shift: AI is measurably compressing both attacker execution and criminal "
            "monetization timelines, supported by all three cases having no novel exploit/technique, "
            "only faster execution of known ones; weakened by only 3 instances. "
            "(B) reporting-selection artifact: all three instances are vendor-authored case studies "
            "(Unit 42, Group-IB) with an incentive to publicize dramatic AI narratives; would be "
            "distinguished by a non-vendor-sourced instance. "
            "No winner is chosen."
        ),
        evidence_references=[
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 2},
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 3},
        ],
        resulting_state="WATCH", origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    e = ensure_event(
        thread_ids=t3["thread_id"], event_type="NEXT_EVIDENCE_IDENTIFIED", event_date="2026-09-04",
        narrative=("A non-vendor-sourced instance of AI accelerating an attack or criminal "
                   "operation, or a negative case (an AI-adjacent story where AI did NOT "
                   "meaningfully accelerate anything), would most reduce uncertainty about "
                   "whether this is a real shift or a selection effect."),
        evidence_references=[],
        origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    # ---------------------------------------------------------------
    # Cross-thread MODEL_POTENTIAL_FLAGGED event (ai_impact typology)
    # ---------------------------------------------------------------
    e = ensure_event(
        thread_ids=[t1["thread_id"], t3["thread_id"]],
        event_type="MODEL_POTENTIAL_FLAGGED", event_date="2026-09-04",
        narrative=(
            "Suspected conceptual form: a small typology/continuum of AI's operational role in an "
            "event (ai_impact field values observed so far: None, Enabling, Amplifying, Governing; "
            "'Targeted' appears only in prose, not yet as an observed tag). Evidence suggesting it: "
            "Unit 42 (Amplifying) and BraZetsu (Amplifying) both fit an 'accelerant' reading; "
            "Watershed 250 (Enabling) is a different role entirely (defensive capability delivery, "
            "not an attack accelerant). What is still missing: no observed 'Targeted' instance; no "
            "test of whether the four values are mutually exclusive, ordered, or independent; no "
            "examination across a wider time window. What would weaken/falsify it: finding that "
            "ai_impact values are applied as inconsistently as 'Levers' was found to be, or that "
            "most events resist clean categorization. This flags only that there MAY be conceptual "
            "structure worth watching -- no model, framework, or name is created."
        ),
        evidence_references=[
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 2},
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 3},
            {"type": "canonical_item", "source_file": "20260902_20260904_cyberbrief_retrospective.json",
             "item_index": 5},
        ],
        origin="researcher-authored",
    )
    created["events"].append(e["event_id"])

    return created


if __name__ == "__main__":
    result = seed()
    print(f"Threads present: {len(result['threads'])}")
    print(f"Events appended or already present: {len(result['events'])}")
