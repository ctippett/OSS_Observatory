## 1. Schema Purpose and Vision

The Canonical CyberBrief Schema v1 defines the standard structure for the daily CyberBrief JSON record.

Its purpose is to create a data contract for the daily CyberBrief based on the current workflow. The schema formalizes the structure currently produced by the CyberBrief process. The August 13, 2026 JSON implementation is the descriptive authority for v1.

Each daily JSON file serves as the canonical/baseline record for that day's CyberBrief. The record preserves both collected cybersecurity observations and the analytical interpretation generated from those observations. The analytical elements are retained because they represent meaningful research data about how signals, trends, relationships, and longitudinal developments were interpreted at the time of collection.

The schema is intended to provide for evolution in the process. CyberBrief research priorities, source coverage, collection methods, analytical techniques, and output requirements are expected to change over time. When those changes require modification of the data structure, the schema should evolve deliberately through versioning rather than through untracked structural drift.

Schema v1 establishes the first baseline contract, not a permanent final design. Its role is to make the current data model explicit, validate future daily records against that model, support reliable downstream analysis, and provide a controlled foundation for future evolution.

The guiding principle is:

**One daily JSON file is the canonical CyberBrief record, preserving both collected data and analytical interpretation under an explicitly versioned data contract.**

## 2. Top-Level Structure

Each canonical CyberBrief JSON file represents one daily CyberBrief record. Schema v1 uses the August 13, 2026 implementation as its descriptive authority while allowing explicit design decisions made during schema formalization to refine that structure.

The canonical record contains the following top-level fields:

| Field                         | Purpose                                                                                    |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| `date`                        | Identifies the date represented by the daily CyberBrief.                                   |
| `items`                       | Contains the individual cybersecurity signals selected for the daily record.               |
| `signal_counts`               | Summarizes the number of signals represented in the briefing by signal classification.     |       |
| `micro_tracking`              | Captures observations associated with specifically monitored research areas.               |
| `inflection_watch`            | Records whether evidence of a potentially meaningful structural inflection was identified. |
| `longitudinal_arcs`           | Connects the day's observations to longer-running CyberBrief research arcs.                |
| `daily_narrative`             | Preserves the day's aggregate analytical interpretation of the collected signals.          |
| `adversary_spotlight`         | Captures the day's selected adversary and associated analytical context.                   |
| `strategic_insights`          | Captures higher-order insights derived from the day's signals.                             |    |

These top-level fields collectively preserve the daily CyberBrief as a single research record containing both the underlying selected signals and the analytical interpretation generated from them.

Schema v1 intentionally excludes the historical `cwe_knowledge_segment` and `operational_definitions` components from the canonical daily record. The CWE Knowledge Segment served primarily as personal knowledge enrichment rather than as data describing the observed cybersecurity environment. Operational Definitions served a related learning and research-ledger function and may have future value as a separate OSS Observatory knowledge resource, particularly for studying how technical terminology emerges and evolves.

Their exclusion from Schema v1 does not imply that either capability lacks value. Rather, it establishes a boundary between the canonical daily research record and supporting knowledge-enrichment functions.

At this level, Schema v1 defines **what constitutes a CyberBrief record**. The internal structure, data types, required/optional status, and validation rules for each field are defined in subsequent sections.


## 3. Daily Record Core

The Daily Record Core defines the foundational elements of each canonical CyberBrief JSON record: the date represented by the record, the individual signals collected for that date, and the aggregate classification of those signals.

### 3.1 `date`

**Purpose:** Identifies the date represented by the CyberBrief record.

**Type:** String

**Required:** Yes

**Format:** `YYYY-MM-DD`

The `date` field establishes the reporting date for the canonical daily record. It is distinct from the individual dates associated with signals inside the `items` array.

Example:

```json
"date": "2026-08-13"
```

### 3.2 `items`

**Purpose:** Stores the individual cybersecurity signals selected for inclusion in the daily CyberBrief.

