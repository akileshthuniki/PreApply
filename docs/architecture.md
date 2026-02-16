# PreApply Engine: How It Works

This document describes the core analysis engine—the "brain" of PreApply—and how it turns a Terraform plan into a deterministic risk assessment.

---

## 1. High-Level Flow

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Terraform Plan     │     │  PreApply Engine     │     │  CoreOutput /       │
│  (JSON)             │ ──► │  (5 stages)         │ ──► │  Policy / Report    │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

The engine is **fully deterministic**: same plan + same config → same output every time. No AI, no external calls.

---

## 2. Pipeline Overview

The main entry point is `preapply.analyze()` in `src/preapply/__init__.py`. The pipeline runs in this order:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: Ingest                                                             │
│  plan.json → load_plan_json → validate_plan_structure → plan_data (dict)     │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Normalize                                                          │
│  plan_data → normalize_plan → NormalizedPlan (resources, actions, deps)     │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: Graph                                                              │
│  NormalizedPlan.resources → DependencyGraph (nodes + edges)                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: Analysis (parallel signals)                                        │
│  • Blast radius (from graph)                                                 │
│  • Shared resources (from graph)                                             │
│  • Security exposures (from raw plan_data)                                   │
│  • Cost alerts (from raw plan_data)                                          │
│  • Risk scoring (combines all)                                               │
│  • Recommendations                                                           │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: Contract / Output                                                  │
│  CoreOutput (versioned JSON) → Human formatter / Policy engine / JSON       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stage Details

### 3.1 Ingest (`ingest/plan_loader.py`)

- **Input:** Path to Terraform plan JSON
- **Output:** Raw `plan_data` dict
- **Steps:**
  - Load and parse JSON
  - Validate structure (format_version, resource_changes, etc.)
  - Ensure `resource_changes` exists
- **Errors:** `PlanLoadError` if file missing, invalid JSON, or bad structure

---

### 3.2 Normalize (`ingest/plan_normalizer.py`)

- **Input:** Raw `plan_data`
- **Output:** `NormalizedPlan` with list of `NormalizedResource`

Each `NormalizedResource` has:

| Field        | Description                                                |
|-------------|------------------------------------------------------------|
| `id`        | Resource identifier (e.g. `aws_lb.shared`)                 |
| `module`    | Module path if in a module (e.g. `vpc`)                    |
| `type`      | Provider resource type (e.g. `aws_lb`)                     |
| `action`    | Normalized action: CREATE, UPDATE, DELETE, READ, NO_OP     |
| `depends_on`| List of resource addresses this resource depends on        |

**Key logic:**
- **Address parsing:** Extracts resource type, module path, and ID from Terraform addresses
- **Action normalization:** Terraform uses `["create"]`, `["update","delete"]`, etc.; we collapse to a single `ResourceAction`
- **Dependency extraction:** From `depends_on`, `configuration.root_module.resources[].expressions.references`, and fallback string interpolation in before/after values

---

### 3.3 Graph (`graph/dependency_graph.py`)

- **Input:** List of `NormalizedResource`
- **Output:** `DependencyGraph` (NetworkX DiGraph)
- **Structure:**
  - Nodes = resources (keyed by full address, e.g. `module.vpc.aws_vpc.main`)
  - Edges = dependencies (A depends on B → edge from A to B)
  - Direction: if A `depends_on` B → edge `A → B` (A points to B)
- **Operations:**
  - `get_downstream_resources(node)` — resources that depend on this node (predecessors in graph)
  - `get_upstream_resources(node)` — resources this node depends on (ancestors)
  - `get_changed_resources()` — resources with CREATE, UPDATE, or DELETE

---

### 3.4 Analysis

#### 3.4.1 Blast Radius (`analysis/blast_radius.py`)

- **Input:** Graph, changed resources
- **Output:** `{ affected_count, affected_components, changed_count }`
- **Logic:** For each changed resource, collect all downstream dependents. Union them. Count unique components (by module or type).

#### 3.4.2 Shared Resources (`analysis/shared_resources.py`)

- **Input:** Graph, config
- **Output:** List of resources used by **2+** other resources (topology-based)
- **Purpose:** Shared resources are single points of failure; modifying them increases risk

#### 3.4.3 Security Exposures (`analysis/security_exposure.py`)

- **Input:** Raw `plan_data`
- **Output:** `List[SecurityExposure]`
- **Checks:**
  - **Security groups:** Ingress/egress with `0.0.0.0/0` or `::/0`
  - **Port sensitivity:** Exposing SSH (22) or RDP (3389) globally → extra penalty
  - **S3 public:** `block_public_acls`/`block_public_policy` disabled, or ACL `public-read`/`public-read-write`

#### 3.4.4 State-Destructive Updates (`analysis/state_destructive.py`)

- **Input:** Raw `plan_data`
- **Output:** List of resources with protection removed (force_destroy, prevent_destroy, deletion_protection)
- **Purpose:** Feeds data loss dimension (action_weight 0.6)

#### 3.4.5 Cost Analysis (`analysis/cost_analysis.py`)

