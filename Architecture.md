OSS Observatory Conceptual Architecture
Purpose
The OSS Observatory is a cloud-native research platform for collecting, validating, organizing, and analyzing longitudinal evidence about the evolution of open source software and cybersecurity in the age of AI.
The architecture is designed to be durable, extensible, and independent of any single AI model, software vendor, or research stream.

1. Inputs
The Observatory ingests information from multiple evidence sources, including:
	•	News articles
	•	Government advisories
	•	Vendor blogs and technical research
	•	Threat intelligence reports
	•	Organization disclosures
	•	Open source project announcements
	•	User configuration
	•	Persistent research baselines

2. Processing
Incoming evidence is transformed through a combination of AI and software.
Processing includes:
	•	AI analysis
	•	Validation
	•	Deduplication
	•	Classification
	•	Serialization

3. Storage
The Observatory preserves structured research assets, including:
	•	Briefs
	•	Items
	•	Sources
	•	Entities
	•	Research questions
	•	Explanatory models
	•	Research conversations
These assets form the Observatory's long-term evidence repository.

4. Outputs
The Observatory produces multiple research and operational outputs:
	•	TXT briefings
	•	JSON records
	•	CSV signal roll-ups
	•	Dashboards
	•	Interactive visualizations
	•	Explanatory models
	•	Research papers

5. System Flow
Inputs
    ↓
Processing
    ↓
Storage
    ↓
Outputs
Evidence accumulates over time, enabling longitudinal analysis, investigations, and model development.

6. Operating Principle
Artificial intelligence performs analysis, extraction, summarization, and drafting.
Software enforces structure, validation, persistence, reproducibility, workflow, and data integrity.
The Observatory owns the workflow.

7. Extensibility
The OSS Observatory is designed to support multiple AI systems and multiple research instruments.
AI models are interchangeable analytical components.
Research instruments are modular sources of evidence that contribute to a shared evidence repository.
Neither the Observatory nor its data architecture depends on any single AI model, prompt, vendor, or research stream.

8. Three Durable Research Records
The Observatory recognizes three durable research records, each answering a different question:
	•	Evidence — what happened in the world.
	•	Analysis — what the Observatory's research systems (including CyberBrief) made of it.
	•	Interaction — what happened when a researcher engaged with that analysis.
Research conversations are the durable record of Interaction. A preserved conversation is evidence of the research process itself: the questions asked, the challenges raised, the disagreements, corrections, connections, exploratory reasoning, dead ends, and developing ideas that occurred along the way.
Research conversations are preserved substantially intact, not aggressively summarized at capture time. Preservation retains both sides of the dialogue, using the full conversation or session record when available rather than reconstructing from a compacted or partial context, so earlier dialogue is not silently lost. Preservation carries only minimal provenance: discussion date, provider or model if known, conversation name, and the associated CyberBrief date or run if applicable.
"Research conversations" (Section 3) is the storage location for this record, under research_conversations/.
No schema, database, index, scoring, tagging, extraction, summarization, or automated interpretation process governs this record today. Capture can be cheap and generous. Interpretation can remain selective and expensive. Preservation does not mean formalization.
"Preserve this discussion" is documented here as an interaction convention, not a software command — a phrase a researcher may use in conversation to ask that the discussion be written to the durable record. It is not required to be identical across providers, and it is not automated: whether automatic preservation, session boundaries, or retrieval tooling are warranted is a decision for actual use to inform, not one made in advance.

9. Modeling and Automation Boundary
This section extends the Operating Principle (Section 6); it does not restate it.
An idea captured in a preserved research conversation is not automatically a model, a model candidate, or a Models Ledger entry simply because it was discussed. Preservation retains enough intellectual texture that reasoning can later be resumed or re-entered, without prematurely deciding what the conversation means. The existing handoff "Move this to modeling" continues to mean: preserve this thinking so it can be developed later — not: this is now a model.
Artificial intelligence handles inference. Software handles invariants. Automation should support researcher cognition rather than require conformance to machinery. Software may preserve, retrieve, connect, count, compare, and surface research material where appropriate; consequential intellectual judgments remain part of the research interaction, and a researcher's exploratory reasoning process is not encoded into deterministic software. The purpose of the Observatory's structured machinery is to create better conditions for thinking, not to produce increasingly elaborate tables.
The following constraints remain in force:
	•	No new application layer unless actually needed.
	•	Do not duplicate data.
	•	Do not make normal daily operation heavier.
	•	No required human work queues.
	•	Preserve first, decide later.
	•	Use existing infrastructure.
	•	Automation reduces cognitive housekeeping rather than making intellectual decisions.
	•	Build only when usage demonstrates a need.
The governing design question remains: What is the least machinery required to get the research value we want?

