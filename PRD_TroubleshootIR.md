# PRD: Samsung Smart Guided Troubleshooting Engine

## 1. Project Overview

**Project:** Smart Guided Troubleshooting Engine  
**Working Name:** TroubleIR  
**Hackathon:** Samsung PRISM, Theme 02  
**Primary Goal:** Convert vague Samsung Galaxy user complaints into structured, validated troubleshooting plans that comply with Samsung's required response schema and can guide the user to the correct Settings screen.

### Core principle

The project must not simply reproduce the pipeline already specified by the Samsung problem statement.

Samsung already defines the broad flow:

`Complaint -> Query Enrichment -> Structure Extraction -> Deeplink Mapping & Action Ordering -> Semantic Cache -> REST API`

Therefore, that pipeline is treated as the **baseline contract**, not as the innovation.

Our contribution must improve measurable failure modes inside that pipeline, while remaining simple enough to implement and demonstrate within the hackathon.

### Central research/engineering question

> Can we make Samsung's required troubleshooting pipeline substantially more reliable, cacheable, and maintainable than a straightforward LLM + retrieval implementation, without sacrificing coverage or latency?

The system should be evaluated against explicit baselines rather than assuming that additional architecture is automatically better.

---

# 2. Problem Description

Users describe device problems in natural language:

- "My phone is getting really hot."
- "The screen is too dim at night."
- "Battery is dying quickly after the update."
- "My phone keeps flickering and the battery drains fast."

The user does not necessarily know the relevant Samsung setting, menu, terminology, or sequence of troubleshooting actions.

The system receives:

1. A colloquial user complaint.
2. Optional SIIS/support text.
3. Samsung-provided deeplink/catalog information and required schema assets.

It must produce a structured troubleshooting response containing appropriate goals, actions, steps, and deeplinks.

The system is constrained by requirements such as:

- exact output schema,
- grounded troubleshooting steps,
- valid Samsung deeplinks,
- correct screen mapping,
- one Action per screen,
- appropriate action ordering,
- critical actions later,
- required query variations,
- semantic caching,
- low latency on cached requests,
- and a compliant `no_match` response when the system cannot safely produce a plan.

The original problem statement defines these requirements. This PRD does not treat them as new inventions.

---

# 3. What We Are NOT Building

The following are explicitly out of scope unless required later by the official specification:

- A generic chatbot.
- A conversational assistant with unnecessary multi-turn interaction.
- Voice control.
- Fine-tuning a large language model.
- Predictive maintenance using synthetic telemetry.
- A flashy One UI clone.
- A generic RAG chatbot.
- A generic "LLM + validator" pipeline presented as innovation.
- Feedback-learning systems.
- Distributed caching.
- Full autonomous device control.
- A system that invents Samsung deeplinks.
- Claims such as "zero hallucinations" without measured evidence.

The project must prioritize measurable technical value over UI polish.

---

# 4. Product Goals

## 4.1 Primary Goals

### G1. Correct troubleshooting structure

Convert a vague complaint into the correct set of:

- intents,
- operations,
- goals,
- actions,
- screens,
- and steps.

### G2. Correct screen resolution

Resolve an action to the most specific supported Samsung Settings screen rather than simply retrieving a semantically similar parent menu.

### G3. Grounded actions

Every generated troubleshooting action should be traceable to the available Samsung support/SIIS evidence.

### G4. Safe deeplink binding

The system should select deeplinks from the supplied catalog rather than allowing the language model to invent executable navigation identifiers.

### G5. Reliable semantic caching

Cached plans must not be returned merely because two queries have high embedding similarity.

The system must specifically handle:

- opposite polarity,
- compound complaints,
- stale catalog dependencies,
- and unseen paraphrases.

### G6. Honest abstention

If the evidence is insufficient or the system is uncertain, returning `no_match` is preferable to producing a misleading troubleshooting plan.

### G7. Maintainability

When the Samsung deeplink catalog changes, only affected cached plans should require invalidation.

---

# 5. Core Product Insight

The project is based on an important distinction:

> The LLM should understand language, but it should not be the sole authority for executable troubleshooting navigation.

However, this is **not** claimed as novel by itself.

An LLM can be given a deeplink catalog and can select valid entries. Therefore, the project must not claim:

> "An LLM cannot find deeplinks."

Instead, the engineering objective is:

> Separate language interpretation from deterministic plan construction so that screen resolution, validation, ordering, caching, and catalog maintenance become independently testable.

The value must be demonstrated through measured improvements over a simpler baseline.

---

# 6. Landscape, Prior Art, and Novelty Positioning

This section exists to prevent the project from making a novelty claim that is already covered by
Samsung products, published research, or other PRISM implementations.

## 6.1 Samsung already has natural-language settings control

Samsung already provides natural-language Settings search on supported Galaxy devices. Samsung's
documentation describes users describing a setting or issue in natural language and receiving relevant
settings. Samsung Members also provides diagnostics and troubleshooting support. In February 2026,
Samsung announced a new Bixby experience in One UI 8.5 that can understand natural-language requests
and directly control device settings.

Sources:

- Samsung, "How to use Settings Search on Galaxy devices":
  https://www.samsung.com/in/support/mobile-devices/how-to-use-settings-search-on-galaxy-devices/