**Type:** Array of objects

**Required:** Yes

Each object in `items` represents one distinct selected development or signal. The `items` array is the primary collection component of the CyberBrief record and preserves the factual, descriptive, and classified information associated with each selected signal.

The internal structure of each item is defined separately in **Section 4: Core Item Schema**.

Schema v1 does not establish a fixed number of items per daily record. The number of selected signals may vary based on the significance of observed activity and the evolving CyberBrief research process.

### 3.3 `signal_counts`

**Purpose:** Provides an aggregate count of the daily items by signal classification.

**Type:** Object

**Required:** Yes

Schema v1 recognizes the following signal-count fields:

* `structural_shift`
* `policy_evolution`
* `incident`

Each value must be a non-negative integer representing the number of selected items assigned to that signal type.

Example:

```json
"signal_counts": {
  "structural_shift": 2,
  "policy_evolution": 2,
  "incident": 1
}
```

`signal_counts` is derived from the classified items contained in the daily record and provides a compact structured summary of the day's signal composition.

## 4. Core Item Schema

Each object within the `items` array represents one distinct cybersecurity signal selected for inclusion in the daily CyberBrief.

The Core Item Schema defines the standard structure used to describe, classify, and preserve each selected signal. The item is the primary unit of observation within the CyberBrief dataset.

Each item contains the following core fields:

| Field                  | Purpose                                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| `title`                | Provides a concise human-readable identifier for the signal or development.                                |
| `date`                 | Records the date associated with the observed development.                                                 |
| `source`               | Identifies the source or sources from which the signal was collected.                                      |
| `source_urls`          | Preserves the URL(s) of the evidence supporting the signal.                                                 |
| `domain`               | Classifies the signal within the CyberBrief research domain taxonomy.                                      |
| `surface`              | Identifies the primary technical, institutional, operational, or ecosystem surface affected by the signal. |
| `signal_type`          | Classifies the nature and expected analytical significance of the observed signal.                         |
| `half_life`            | Classifies the expected persistence or durability of the signal's significance.                            |
| `ai_impact`            | Characterizes the role or relevance of AI within the observed development.                                 |
| `arc`                  | Associates the signal with a defined longitudinal CyberBrief research arc when applicable.                 |
| `iad_signal`           | Identifies whether and where the item presents meaningful potential for later IAD analysis.                |
| `summary`              | Preserves a concise factual description of the signal and its significance.                                |
| `extracted_statistics` | Preserves quantitative facts or measurements extracted from the source material.                           |
| `breach_specifics`     | Preserves additional structured information when the item represents a data breach or related compromise.  |

### 4.1 `title`

**Purpose:** Provides a concise human-readable identifier for the signal.

**Type:** String

**Required:** Yes

The title should identify the development clearly enough to distinguish it from other items in the daily record.

### 4.2 `date`

**Purpose:** Records the date associated with the individual signal or development.

**Type:** String

**Required:** Yes

**Format:** `YYYY-MM-DD`

The item-level date may differ from the top-level CyberBrief `date` when the underlying event occurred, was disclosed, or was reported on an earlier date.

### 4.3 `source`

**Purpose:** Identifies the source or sources associated with the collected signal.

**Type:** String

**Required:** Yes

The source field provides provenance for the item and supports later verification, research, and auditability.

A signal may be supported by multiple sources. Schema v1 preserves the mature CyberBrief convention of representing those sources within a single string.

### 4.4 `domain`

**Purpose:** Classifies the signal within the CyberBrief research domain taxonomy.

**Type:** String

**Required:** Yes

The domain identifies the broad research area to which the signal belongs.

The domain vocabulary may evolve as CyberBrief research priorities and source coverage change. Schema v1 therefore does not treat the domain taxonomy as permanently fixed.

### 4.5 `surface`

**Purpose:** Identifies the primary technical, institutional, operational, or ecosystem surface affected by the signal.

