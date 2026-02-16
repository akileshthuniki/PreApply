# PreApply Production Score Engine

How the risk score and risk level are calculated. **Fully deterministic**—same inputs always produce the same output. Uses a multi-dimensional formula with stacking decay, interaction multipliers, and context-aware blast radius.

---

## 1. Formula Overview

```
FinalScore = (R_primary × (1 + Σμ_i)) + (B × ω_context)

Where:
R_primary = max(D_data, D_security, D_infrastructure, D_cost)
Σμ_i = sum of all applicable interaction multipliers
B = 10 × log₂(affected_count + 1)
ω_context = blast radius weight based on primary risk type
```

Score is **not capped**; typical range 0–250+.

---

## 2. Dimension Calculations

### 2.1 Data Loss Dimension

```
D_data = Σ(i=0 to n-1) [50 × (0.85^i) × action_weight(resource_i)]

action_weight:
- DELETE: 1.0
- UPDATE (state-destructive): 0.6
- All others: 0.0

State-destructive: force_destroy true←false, prevent_destroy true←false, deletion_protection enabled←disabled
```

**Critical:** Do NOT use delete_multiplier (2.0) in data loss. The base 50 is high enough.

### 2.2 Security Dimension

```
D_security = Σ(i=0 to n-1) [(base_exposure + port_penalty) × (0.9^i)]

base_exposure = 40
port_penalty = 20 if port in [22, 3389, 1433, 3306, 5432, 5439, 27017] else 0
```

### 2.3 Infrastructure Dimension

```
D_infrastructure = Σ (30 × criticality_mult × action_mult_per_resource)

criticality_mult: Critical types 1.3, Standard 1.0
action_mult_per_resource: DELETE 2.0, UPDATE 1.5, CREATE 1.0
Shared = in-degree ≥ 2 in dependency graph
```

### 2.4 Cost Dimension

```
D_cost = Σ(i=0 to n-1) [cost_weight × (0.9^i)]

cost_weight: Creation 15, Scaling 10
```

---

## 3. Interaction Multipliers (Additive)

| Condition | Bonus |
|-----------|-------|
| D_data ≥ 40 AND D_security ≥ 40 | +0.35 |
| D_infrastructure ≥ 60 AND D_security ≥ 40 | +0.30 |
| D_data ≥ 40 AND D_infrastructure ≥ 60 | +0.25 |
| D_cost ≥ 30 AND D_infrastructure ≥ 60 | +0.20 |
| 3+ dimensions ≥ 35 | +0.40 ("perfect storm") |
| 2 dimensions ≥ 35 | +0.15 |

---

## 4. Blast Radius (Context-Aware)

```
B = 10 × log₂(affected_count + 1)
blast_contribution = B × ω_context

ω by primary dimension:
- infrastructure: 1.0
- security: 0.4
- data: 0.2
- cost: 0.5
```

---

## 5. Risk Level Mapping (6-Tier)

| Level | Score | Action | Approval |
|-------|-------|--------|----------|
| **CRITICAL-CATASTROPHIC** | ≥ 200 | HARD_BLOCK | VP_ENGINEERING + INCIDENT_REVIEW |
| **CRITICAL** | ≥ 150 | SOFT_BLOCK | VP_ENGINEERING or DIRECTOR |
| **HIGH-SEVERE** | ≥ 100 | REQUIRE_APPROVAL | SENIOR_ENGINEER + ARCHITECT |
| **HIGH** | ≥ 70 | REQUIRE_APPROVAL | SENIOR_ENGINEER or TECH_LEAD |
| **MEDIUM** | ≥ 40 | REQUIRE_PEER_REVIEW | ANY_ENGINEER |
| **LOW** | < 40 | AUTO_APPROVE | NONE |

---

## 6. Policy Compatibility (4-Tier)

For policy matching, 6-tier maps to 4-tier:

- CRITICAL-CATASTROPHIC, CRITICAL → `RiskLevel.CRITICAL`
- HIGH-SEVERE, HIGH → `RiskLevel.HIGH`
- MEDIUM → `RiskLevel.MEDIUM`
- LOW → `RiskLevel.LOW`

---

## 7. Configuration Reference

```yaml
# risk_scoring section in defaults.yaml

risk_scoring:
  data_loss:
    base_weight: 50.0
    decay_factor: 0.85
    state_destructive_multiplier: 0.6
  security:
    base_weight: 40.0
    decay_factor: 0.90
    sensitive_port_penalty: 20.0
    sensitive_ports: [22, 3389, 1433, 3306, 5432, 5439, 27017]
  infrastructure:
    shared_resource_base: 30.0
    critical_multiplier: 1.3
  cost:
    creation_weight: 15.0
    scaling_weight: 10.0
    decay_factor: 0.90
  interactions: { ... }
  blast_radius: { ... }
  thresholds:
    critical_catastrophic: 200.0
    critical: 150.0
    high_severe: 100.0
    high: 70.0
    medium: 40.0
```

Legacy config (blast_radius, shared_resources) is auto-migrated when risk_scoring is absent.

---

## 8. Implementation

- **Entry:** `analysis/risk_scoring.py` → `calculate_risk_score()`
- **Scorer:** `ProductionRiskScorer` with dimension methods
- **Inputs:** `DependencyGraph`, config, `security_exposures`, `cost_alerts`, `state_destructive_updates`
- **Outputs:** `blast_radius_score`, `risk_level`, `risk_level_detailed`, `risk_action`, `approval_required`, `risk_attributes` (incl. `risk_breakdown`), `contributing_factors`

---

*PreApply Score Engine — Transparent, configurable, deterministic, production-grade.*