- Samsung, "Search from Settings on your Galaxy phone":
  https://www.samsung.com/us/support/answer/ANS10002893/
- Samsung, "How to use Samsung Members Diagnostics":
  https://www.samsung.com/in/support/mobile-devices/how-to-use-samsung-members-diagnostics/
- Samsung Newsroom, "Samsung Introduces the New Bixby in One UI 8.5":
  https://news.samsung.com/us/samsung-introduces-new-bixby-one-ui-8-5/

Implication:

Do not pitch the project as "natural language to a Samsung setting." That capability already
exists. The project must instead demonstrate value in multi-step troubleshooting plans, grounding,
screen-level resolution, deterministic binding, cache correctness, abstention, and maintenance.

## 6.2 Relevant technical prior art

The design should explicitly distinguish its components from related research:

- **vCache**: verified semantic prompt caching with learned per-prompt decision boundaries. This
  motivates evaluating cache error, not only hit rate.
  https://proceedings.iclr.cc/paper_files/paper/2026/hash/9559cd2116de7a8f5672eac3fcd232cc-Abstract-Conference.html
- **LLM-Modulo**: LLMs combined with external verifiers rather than relying on unconstrained model
  output. TroubleIR uses the same broad verifier principle in a Samsung troubleshooting domain.
  https://arxiv.org/abs/2411.14484
- **AutoDroid**: LLM-powered Android task automation using app-specific UI knowledge and dynamic
  exploration. TroubleIR is narrower: it compiles Samsung support knowledge into constrained
  troubleshooting plans rather than operating as a general GUI agent.
  https://arxiv.org/abs/2308.15272
  https://github.com/MobileLLM/AutoDroid

These are prior-art references, not claims that the project independently invents the underlying
ideas.

## 6.3 PRISM competitor scan

The team should maintain a small competitor matrix covering public PRISM repositories such as
TapFix, Team ECLIPSE's advanced implementation, Ariha910/samsung-prism, and FixRoute.

The purpose is not to reproduce competitor implementations. It is to identify crowded ideas that
should not be presented as the main innovation, including:

- hybrid retrieval,
- LLM extraction plus validators,
- slot-agreement semantic caching,
- clarifying questions,
- sessions,
- feedback ranking,
- predictive telemetry,
- safety interceptors,
- One UI styled frontends,
- on-device setting toggles.

Repository URLs must be recorded only after verifying the exact public repository identity. If a
repository cannot be reliably located, list its name as an unverified reference rather than
inventing a URL.

## 6.4 Novelty position

The project should state novelty conservatively:

1. **SettingsGraph** is the main structural contribution: a screen hierarchy reconstructed from
   Samsung catalog/support evidence and used to reject ancestor-menu matches.
2. **Guarded plans** are an optional contribution when validation metadata is sufficiently populated.
3. **Compositional verified caching** is an engineering combination of atomized intents, polarity/
   slot protection, dependency tracking, and composition.
4. **Metamorphic admission/calibration** is an engineering combination for deciding when a generated
   plan should be trusted or cached.
5. **TroubleIR** is a domain-specific application of the broader LLM-plus-verifier pattern.

Do not claim any of these are "never done before." The evidence should come from ablations and
measured improvements over the baseline.

# 6. Proposed System

## 6.1 High-Level Architecture

```text
                    USER COMPLAINT
                           |
                           v
                  +------------------+
                  | Query Normalizer |
                  +------------------+
                           |
                           v
                  +------------------+
                  | Clause / Intent  |
                  | Decomposition    |
                  +------------------+
                           |
                +----------+----------+
                |                     |
             CACHE HIT             CACHE MISS
                |                     |
                v                     v
        Verified Atom Cache      SIIS / Support
                |                  Evidence
                |                     |
                |                     v
                |               LLM Extraction
                |                     |
                |                     v
                |                 TroubleIR
                |                     |
                |                     v
                |             Grounding Validator
                |                     |
                |                     v
                |              SettingsGraph
                |                     |
                |                     v
                |              Action Compiler
                |                     |
                |                     v
                |             Deeplink Binding
                |                     |
                |                     v
                |               Ordering/Lint
                |                     |
                +----------+----------+
                           |
                           v
                  Reliability / Admission
                           |
                  +--------+--------+
                  |                 |
               SERVE              ABSTAIN
                  |                 |
                  v                 v
               Cache             no_match
                  |
                  v
               RESPONSE
```

---

# 7. System Components

## 7.1 Component A: Query Understanding

### Purpose

Normalize the user's complaint and identify independent troubleshooting intents.

### Responsibilities

- Normalize spelling and informal language.
- Identify clauses.
- Identify:
  - component,
  - symptom,
  - trigger,
  - polarity.
- Detect compound complaints.

### Example

Input:

> "Screen is too bright at night and battery dies really quickly."

Potential atoms:

```text
Atom 1:
component = display
symptom = brightness
polarity = too_bright
trigger = night

Atom 2:
component = battery
symptom = rapid_drain
polarity = high_drain
trigger = unspecified
```

The decomposition must not be blindly trusted. Low-confidence decomposition should remain on the cold path rather than being aggressively cached.