**Type:** String

**Required:** Yes

`surface` provides a more specific characterization than `domain` and supports aggregation and longitudinal analysis across recurring areas of activity.

### 4.6 `signal_type`

**Purpose:** Classifies the nature and expected analytical significance of the signal.

**Type:** String

**Required:** Yes

Schema v1 recognizes three signal types:

* `Incident`
* `Policy Evolution`
* `Structural Shift`

These classifications distinguish events and developments according to their expected degree of structural significance.

### 4.7 `half_life`

**Purpose:** Classifies the expected persistence of the signal's significance.

**Type:** String

**Required:** Yes

Schema v1 recognizes three Half-Life classifications:

* `Short`
* `Medium`
* `Long`

Half-Life provides a longitudinal research lens by distinguishing developments likely to decay quickly from those expected to remain relevant over longer periods.

### 4.8 `ai_impact`

**Purpose:** Characterizes the role or relevance of artificial intelligence within the observed signal.

**Type:** String

**Required:** Yes

Schema v1 preserves the AI-impact classification used by the mature CyberBrief implementation. The allowable vocabulary will be explicitly defined in the Schema v1 validation rules.

### 4.9 `arc`

**Purpose:** Associates an individual signal with a defined longitudinal CyberBrief research arc when applicable.

**Type:** String

**Required:** Yes

The field may contain the identifier and name of the applicable longitudinal arc or an empty string when no current arc applies.

Arc assignments allow individual observations to accumulate into longer-running research threads without requiring the daily item itself to perform the resulting longitudinal analysis.

### 4.10 `iad_signal`

**Purpose:** Identifies whether and where an item presents meaningful potential for later analysis using the Institutional Analysis and Development lens.

**Type:** Object

**Required:** Yes

IAD-Signal is a lightweight research marker rather than a completed IAD analysis. It makes only two claims:

1. How strongly the item appears to warrant later institutional analysis using the IAD lens.
2. Which IAD dimensions appear potentially relevant based on the information contained in the item.

The object contains:

```json
"iad_signal": {
  "relevance": "High",
  "dimensions": ["Actors", "Rules-in-Use", "Incentives"]
}
```

#### `relevance`

**Type:** String

**Allowed values:**

* `None`
* `Low`
* `Medium`
* `High`

#### `dimensions`

**Type:** Array of strings

**Allowed values:**

* `Actors`
* `Rules-in-Use`
* `Arena`
* `Incentives`
* `Interactions`
* `Outcomes`
* `Levers`

Zero or more dimensions may be selected. When `relevance` is `None`, `dimensions` must be an empty array.

IAD-Signal identifies **analytical potential only**. It does not assert institutional relationships, causal mechanisms, findings, outcomes, or recommended interventions. Full IAD analysis is a downstream research activity performed at an appropriate unit of analysis.

### 4.11 `summary`

**Purpose:** Preserves a concise factual description of the observed development and its significance.

**Type:** String

**Required:** Yes

The summary should contain sufficient context to make the item analytically useful without requiring the original source to understand the basic development.

### 4.12 `extracted_statistics`

**Purpose:** Preserves quantitative facts, measurements, counts, percentages, financial values, or other numerical information associated with the signal.

**Type:** Array of strings

**Required:** Yes

The array may be empty when the underlying signal contains no meaningful quantitative information.

Quantitative information should be grounded in the underlying source material rather than inferred when the source does not provide it.

### 4.13 `breach_specifics`

**Purpose:** Preserves structured information when the selected signal involves a data breach or related compromise for which additional breach-specific information is analytically useful.

**Type:** Object or `null`

**Required:** Yes

For items without applicable breach-specific information, the value is:

```json
"breach_specifics": null
```

When applicable, Schema v1 preserves the mature implementation's structured breach information:

* `victim`
* `actor`
* `vector`
* `data`
* `status`

