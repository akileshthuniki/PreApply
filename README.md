# PreApply

> Deterministic Terraform plan risk analyzer — know your blast radius *before* you apply.

[![PyPI version](https://img.shields.io/pypi/v/preapply)](https://pypi.org/project/preapply/)
[![PyPI downloads](https://img.shields.io/pypi/dm/preapply)](https://pypi.org/project/preapply/)
[![Python](https://img.shields.io/pypi/pyversions/preapply)](https://pypi.org/project/preapply/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

---

## ⭐ If PreApply saves you from a bad deployment, consider giving it a star!

---

## The Problem

You've been there.

It's deployment day. You run `terraform plan`. The output is 800 lines long.
You scan it. It looks fine. You apply.

Then your load balancer goes down. Three dependent services follow.
Your phone explodes with alerts.

**The problem wasn't carelessness. The problem was that infrastructure
relationships are complex, subtle, and easy to misread under pressure.**

PreApply solves this by analyzing your Terraform plan *before* you apply it —
giving you a clear, deterministic risk assessment you can trust.

---

## What PreApply Does

```
$ preapply analyze plan.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PreApply Risk Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Risk Level:        HIGH ⚠️
  Blast Radius:      72/100
  Affected Resources: 12
  Affected Components: web-tier, database-tier, auth-service

  Recommendations:
  → Review shared resource modifications before applying
  → Database changes will affect 8 downstream services
  → Consider applying in stages to reduce blast radius

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Features

| Feature | Description |
|---------|-------------|
| 🔥 **Blast Radius Analysis** | Exactly which resources get affected |
| 📊 **Risk Scoring** | LOW / MEDIUM / HIGH with 0-100 score |
| 🔗 **Dependency Mapping** | Upstream/downstream impact visualization |
| 🎯 **Deterministic Results** | Same input = same output, every time |
| 🤖 **Local AI Advisor** | Optional plain-language explanations (private, no API calls) |
| 📝 **Multiple Output Formats** | Human-readable and JSON |
| 🚀 **CI/CD Ready** | GitHub Actions, GitLab CI, Jenkins |

---

## Why Deterministic?

Most infrastructure tools try to use AI for risk detection. We don't.

**AI-based risk detection is unreliable for infrastructure decisions because:**
- Non-deterministic (same plan can get different scores)
- Hard to audit or explain to stakeholders
- Can "hallucinate" risks or miss real ones
- Requires external API calls (privacy concern)

**PreApply's approach:**
- Core analysis is 100% deterministic
- AI is optional and advisory only (never changes risk score)
- Every decision is traceable and explainable
- Works fully offline

---

## Installation

```bash
# Basic installation
pip install preapply

# With optional AI advisor support
pip install 'preapply[ai]'
```

> AI support requires [Ollama](https://ollama.ai) installed and running locally.

---

## Quick Start

```bash
# Step 1: Generate Terraform plan
terraform plan -out=tfplan
terraform show -json tfplan > plan.json

# Step 2: Analyze risk
preapply analyze plan.json

# Step 3: Save analysis for detailed review
preapply analyze plan.json --json --output analysis.json

# Step 4: Get detailed explanation
preapply explain analysis.json

# Step 5: Ask AI questions (optional)
preapply ask ai "What is the worst case impact?" analysis.json
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Terraform Risk Analysis

on:
  pull_request:
    paths:
      - '**.tf'

jobs:
  preapply:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Install PreApply
        run: pip install preapply

      - name: Generate Plan
        run: |
          terraform init
          terraform plan -out=tfplan
          terraform show -json tfplan > plan.json

      - name: Analyze Risk
        run: |
          preapply analyze plan.json
          preapply analyze plan.json --json --output analysis.json

      - name: Upload Analysis
        uses: actions/upload-artifact@v3
        with:
          name: risk-analysis
          path: analysis.json
```

---

## Command Reference

### `preapply analyze`
Main analysis command. Analyzes a Terraform plan JSON file.

```bash
preapply analyze <plan.json> [OPTIONS]

Options:
  --json          Output structured JSON instead of human-readable
  --output, -o    Save output to file
  --quiet         Suppress progress messages
```

### `preapply explain`
Generate deterministic explanations of risk assessment.

```bash
preapply explain <input_file> [resource_id] [OPTIONS]

Options:
  --json              Output structured JSON
  --list-resources    List all available resource IDs
```

### `preapply summary`
Generate a short paragraph summary of the risk assessment.

```bash
preapply summary <plan.json> [OPTIONS]
```

### `preapply ask`
Ask AI advisor questions (requires `pip install 'preapply[ai]'`).

```bash
preapply ask ai "<question>" <analysis.json> [OPTIONS]

Options:
  --model       Ollama model name (default: llama3.2)
  --max-tokens  Maximum tokens for response
```

---

## Output Format

PreApply returns a structured `CoreOutput` JSON object:

```json
{
  "version": "1.0.0",
  "risk_level": "HIGH",
  "blast_radius_score": 72,
  "affected_count": 12,
  "affected_components": ["web-tier", "database-tier", "auth-service"],
  "risk_attributes": {
    "shared_dependencies": [...],
    "critical_infrastructure": [...],
    "blast_radius": {
      "affected_resources": 12,
      "affected_components": 3,
      "changed_resources": 5
    }
  },
  "recommendations": [
    "Review shared resource modifications before applying",
    "Database changes will affect 8 downstream services"
  ]
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

## Requirements

- Python 3.8+
- Terraform (for generating plan JSON files)
- Ollama (optional, for AI features)

---

## Development

```bash
# Clone repository
git clone https://github.com/akileshthuniki/PreApply.git
cd PreApply/Core

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Code formatting
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

---

## Contributing

Contributions are welcome! Areas where help is most needed:

- Additional Terraform resource type handlers
- More CI/CD platform integrations
- Documentation improvements
- Test coverage

Please open an issue before submitting a large PR.

---

## License

Licensed under the [Apache License 2.0](LICENSE).

---

## Author

Built by [Akilesh Thuniki](https://github.com/akileshthuniki) —
DevOps Engineer specializing in infrastructure safety and automation.

- 🌐 Portfolio: [akileshthuniki-portfolio.netlify.app](https://akileshthuniki-portfolio.netlify.app)
- 💼 LinkedIn: [linkedin.com/in/akileshthuniki](https://linkedin.com/in/akileshthuniki)
- 📦 PyPI: [pypi.org/project/preapply](https://pypi.org/project/preapply)

---

*PreApply — Because "it looked fine in the plan" isn't good enough.*