---

# 8. TroubleIR

TroubleIR is the internal intermediate representation used between language understanding and deterministic plan construction.

Example:

```json
{
  "intents": [
    {
      "component": "display",
      "symptom": "brightness",
      "polarity": "too_bright",
      "trigger": "night"
    }
  ],
  "operations": [
    {
      "verb": "open",
      "target_text": "Display settings",
      "source_span": [120, 145],
      "precedence_refs": []
    }
  ]
}
```

The exact schema must ultimately conform to the official Samsung assets and output contract.

### Important rule

The LLM receives SIIS/support evidence needed for extraction.

The compiler, not the LLM, owns the final executable binding.

---

# 9. Grounding Layer

Every operation should retain provenance.

```text
Operation
   |
   +-- source document
   +-- source sentence
   +-- character span
   +-- extracted claim
```

A step should only be accepted when it can be supported by the available evidence.

### Failure behavior

If the extracted operation cannot be adequately grounded:

```text
E204: UNGROUNDED_OPERATION
```

The system may perform one repair attempt. If grounding still fails, the operation must not silently become a fabricated troubleshooting step.

---

# 10. SettingsGraph

## 10.1 Purpose

The SettingsGraph represents the hierarchy of Samsung Settings screens relevant to the available support/catalog data.

The graph exists to solve a specific problem:

> Semantic retrieval can identify a relevant parent menu while the actual troubleshooting action belongs to a deeper screen.

### Example

```text
Settings
 |
 +-- Display
      |
      +-- Navigation bar
           |
           +-- Button order
```

If retrieval identifies `Display` while the evidence establishes `Display -> Navigation bar`, the parent node should not be accepted when the deeper node is required.

### Graph construction

Offline graph construction may use:

1. Deeplink catalog descriptions.
2. SIIS navigation paths.
3. Explicit hierarchy phrases.
4. Normalized screen aliases.

An LLM may assist in offline alias normalization, but graph entries must be inspectable and testable.

### Runtime rule

Resolve the deepest node consistent with the evidence.

If a candidate is an ancestor of the required node:

```text
reject candidate
reason = parent_menu
```

### Important limitation

The graph must not invent hierarchy merely because two settings sound related.

Every edge should retain evidence.

---

# 11. Deeplink Binding

The system must distinguish among:

1. A valid catalog deeplink.
2. The required `dummy_positive` representation where applicable.
3. No deeplink for a manual action.

The system must never generate arbitrary navigation URLs.

### Validation

Before a response is returned:

- URI must belong to the allowed catalog where a URI is required.
- No unauthorized URLs may appear in output.
- Manual actions must not receive fake executable deeplinks.
- The exact output schema must validate.

---

# 12. Action Grouping

The official task requires actions to correspond to screens.

Therefore:

```text
multiple operations
        |
        v
resolve screen nodes
        |
        v
group consecutive operations
        |
        v
Action
```

The system must not group unrelated settings simply because their names are semantically similar.

---

# 13. Action Ordering

Actions should be ordered using evidence-backed precedence plus deterministic safety/reversibility rules allowed by the task.

General principle:

```text
least disruptive
       |
       v
reversible/basic checks
       |
       v
more consequential actions
       |
       v
critical actions
```

The system must not invent causal relationships.

If the source material does not establish an ordering relationship, that relationship should be marked as uncertain rather than presented as a fact.

---

# 14. Semantic Cache

## 14.1 Why a normal semantic cache is insufficient

Two queries can be extremely close in embedding space but require opposite plans.

Example:

```text
"Screen is too bright"
"Screen is too dim"
```

Therefore:

```text
embedding similarity alone != plan equivalence
```

## 14.2 Atom-level cache

Instead of caching only entire queries, store verified troubleshooting plans at the intent/atom level.

Example:

```text
display + brightness + too_bright
```

can be stored independently from:

```text
battery + rapid_drain
```

A compound query can then compose previously verified atoms.

## 14.3 Cache admission

A candidate cached result should require:

- semantic similarity,
- intent/slot agreement,
- polarity agreement,
- verified plan status,
- valid dependencies.

The exact thresholds must be fitted and evaluated rather than arbitrarily chosen.

---

# 15. Dependency-Aware Cache Invalidation

Each cached plan records its dependencies.

Example:

```json
{
  "plan_id": "plan_102",
  "dependencies": {
    "catalog_entries": [
      "deeplink_42",
      "deeplink_97"
    ],
    "siis_hash": "..."
  }
}
```

If `deeplink_42` changes, only plans depending on that entry need invalidation.

This avoids blindly clearing the entire cache after every catalog change.

---

# 16. Reliability and Abstention

The system should not treat an LLM's self-reported confidence as ground truth.

Potential reliability features:

- agreement across required query variations,
- retrieval margin,
- grounding coverage,
- repair count,
- presence/absence of SIIS,
- screen resolution agreement.

A calibration model may combine these features.

### Important terminology

Call the resulting value:

> **empirical reliability score**

Do not claim it is a formal correctness guarantee.

If reliability falls below the experimentally selected threshold:

```text
fallback = no_match
```

---

# 17. Metamorphic Testing