These fields preserve information about the affected organization or population, attributed actor when known, compromise vector, exposed or affected data, and current breach or disclosure status.

### 4.14 `source_urls`

**Purpose:** Preserves the URL(s) of the evidence supporting the signal, independent of the `source` field's descriptive name(s).

**Type:** Array of strings

**Required:** Yes

`source_urls` contains at least one URL. It may contain more than one when multiple sources materially support the observation.

```json
"source_urls": [
  "https://example.com/article"
]
```

The field preserves only the URL(s) themselves. Schema v1 does not attach additional per-URL metadata (such as retrieval date, outlet name, or primary/secondary classification) to `source_urls` — that remains a candidate for future schema evolution rather than a v1 requirement.


5. Analytical and Longitudinal Structures

In addition to individual signal records, the canonical CyberBrief preserves selected analytical structures that connect daily observations to broader patterns, research priorities, and developments over time.

These structures are retained because they capture analytical judgments made at the time of collection that may be valuable for longitudinal research. They complement the underlying item-level evidence but do not replace later analysis of that evidence.

Schema v1 includes the following analytical and longitudinal structures:

Field	Purpose
micro_tracking	Tracks observations associated with specifically monitored research areas or recurring phenomena.
inflection_watch	Identifies evidence that may indicate an emerging structural change or meaningful inflection point.
longitudinal_arcs	Connects current observations with established longer-running CyberBrief research themes.
daily_narrative	Preserves the aggregate interpretation of what the day's collected signals suggest.
strategic_insights	Preserves higher-order analytical observations derived from the day's evidence.

These fields preserve contemporaneous analytical interpretation as part of the canonical research record. Their presence does not imply that the interpretations are permanent conclusions; they represent analytical judgments made using the evidence available at the time.

Detailed structural requirements for these fields are defined in the executable Schema v1 rather than duplicated in this human-readable contract.

6. Adversary Spotlight

adversary_spotlight preserves the CyberBrief's recurring actor-focused analysis of a threat actor or adversarial group relevant to the observed cybersecurity environment.

The structure captures:

who the actor is;
the actor's primary tactics; and
recent activity or impact associated with the actor.

Adversary Spotlight is retained in Schema v1 because it preserves contemporaneous analytical context about threat actors that may support later longitudinal research into adversary behavior, tactics, activity, and evolution.

The selected actor does not need to correspond to every item in the daily record, nor does selection imply that the actor represents the day's most important signal. It is an analytical feature of the daily record rather than an item-level classification.

Detailed structural and validation requirements are defined in the executable Schema v1.

7. Schema Governance

This section defines the decisions, change-management principles, and future considerations governing Canonical CyberBrief Schema v1.

7.1 Design Decisions

Records the significant architectural and methodological decisions made while establishing Schema v1 and why they were made.

7.2 Schema Evolution and Versioning

Defines how the schema can change over time while preserving historical integrity and auditability.

7.3 Future Schema Considerations

Records known limitations, open questions, and potential improvements to evaluate for future schema versions.

8. Future Schema Considerations

This section records known limitations, open questions, and candidate improvements that do not alter Schema v1 but should be evaluated when considering future schema versions.

Inclusion in this section does not imply that a change should be made; each item requires evaluation against accumulated evidence and research needs before incorporation into a future schema version.

Source structure: Schema v1 preserves source as a single string for compatibility with the mature workflow; evaluate whether future versions should represent multiple sources as structured objects or arrays, including source URLs and provenance metadata.
Domain and surface vocabulary: Schema v1 preserves domain and surface as flexible strings; evaluate accumulated data for vocabulary drift and determine whether controlled taxonomies, normalization, or hierarchical classifications would improve longitudinal analysis.
IAD-Signal validation: iad_signal is introduced in Schema v1 as a lightweight research marker; evaluate its usefulness after sufficient observations accumulate, including whether relevance levels and IAD dimensions reliably identify candidates for deeper institutional analysis.