- **Input:** Raw `plan_data`, config
- **Output:** `List[CostAlert]`
- **Checks:**
  - High-cost type creation (e.g. `aws_nat_gateway`)
  - High-cost instance creation (e.g. `p4d.24xlarge`)
  - Instance scaling: low tier → high tier (e.g. `t3.micro` → `p4d.24xlarge`)

#### 3.4.6 Risk Scoring (`analysis/risk_scoring.py`)

- **Input:** Graph, config, security_exposures, cost_alerts, state_destructive_updates
- **Output:** Score (0–250+), risk level, risk_level_detailed, risk_action, approval_required, risk_attributes

**Production formula:** Multi-dimensional with decay, interaction multipliers, context-aware blast radius. See [scoring-algorithm.md](scoring-algorithm.md).

**Dimensions:** data (deletions, state-destructive updates), security (exposures + port penalty), infrastructure (shared resources × action mult), cost (creations, scalings).

**Risk levels (6-tier):** CRITICAL-CATASTROPHIC, CRITICAL, HIGH-SEVERE, HIGH, MEDIUM, LOW. Mapped to 4-tier (LOW, MEDIUM, HIGH, CRITICAL) for policy matching.

#### 3.4.7 Recommendations (`analysis/recommendations.py`)

- **Input:** Graph, risk_score, config
- **Output:** `List[str]`
- **Logic:** Pattern-based advice (isolate shared resources, warn on deletes, large blast radius, cross-module changes)

---

### 3.5 Contract / Output (`contracts/core_output.py`)

- **Output:** `CoreOutput` (Pydantic model)
- **Fields:** `version`, `risk_level`, `risk_level_detailed`, `blast_radius_score`, `risk_action`, `approval_required`, `affected_count`, `deletion_count`, `affected_components`, `risk_attributes`, `recommendations`
- **risk_attributes** includes: `blast_radius`, `shared_dependencies`, `critical_infrastructure`, `sensitive_deletions`, `security_exposures`, `cost_alerts`, `action_types`, `risk_breakdown`

---

## 4. Policy Engine (`policy/engine.py`)

The policy engine evaluates `CoreOutput` against YAML policies **after** analysis.

- **Input:** `CoreOutput`, explanation ID, policy file
- **Output:** `PolicyEvaluationResult` (passed, results, failure_count, warning_count)

**Match rules:**
- `explanation_id` — matches explanation type
- `risk_level` — LOW / MEDIUM / HIGH / CRITICAL (4-tier)
- `action_type` — CREATE / UPDATE / DELETE
- `has_sensitive_deletions` — true if RDS/S3 deletes present
- `has_security_exposures` — true if public exposure detected

**Actions:** `fail` (block), `warn` (log only)

---

## 5. Configuration (`config/defaults.yaml`)

- **blast_radius:** Legacy weights (auto-migrated to risk_scoring)
- **risk_scoring:** Production formula (dimensions, interactions, blast radius, thresholds)
- **shared_resources:** `critical_types`, `sensitive_delete_types`
- **cost_alerts:** `high_cost_types`, `high_cost_instance_types`, `instance_cost_tiers`

If `risk_scoring` is absent, config loader auto-migrates from blast_radius and shared_resources.

Override via `PREAPPLY_CONFIG` env or `--config` path.

---

## 6. Data Flow Summary

```
plan.json
    │
    ▼
plan_data (dict)
    │
    ├──► normalize_plan() ──► NormalizedPlan
    │                              │
    │                              ▼
    │                         DependencyGraph
    │                              │
    │                              ├──► blast_radius()
    │                              ├──► shared_resources()
    │                              ├──► risk_scoring(graph, …)
    │                              └──► recommendations()
    │
    ├──► detect_security_exposures() ──► security_exposures
    ├──► detect_state_destructive_updates() ──► state_destructive_updates
    │
    └──► detect_cost_alerts() ──► cost_alerts
                                        │
                                        ▼
                              risk_scoring(graph, config, security_exposures, cost_alerts, state_destructive_updates)
                                        │
                                        ▼
                              CoreOutput ──► JSON / Human / Policy check
```

---

## 7. File Map

| Component       | Path                                      |
|----------------|-------------------------------------------|
| Main pipeline  | `src/preapply/__init__.py`                |
| Ingest         | `ingest/plan_loader.py`, `plan_normalizer.py` |
| Graph          | `graph/dependency_graph.py`              |
| Blast radius   | `analysis/blast_radius.py`                |
| Shared         | `analysis/shared_resources.py`            |
| Security       | `analysis/security_exposure.py`           |
| State-destructive | `analysis/state_destructive.py`       |
| Cost           | `analysis/cost_analysis.py`               |
| Risk scoring   | `analysis/risk_scoring.py`                |
| Recommendations| `analysis/recommendations.py`             |
| Policy         | `policy/engine.py`, `policy/loader.py`   |
| Output         | `contracts/core_output.py`, `risk_attributes.py` |
| Config         | `config/defaults.yaml`                   |

---

*PreApply — Deterministic infrastructure risk analysis.*