The required query variations can also serve as a consistency test.

For one complaint:

```text
Variation A -> Display -> Brightness
Variation B -> Display -> Brightness
Variation C -> Display -> Brightness
Variation D -> Display -> Navigation
```

If variations disagree materially, the system should avoid blindly admitting the result to cache.

This turns required query enrichment from only an output requirement into an internal consistency signal.

---

# 18. Catalog Gap Miner

The system should optionally produce a report:

```text
Support/SIIS path:
Settings -> Display -> X

Catalog deeplink:
MISSING

Frequency:
37 support paths
```

This creates a potential Samsung engineering artifact:

> Which troubleshooting screens are frequently referenced by support knowledge but lack usable deeplink coverage?

This is more valuable than merely showing a chatbot response.

---

# 19. Optional Guarded Plans

If the catalog contains sufficient validation entries, the system may support state-aware actions.

Example:

```text
Current setting:
Battery optimization = already enabled

Plan:
Do not ask user to enable it again.
```

The system can use `validationDeeplink` information where supported by the official assets.

### Go/no-go rule

Do not build this component until the real assets are audited.

If validation coverage is insufficient:

> Remove this feature from the implementation and document it as future work.

---

# 20. Baselines

This is mandatory.

We must prove that additional architecture actually improves performance.

## B0: Raw LLM

```text
Complaint + SIIS + catalog
          |
          v
         LLM
          |
          v
       Response
```

No specialized compiler.

## B1: Reference Pipeline

Implement the obvious pipeline described by the official task:

```text
Query enrichment
      |
Structure extraction
      |
Deeplink mapping
      |
Action ordering
      |
Semantic cache
      |
REST API
```

## B2: TroubleIR Core

```text
B1
+
grounding
+
SettingsGraph
+
deterministic compilation
```

## B3: TroubleIR + Verified Cache

```text
B2
+
atom cache
+
polarity/slot checks
+
dependency tracking
```

## B4: Full System

```text
B3
+
metamorphic admission
+
empirical reliability calibration
```

Optional:

```text
+ guarded plans
```

---

# 21. Evaluation Risks and Judge Assumptions

## 21.1 Likely automated evaluation

The team should assume that at least part of evaluation may be machine-scored, while treating this
as a hypothesis until organizers confirm it.

The design therefore prioritizes fields that are explicitly measurable and schema-checkable:

- step accuracy,
- deeplink relevance,
- exact URI validity,
- rule compliance,
- action ordering,
- fallback behavior,
- latency.

Do not optimize for visual polish at the expense of reference-schema compliance.

## 21.2 `dummy_positive` versus masked-URI discrepancy

The design document identified an apparent discrepancy between the official examples and one public
competitor implementation around `dummy_positive` versus a masked URI for a screen such as
Navigation bar.

This must be resolved from the official assets before implementation.

Required audit:

1. Inspect Appendix B and all supplied examples.
2. Inspect `deeplinks.json`.
3. Inspect the schema and `originalType`/type fields if present.
4. Identify which screens are expected to receive a real catalog URI.
5. Identify which screens are expected to receive `bixby://dummy_positive`.
6. Identify when the correct value is `null`.
7. Encode the result as a deterministic binding policy.
8. Add unit tests for every observed category.

Do not infer the policy from a competitor repository when the official assets provide evidence.

# 21. Evaluation Strategy

Do not claim improvement without measurements.

## 21.1 Gold Plans

Create a manually labeled set based on the available SIIS/support assets.

Each sample should record:

- expected intent,
- expected actions,
- expected screen,
- expected deeplink behavior,
- expected ordering.

Two people should independently label a subset where possible.

## 21.2 Paraphrase Set

Test on paraphrases that are not generated by the same process used to prewarm the cache.

Include:

- human-written queries,
- alternate wording,
- typo-heavy queries,
- formal language,
- frustrated language.

## 21.3 Contrastive Set

Create opposite-intent pairs:

```text
too bright <-> too dim
too loud <-> too quiet
turn on <-> turn off
```

These are particularly important for cache evaluation.

## 21.4 Compound Set

Examples:

```text
screen flickers + battery drains
Wi-Fi disconnects + phone overheats
```

Evaluate whether atom composition works without mixing unrelated actions.

## 21.5 Drift Set

Simulate:

- deleted catalog entries,
- renamed entries,
- changed descriptions,
- added entries.

Measure whether affected plans are invalidated correctly.

---

# 22. Metrics

## Compliance

- Schema validity.
- Rule compliance.
- URL leak rate.
- Exact URI validity.
- Valid deeplink rate.

Targets should only be claimed after measurement.

## Accuracy

- Step accuracy.
- Deeplink relevance.
- Exact-screen accuracy.
- Parent-menu error rate.
- Ungrounded-step rate.

## Ordering

- Critical-action ordering violations.
- Agreement with gold ordering.

## Cache

- Hit rate.
- False-hit rate.
- Contrastive false-hit rate.
- Compound hit rate.
- Merge validity.
- Invalidation precision.
- Invalidation recall.

## Latency

Measure:

- warm p50,
- warm p95,
- cold p50,
- cold p95.

The latency requirements are explicit acceptance criteria:

