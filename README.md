# PreApply

> Deterministic Terraform plan risk analyzer — know your blast radius *before* you apply.

[![PyPI version](https://img.shields.io/pypi/v/preapply)](https://pypi.org/project/preapply/)
[![PyPI downloads](https://img.shields.io/pypi/dm/preapply)](https://pypi.org/project/preapply/)
[![Python](https://img.shields.io/pypi/pyversions/preapply)](https://pypi.org/project/preapply/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

---

## The Problem

You've been there. It's deployment day. You run `terraform plan`. The output is 800 lines long. You scan it. It looks fine. You apply.

Then your load balancer goes down. Three dependent services follow. Your phone explodes with alerts.

**PreApply solves this** by analyzing your Terraform plan *before* you apply it — giving you a clear, deterministic risk assessment you can trust.

---

## What You Get
```
$ preapply analyze plan.json

+===============================================================+
| [!] HIGH RISK - SENIOR ENGINEER APPROVAL REQUIRED             |
+===============================================================+

Risk Score: 96.34 / 250+ (HIGH tier)
Required Action: Obtain approval before applying

WHY THIS IS HIGH:
* Sensitive deletion: aws_db_instance.production
* Security exposure: ingress open to 0.0.0.0/0 (Port 22)

RECOMMENDED ACTIONS:
1. REVIEW DATABASE DELETION - Verify backup before proceeding
2. ADDRESS SECURITY EXPOSURE - Restrict to known IP ranges
3. GET APPROVALS - SENIOR_ENGINEER or TECH_LEAD sign-off required
```

---

## Key Features

- 🔥 **Blast Radius Analysis** — Calculate exactly which resources are affected
- 📊 **Multi-Dimensional Risk Scoring** — 0-250+ score across data loss, security, infrastructure, and cost
- ⚡ **Interaction Detection** — Detects when multiple risks combine into catastrophic scenarios
- 🔐 **Policy Enforcement** — Block hazardous plans in CI/CD (exit codes: 0=pass, 2=block, 3=approval)
- 🎯 **100% Deterministic** — Same plan = same score, every time
- 🤖 **Optional Local AI** — Plain-language explanations (runs offline, no data leaves your machine)

---

---
##  Why Deterministic?
Most infrastructure tools try to use AI for risk detection. We don't.

AI-based risk detection is unreliable for infrastructure decisions because:

Non-deterministic (same plan can get different scores)
Hard to audit or explain to stakeholders
Can "hallucinate" risks or miss real ones
Requires external API calls (privacy concern)
PreApply's approach:

Core analysis is 100% deterministic
AI is optional and advisory only (never changes risk score)
Every decision is traceable and explainable
Works fully offline
---

## Installation
```bash
# Basic installation
pip install preapply

# With optional AI advisor
pip install 'preapply[ai]'

AI support requires Ollama installed and running locally.
```

---

## Quick Start
```bash
# Generate plan
terraform plan -out=tfplan
terraform show -json tfplan > plan.json

# Analyze
preapply analyze plan.json

# Enforce in CI
preapply policy check plan.json --policy-file policy.yaml
```

**Try it now (no Terraform required):**
```bash
preapply analyze samples/low_risk.json
```

---

## CI/CD Integration

### GitHub Actions
```yaml
- name: Install PreApply
  run: pip install preapply

- name: Generate Plan
  run: |
    terraform init
    terraform plan -out=tfplan
    terraform show -json tfplan > plan.json

- name: Risk Analysis & Policy Check
  run: |
    preapply analyze plan.json
    preapply policy check plan.json --policy-file policy.yaml
```

Exit codes: `0` = pass, `2` = blocked, `3` = approval required

---

## Why Deterministic?

**AI-based risk detection is unreliable for infrastructure:**
- Non-deterministic (same plan = different scores)
- Hard to audit or explain
- Can hallucinate risks or miss real ones

**PreApply's approach:**
- 100% deterministic mathematical model
- AI is optional and advisory only (never affects risk score)
- Every decision is traceable and explainable
- Works fully offline

---

## How It Works

PreApply uses a **multi-dimensional risk model**:

1. **Data Loss** — RDS/S3 deletions, protection removal
2. **Security** — Public exposures (0.0.0.0/0), sensitive ports (SSH/RDP)
3. **Infrastructure** — Shared resources, critical infra (VPC, ALB)
4. **Cost** — High-cost creations, instance scaling

**Interaction Multipliers** detect when risks amplify each other:
- Database deletion + security exposure = 1.65× multiplier
- 3+ dimensions elevated = "perfect storm" bonus

**6-Tier Risk Levels:**
- LOW → AUTO_APPROVE
- MEDIUM → REQUIRE_PEER_REVIEW
- HIGH → REQUIRE_APPROVAL (senior engineer)
- HIGH-SEVERE → REQUIRE_APPROVAL (senior + architect)
- CRITICAL → SOFT_BLOCK (VP or director)
- CRITICAL-CATASTROPHIC → HARD_BLOCK (VP + incident review)

---

## Command Reference
```bash
# Analyze a plan
preapply analyze plan.json [--json] [--ascii]

# Policy check (CI/CD)
preapply policy check plan.json --policy-file policy.yaml

# Get explanations
preapply explain analysis.json [resource_id]

# Ask AI (optional, requires Ollama)
preapply ask ai "What's the worst case?" analysis.json
```

---

## Output Format

PreApply outputs structured JSON with:
```json
{
  "version": "1.0.4",
  "risk_level": "HIGH",
  "risk_level_detailed": "HIGH",
  "blast_radius_score": 96.34,
  "risk_action": "REQUIRE_APPROVAL",
  "approval_required": "SENIOR_ENGINEER or TECH_LEAD",
  "risk_breakdown": {
    "primary_dimension": "data",
    "dimensions": {
      "data": 75.5,
      "security": 60.0,
      "infrastructure": 0.0,
      "cost": 0.0
    },
    "interaction_multiplier": 1.35
  },
  "sensitive_deletions": [...],
  "security_exposures": [...],
  "recommendations": [...]
}
```
---

## Architecture

PreApply processes Terraform plans through five layers:

```
Terraform Plan JSON
        │
        ▼
┌─────────────────┐
│   Ingest Layer  │  Loads and normalizes plan JSON
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Graph Layer   │  Builds dependency relationships
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analysis Layer  │  Calculates blast radius + risk scores
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Contract Layer   │  Versioned CoreOutput schema
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Presentation     │  Human-readable or JSON output
└─────────────────┘
```

---

## AI Advisor

The AI advisor is a **read-only** helper powered by Ollama (local AI).

**✅ Can:**
- Help you understand the plan file
- Answer questions about the analysis
- Provide plain-language context about risk factors

**❌ Cannot:**
- Modify anything
- Change risk scores or levels
- Affect policy decisions

**Why local AI?**
Your Terraform plans contain sensitive infrastructure details.
PreApply's AI never sends data to external APIs.
Everything stays on your machine.

---
---

## FAQ

**Does this replace Terraform's plan review?**  
No. It augments it by calculating blast radius and risk scores you can't see in raw output.

**Will this slow down CI/CD?**  
No. Analysis takes <2 seconds for plans with 100+ resources.

**Can I customize the scoring?**  
Yes. See `src/preapply/config/defaults.yaml` for weights and thresholds.

---

## Development
```bash
git clone https://github.com/akileshthuniki/PreApply.git
cd PreApply/Core
pip install -e ".[dev]"

# Validate
preapply analyze samples/low_risk.json

# Format & lint
black src/
ruff check src/
```

---

## Contributing

Contributions welcome! Open an issue before submitting large PRs.

**Help wanted:**
- Additional Terraform resource handlers
- More CI/CD examples
- Documentation improvements

---

## License

Apache License 2.0

---

## Author

Built by [Akilesh Thuniki](https://github.com/akileshthuniki) — DevOps Engineer specializing in infrastructure safety.

- 🌐 [Portfolio](https://akileshthuniki-portfolio.netlify.app)
- 💼 [LinkedIn](https://linkedin.com/in/akileshthuniki)
- 📦 [PyPI](https://pypi.org/project/preapply)

---

*PreApply — Because "it looked fine in the plan" isn't good enough.*