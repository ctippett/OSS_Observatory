from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SignalCounts:
    structural_shift: int
    policy_evolution: int
    incident: int


@dataclass
class BriefItem:
    title: str
    date: str
    source: str
    domain: str
    surface: str
    signal_type: str
    half_life: str
    ai_impact: str
    arc: str
    summary: str
    extracted_statistics: List[str] = field(default_factory=list)
    breach_specifics: Optional[dict] = None


@dataclass
class CyberBrief:
    date: str
    signal_counts: SignalCounts
    iad_lens: str
    items: List[BriefItem]
    daily_narrative: str
    strategic_insights: List[str]
    industry_research_reference: List[str]

    adversary_spotlight: Optional[dict] = None
    micro_tracking: Optional[dict] = None
    inflection_watch: Optional[str] = None
    longitudinal_arcs: Optional[dict] = None