- **Warm path p95 <= 300 ms**
- **Cold path p95 <= 8,000 ms**
- Measure p50 and p95 separately for warm and cold paths.
- Report the number of requests used for each benchmark and the hardware/runtime environment.

A result that is functionally correct but misses these latency targets is not considered fully compliant.
The warm target must be measured with the LLM and SIIS work removed from the critical path.

## Reliability

- Expected calibration error where enough labels exist.
- Coverage at a selected wrong-plan rate.
- Abstention rate.

Do not manufacture calibration results.

---

# 23. Leakage Prevention

Evaluation leakage can make cache performance look artificially good.

Do not evaluate cached paraphrases using the same model family or exact generation process that produced the cache prewarm set.

Test sets should be separated from:

- development queries,
- prewarm queries,
- threshold-fitting data.

The final report must document the split.

---

# 24. Codebase Structure

Recommended structure:

```text
troubleir/
|
├── README.md
├── PRD.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
|
├── data/
│   ├── raw/
│   │   ├── queries.json
│   │   ├── siis_responses.json
│   │   └── deeplinks.json
│   │
│   ├── processed/
│   │   ├── settings_graph.json
│   │   ├── screen_aliases.json
│   │   └── dependency_index.json
│   │
│   └── evaluation/
│       ├── gold.jsonl
│       ├── paraphrases.jsonl
│       ├── contrastive.jsonl
│       ├── compound.jsonl
│       └── drift.jsonl
|
├── src/
│   └── troubleir/
│       ├── api/
│       │   ├── routes.py
│       │   └── schemas.py
│       │
│       ├── ingestion/
│       │   ├── catalog.py
│       │   └── siis.py
│       │
│       ├── understanding/
│       │   ├── normalize.py
│       │   ├── clause_splitter.py
│       │   ├── intent.py
│       │   └── enrichment.py
│       │
│       ├── ir/
│       │   ├── models.py
│       │   └── parser.py
│       │
│       ├── compiler/
│       │   ├── grounding.py
│       │   ├── screen_resolution.py
│       │   ├── grouping.py
│       │   ├── binding.py
│       │   ├── categorization.py
│       │   ├── ordering.py
│       │   ├── surfacing.py
│       │   └── lint.py
│       │
│       ├── graph/
│       │   ├── builder.py
│       │   ├── resolver.py
│       │   ├── aliases.py
│       │   └── gap_miner.py
│       │
│       ├── cache/
│       │   ├── store.py
│       │   ├── lookup.py
│       │   ├── admission.py
│       │   ├── composer.py
│       │   └── invalidation.py
│       │
│       ├── calibration/
│       │   ├── features.py
│       │   ├── metamorphic.py
│       │   └── calibrator.py
│       │
│       ├── guards/
│       │   └── validation.py
│       │
│       └── evaluation/
│           ├── metrics.py
│           ├── runners.py
│           └── reports.py
|
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
|
├── scripts/
│   ├── build_graph.py
│   ├── build_cache.py
│   ├── generate_twins.py
│   ├── run_evaluation.py
│   ├── benchmark_latency.py
│   └── diff_catalog.py
|
├── experiments/
│   ├── baseline_b0/
│   ├── baseline_b1/
│   ├── ablations/
│   └── results/
|
├── demo/
│   ├── app/
│   └── fixtures/
|
└── docs/
    ├── architecture.md
    ├── evaluation.md
    ├── data-contract.md
    └── known-limitations.md
```

---

# 25. API Design

## POST `/v1/troubleshoot`

Request:

```json
{
  "query": "My phone is getting very hot and battery drains quickly",
  "siis_response": "Optional Samsung support/SIIS content"
}
```

Response must conform to the official Samsung schema.

Additional internal metadata may be exposed only where permitted by the official contract.

Potential internal metadata:

```json
{
  "cache_hit": true,
  "reliability": 0.91,
  "diagnostics": [],
  "dependencies": [
    "deeplink_42"
  ]
}
```

Do not modify the official response contract merely for convenience.

---

# 26. Error and Abstention Model

Use explicit internal diagnostics.

Examples:

```text
E204 UNGROUNDED_OPERATION
E310 PARENT_MENU_MATCH
E401 INVALID_DEEPLINK
E402 URL_LEAK
E403 SCHEMA_FAILURE
E501 CACHE_POLARITY_MISMATCH
E502 CACHE_SLOT_MISMATCH
E601 STALE_DEPENDENCY
E701 LOW_RELIABILITY
```

Errors should be useful during development and evaluation.

User-facing output must remain compliant with the official schema.

---

# 27. Build Phase Plan

The implementation must be staged so that the team does not spend the entire hackathon building optional research features.

## Phase 0: Asset Audit

### Goal

Understand the actual Samsung assets before designing around assumptions.

### Tasks

- Locate all supplied files.
- Inspect `queries.json`.
- Inspect `siis_responses.json`.
- Inspect `deeplinks.json`.
- Inspect schema definitions.
- Determine actual deeplink fields.
- Determine validation entry coverage.
- Determine `dummy_positive` behavior from official examples.
- Check whether catalog descriptions are sufficiently informative.
- Identify One UI/version metadata.

### Gate

Do not proceed to advanced architecture until the assets are understood.

---

# 28. Phase 1: Baseline

### Build

Implement the simplest compliant pipeline:

```text
Query
 -> enrichment
 -> extraction
 -> deeplink mapping
 -> ordering
 -> cache
 -> API
```

### Goal

Create something that works before introducing TroubleIR.

### Deliverables

- B0 raw LLM baseline.
- B1 reference pipeline.
- Basic test runner.
- Initial metrics.

### Gate

If B1 already performs extremely well, reassess whether the proposed innovation is necessary.

---

# 29. Phase 2: TroubleIR Core

### Build

- Structured IR.
- Source spans.
- Grounding validator.
- Deterministic compiler.
- Output linting.
- Exact catalog binding.

### Deliverables

- P1 grounding.
- P4 binding.
- P8 lint.
- Diagnostic system.

### Gate

Demonstrate a measurable reduction in invalid/ungrounded outputs against B0/B1.

---

# 30. Phase 3: SettingsGraph

### Build

- Graph extraction.
- Alias normalization.
- Catalog node attachment.
- Parent/ancestor detection.
- Exact-screen resolver.

### Deliverables

- `settings_graph.json`.
- Graph visualization for demo.
- Exact-screen benchmark.

### Gate

Only keep this feature as a headline component if it improves exact-screen accuracy or reduces parent-menu errors.

---

# 31. Phase 4: Verified Compositional Cache

### Build

- Atom representation.
- Clause splitting.
- Atom lookup.
- Polarity/slot agreement.
- Contrastive threshold fitting.
- Atom composition.
- Dependency tracking.

### Deliverables

- Cache implementation.
- Contrastive benchmark.
- Compound benchmark.
- Latency benchmark.

### Gate

Show that the cache does not simply maximize hit rate at the cost of incorrect plans.

---

# 32. Phase 5: Reliability / Metamorphic Layer

### Build only after the core works.

- Query variation generation.
- Variation agreement.
- Admission filtering.
- Reliability features.
- Calibration if sufficient labels exist.

### Gate

If there are too few reliable labels, do not fabricate a sophisticated calibration claim.

Report the feature as an experimental reliability signal instead.

---

# 33. Phase 6: Optional Features

Build only if the core system is already stable.

Priority order:

1. Catalog drift invalidation demo.
2. Gap miner.
3. Guarded plans.
4. More sophisticated calibration.

Do not let optional features destabilize the required pipeline.

---

# 34. Three-Person Team Allocation

## Person 1: Compiler / IR

Responsible for:

- LLM extraction.
- TroubleIR.
- grounding.
- compilation.
- output validation.

## Person 2: SettingsGraph

Responsible for:

- graph construction.
- screen resolution.
- aliases.
- deeplink mapping.
- gap miner.

## Person 3: Cache / Performance

Responsible for:

- semantic cache.
- atomization.
- contrastive protection.
- dependency tracking.
- latency.

## Person 4: Evaluation / Integration

Responsible for:

- baselines.
- gold data.
- test sets.
- metrics.
- API integration.
- demo.

All three members should share responsibility for final integration.

---

# 35. Suggested 48-Hour Schedule

## Hours 0-4

- Asset audit.
- Schema inspection.
- Catalog inspection.
- Define baseline.
- Assign team responsibilities.

## Hours 4-12

- B0 raw LLM.
- B1 reference pipeline.
- Basic API.
- Basic validators.
- Initial evaluation set.

## Hours 12-22

- TroubleIR.
- Grounding.
- Deterministic binding.
- Output linting.
- First comparison against B0/B1.

## Hours 22-30

- SettingsGraph.
- Exact-screen resolver.
- Parent-menu rejection.
- Screen accuracy benchmark.

## Hours 30-37

- Atom cache.
- Contrastive protection.
- Compound composition.
- Dependency tracking.

## Hours 37-41

- Latency optimization.
- Metamorphic admission.
- Reliability experiment if labels permit.

## Hours 41-44

- Full evaluation.
- Ablations.
- Metrics report.
- Known limitations.

## Hours 44-48

- Demo.
- Presentation.
- Backup video.
- Final testing.
- Freeze code.

---

# 36. Required Ablation Study

At minimum:

```text
B1 Reference pipeline

B2 B1 + TroubleIR grounding

B3 B2 + SettingsGraph

B4 B3 + verified cache

B5 B4 + metamorphic admission
```

Additional ablations:

```text
without polarity agreement
without slot agreement
without graph ancestor rejection
without dependency invalidation
without admission filtering
```

This prevents the final architecture from becoming a collection of features that were never shown to matter.

---

# 37. Demo Strategy

The demo should show **decisions and evidence**, not just a chatbot UI.

Recommended sequence:

### Demo 1: Normal complaint

Show:

```text
User complaint
      |
      v
Extracted intent
      |
      v
Source evidence
      |
      v
Screen
      |
      v
Deeplink
      |
      v
Final action
```

### Demo 2: Parent-menu failure

Show two candidates:

```text
Display                 rejected
Display -> Navigation   accepted
```

Explain why the graph rejects the parent.

### Demo 3: Contrastive cache

Show:

```text
"screen too dim"
"screen too bright"
```

with high semantic similarity but different polarity.

Demonstrate that the cache does not return the wrong plan.

### Demo 4: Compound complaint

Show:

```text
screen flickers
+
battery drains
```

and demonstrate atom composition.

### Demo 5: Catalog drift

Change/remove one catalog entry.

Show only dependent plans becoming stale.

### Demo 6: Honest abstention

Give an unsupported query.

Show:

```text
fallback: no_match
```

This is preferable to fabricated troubleshooting.

---

# 39. Four-Minute Demo Script

The live demo must fit within approximately four minutes. It should demonstrate technical decisions,
not a generic chatbot interface.

| Time | Demo | What to show |
|---|---|---|
| 0:00-0:40 | Baseline vs TroubleIR | Same complaint sent to B0 and TroubleIR. Show schema compliance, grounding, and valid screen/deeplink binding. |
| 0:40-1:10 | Provenance | Click one action and highlight the exact SIIS sentence/source span that supports it. |
| 1:10-1:35 | SettingsGraph | Show the correct target screen and a parent-menu candidate rejected by the graph. |
| 1:35-2:00 | Reliability + LLM skip | Show a clean SIIS response taking the deterministic branch, then an ambiguous response taking the LLM branch. |
| 2:00-2:25 | Paraphrase cache | Send a typo-heavy paraphrase and show `cache_hit: true`, low latency, and zero cold-path LLM cost. |
| 2:25-2:50 | Contrastive refusal | Show two opposite queries with high embedding similarity. Demonstrate polarity/slot protection rejecting the wrong cached plan. |
| 2:50-3:15 | Compound query | Combine two previously cached atoms and show a new multi-intent plan without a whole-query cache miss. |
| 3:15-3:35 | Honest no-match | Query with no SIIS and no verified cache atom. Return `contexts: []` and `fallback: no_match`. |
| 3:35-3:50 | Catalog drift | Remove/change one catalog entry and show only dependent plans becoming stale. |
| 3:50-4:00 | Close | Show measured B0/B1/TroubleIR metrics, latency numbers, and the gap-miner output. |

### Backup plan

Keep all of the following ready locally:

- recorded end-to-end demo video,
- precomputed evaluation results,
- prebuilt SettingsGraph,
- cached demo responses,
- a static `results.jsonl`,
- screenshots of the provenance and drift views.

If the external LLM API is slow or unavailable during the presentation, switch to the recorded video
and use the local results to explain the same measured behavior. Do not pretend a prerecorded result
is live.

# 38. Evidence and Provenance UI

The demo UI should have a technical inspection mode.

For each action show:

```text
Intent
Source sentence
Source span
Resolved screen
Catalog entry
Deeplink status
Ordering reason
Cache status
Reliability signal
```

The UI should be secondary to the underlying system.

---

# 39. Security and Safety

The system should prevent:

- arbitrary URL injection,
- unsupported deeplink generation,
- unsupported troubleshooting instructions,
- accidental execution of destructive actions without proper ordering/evidence.

The system should distinguish:

```text
informational/manual step
```

from:

```text
executable navigation action
```

Critical operations should be handled according to the official task's ordering and schema requirements.

---

# 40. Data Integrity

Never modify the original Samsung assets.

Use:

```text
data/raw/
```

for immutable source files.

Derived artifacts belong in:

```text
data/processed/
```

Every derived graph/cache/calibration artifact should record:

- source file hash,
- generation timestamp,
- generator version.

This makes experiments reproducible.

---

# 41. Reproducibility

Every reported metric must be reproducible using a command such as:

```bash
python scripts/run_evaluation.py
```

Latency:

```bash
python scripts/benchmark_latency.py
```

Graph generation:

```bash
python scripts/build_graph.py
```

Catalog diff:

```bash
python scripts/diff_catalog.py
```

Results should be stored under:

```text
experiments/results/
```

---

# 42. Git and Commit Discipline

Use small, meaningful commits.

Recommended commit groups:

```text
chore: initialize project
feat: add asset loaders
feat: implement baseline pipeline
feat: add TroubleIR models
feat: add grounding validator
feat: add SettingsGraph builder
feat: add screen resolver
feat: add verified cache
feat: add dependency invalidation
feat: add evaluation suite
feat: add latency benchmark
feat: add demo inspection view
docs: add evaluation results
docs: add known limitations
```

Avoid meaningless commits made solely to increase commit count.

---

# 43. Known Risks

## Risk 1: Sparse catalog descriptions

Mitigation:

- use SIIS navigation paths,
- retain evidence,
- lower confidence,
- abstain when necessary.

## Risk 2: Insufficient validation entries

Mitigation:

- drop guarded plans from MVP.

## Risk 3: Incorrect clause splitting

Mitigation:

- confidence/consistency check,
- fall back to whole-query cold processing.

## Risk 4: Too little labeled data

Mitigation:

- use cross-validation carefully,
- avoid formal guarantees,
- report limitations.

## Risk 5: Graph introduces false relationships

Mitigation:

- every edge retains evidence,
- manual inspection,
- do not infer unsupported relationships.

## Risk 6: Baseline already performs well

Mitigation:

- measure first,
- remove features that do not provide measurable value,
- do not force an innovation narrative.

---

# 44. Innovation Criteria

A feature is allowed to be called a meaningful contribution only if it satisfies at least one of:

1. Reduces an important measured failure mode.
2. Improves latency without reducing correctness.
3. Improves cache correctness at comparable hit rate.
4. Improves exact-screen resolution.
5. Makes catalog changes safer to manage.
6. Produces a useful Samsung engineering artifact.
7. Enables reliable abstention where the baseline produces an incorrect plan.

Do not call something innovative merely because it contains an LLM, graph, embeddings, or a new UI.

---

# 45. Claims We Must NOT Make

Do not say:

- "This has never been done before."
- "LLMs cannot find deeplinks."
- "Zero hallucinations."
- "Guaranteed correctness."
- "Perfect screen resolution."
- "The graph understands Samsung Settings automatically."
- "The cache is always correct."

Instead use measurable statements:

- "The compiler reduced ungrounded operations by X% on our test set."
- "Parent-menu errors decreased from X to Y."
- "False-hit rate decreased from X to Y at matched cache hit rate."
- "Affected cached plans were invalidated correctly in X/Y drift tests."

---

# 45. Positioning, Moat, and Future Integration

## 45.1 What should look technically defensible

The strongest moat is not the use of an LLM. It is the structured operational layer around Samsung's
support knowledge:

- a screen hierarchy reconstructed from Samsung-specific evidence,
- deterministic screen/deeplink binding,
- a plan store with explicit catalog/SIIS dependencies,
- measured cache correctness,
- contrastive protection against polarity-opposite queries,
- explicit abstention,
- a drift mechanism that can identify stale plans,
- a gap-miner report that identifies support paths lacking deeplinks.

The moat should be demonstrated with measurements, not described as a vague "AI advantage."

## 45.2 What would look like AI slop

Do not spend hackathon time on:

- agentic architecture diagrams with no measurable purpose,
- chatbot typing animations,
- decorative One UI replicas,
- predictive maintenance based on synthetic telemetry,
- seeded feedback numbers,
- LLM-invented confidence values,
- claims of "zero hallucination" without a test set,
- unnecessary multi-turn conversation,
- features that do not improve an official metric or a named failure mode.

## 45.3 Future Samsung integration

These are future integration paths, not MVP requirements:

1. ingest SIIS knowledge continuously rather than from a static asset dump;
2. use One UI release diffs to trigger dependency-aware cache invalidation;
3. evaluate validation guards against real device state;
4. route low-reliability plans to a support/agent console;
5. use the gap miner to identify screens that need catalog deeplinks;
6. maintain versioned SettingsGraphs for different One UI releases.

## 45.4 Questions for organizers

Confirm these before final implementation if the organizers provide a clarification channel:

- May a cold query without SIIS retrieve from `siis_responses.json`, or must it return `no_match`?
- What is the exact rule for `dummy_positive` versus a catalog URI?
- Are multiple Goals acceptable for compound complaints?
- Is the final judge automated against a reference plan?
- Are masked URIs placeholders only, or can they ever be valid output values?
- Which One UI/catalog version should be treated as authoritative?
- Is `validationDeeplink` expected in the final response whenever a validation entry exists, or is it optional?

# 46. Final MVP Definition

The MVP is complete when all of the following work:

- [ ] Samsung assets load successfully.
- [ ] Official response schema validates.
- [ ] B0 baseline works.
- [ ] B1 reference pipeline works.
- [ ] TroubleIR extraction works.
- [ ] Source grounding works.
- [ ] Exact catalog binding works.
- [ ] SettingsGraph or an evidence-backed screen resolver works.
- [ ] Parent-menu rejection works where applicable.
- [ ] Semantic cache works.
- [ ] Contrastive cache protection works.
- [ ] Compound queries can be evaluated.
- [ ] Warm-path latency is measured.
- [ ] Cold-path latency is measured.
- [ ] `no_match` behavior works.
- [ ] Evaluation split is leakage-aware.
- [ ] Results are reproducible.
- [ ] At least one measurable improvement over B1 is demonstrated.

---

# 47. Final Success Criteria

The project is successful if the team can demonstrate:

1. The system satisfies the official Samsung task requirements.
2. The baseline pipeline works without relying on the proposed innovations.
3. Each additional architectural component has a measurable reason to exist.
4. The system reduces important failure modes rather than merely adding complexity.
5. Cache correctness is evaluated, not assumed.
6. Screen resolution is evaluated, not assumed.
7. The system can abstain instead of fabricating unsupported plans.
8. Catalog changes can be handled without silently serving stale plans.
9. The final demo shows technical decisions and evidence.
10. All claims are supported by measured experiments.

---

# 48. Guiding Principle

The project should always pass this test:

> If removing our system and replacing it with a general LLM plus the Samsung documentation produces essentially the same result, then our system is not solving a meaningful additional problem.

Therefore:

**Do not build architecture for the sake of architecture.**

First establish the baseline.

Then identify where it fails.

Then build the smallest mechanism that fixes that failure.

Then measure the improvement.

That is the core development philosophy of TroubleIR.
