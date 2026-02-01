# PreApply

[![PyPI version](https://img.shields.io/pypi/v/preapply.svg)](https://pypi.org/project/preapply/)
[![Python versions](https://img.shields.io/pypi/pyversions/preapply.svg)](https://pypi.org/project/preapply/)
[![License](https://img.shields.io/pypi/l/preapply.svg)](https://pypi.org/project/preapply/)

**Deterministic infrastructure risk analysis engine for Terraform plans.**

PreApply analyzes Terraform plan JSON files to identify risk factors, calculate blast radius, and provide deterministic recommendations. It helps you understand the impact of infrastructure changes before applying them.

## Features

- 🔍 **Blast Radius Analysis** - Calculate the impact scope of infrastructure changes
- 📊 **Risk Scoring** - Automated risk level assessment (LOW, MEDIUM, HIGH)
- 🔗 **Dependency Graph** - Visualize resource dependencies and relationships
- 🎯 **Deterministic Analysis** - No AI interpretation in core engine, results are reproducible
- 🤖 **AI Advisor** (Optional) - Read-only AI helper powered by Ollama for understanding plans
- 📝 **Multiple Output Formats** - Human-readable and JSON output
- 🚀 **CI/CD Ready** - Integrate into your pipeline for automated risk checks

## Installation

### Basic Installation

```bash
pip install preapply
```

### With AI Support (Optional)

For AI-powered advisory features, install with the `ai` extra:

```bash
pip install 'preapply[ai]'
```

**Note:** AI support requires [Ollama](https://ollama.ai) to be installed and running locally.

## Quick Start

### 1. Generate Terraform Plan

```bash
terraform plan -json > plan.json
```

### 2. Analyze the Plan

```bash
# Human-readable output
preapply analyze plan.json

# Save as JSON for further processing
preapply analyze plan.json --json --output analysis.json
```

### 3. Get Detailed Explanation

```bash
# Explain overall risk assessment
preapply explain analysis.json

# Explain specific resource
preapply explain analysis.json aws_lb.shared
```

### 4. Ask AI Questions (Optional)

```bash
# Requires AI support: pip install 'preapply[ai]'
preapply ask ai "What is the worst case impact?" analysis.json
preapply ask ai "How can I reduce risk?" analysis.json
```

## Usage Examples

### Basic Analysis

```bash
# Analyze Terraform plan
preapply analyze plan.json

# Output:
# Risk Level: MEDIUM
# Blast Radius Score: 45/100
# Affected Resources: 5
# Affected Components: web-tier, database-tier
```

### Save and Reuse Analysis

```bash
# Save analysis as JSON
preapply analyze plan.json --json --output analysis.json

# Use saved analysis for explanations
preapply explain analysis.json
preapply summary analysis.json
```

### AI-Powered Questions

```bash
# Ask about risk assessment
preapply ask ai "What resources are most at risk?" analysis.json

# Get recommendations
preapply ask ai "How can I reduce the blast radius?" analysis.json
```

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

**Example:**
```bash
preapply analyze plan.json --json --output analysis.json
```

### `preapply explain`

Generate deterministic explanations of risk assessment.

```bash
preapply explain <input_file> [resource_id] [OPTIONS]

Options:
  --json              Output structured JSON
  --list-resources    List all available resource IDs
  --quiet             Suppress progress messages
```

**Examples:**
```bash
preapply explain analysis.json
preapply explain analysis.json aws_vpc.main
preapply explain plan.json  # Auto-detects Terraform plan
```

### `preapply summary`

Generate a short paragraph summary of risk assessment.

```bash
preapply summary <plan.json> [OPTIONS]

Options:
  --json          Output structured JSON
  --quiet         Suppress progress messages
```

### `preapply ask`

Ask AI advisor questions about the analysis (requires AI support).

```bash
preapply ask ai "<question>" <analysis.json> [OPTIONS]

Options:
  --model          Ollama model name (default: llama3.2)
  --max-tokens      Maximum tokens for response
  --json           Output JSON format
```

**Example:**
```bash
preapply ask ai "What is the worst case impact?" analysis.json
```

### `preapply version`

Show PreApply version.

```bash
preapply version
```

## Output Format

PreApply returns a structured JSON object (`CoreOutput`) with:

- `risk_level`: `LOW`, `MEDIUM`, or `HIGH`
- `blast_radius_score`: Integer score from 0-100
- `affected_count`: Number of resources affected
- `affected_components`: List of affected component identifiers
- `risk_attributes`: Structured risk attributes including:
  - Shared dependencies
  - Critical infrastructure
  - Blast radius metrics
- `recommendations`: Deterministic recommendations

**Example JSON Output:**
```json
{
  "version": "1.0.0",
  "risk_level": "MEDIUM",
  "blast_radius_score": 45,
  "affected_count": 5,
  "affected_components": ["web-tier", "database-tier"],
  "risk_attributes": {
    "shared_dependencies": [...],
    "critical_infrastructure": [...],
    "blast_radius": {
      "affected_resources": 5,
      "affected_components": 2,
      "changed_resources": 3
    }
  },
  "recommendations": [
    "Review shared resource modifications",
    "Consider impact on dependent services"
  ]
}
```

## AI Advisor

The AI advisor is a **read-only helper** powered by Ollama (local AI). It:

✅ **Can:**
- Help you understand what's inside the plan file
- Answer questions about the analysis
- Provide context about risk factors

❌ **Cannot:**
- Edit or modify anything
- Change risk scores or levels
- Affect policy decisions
- Modify the plan or analysis

**Requirements:**
- Install AI support: `pip install 'preapply[ai]'`
- Install and run [Ollama](https://ollama.ai) locally
- Pull a model: `ollama pull llama3.2`

## Architecture

PreApply processes Terraform plans through five distinct layers:

1. **Ingest** - Loads and normalizes Terraform plan JSON
2. **Graph** - Builds dependency relationships between resources
3. **Analysis** - Calculates blast radius and risk scores
4. **Contracts** - Defines versioned output schema (CoreOutput)
5. **Presentation** - Formats results for human-readable output

## Requirements

- Python 3.8 or higher
- Terraform (for generating plan JSON files)

## Development

### Setup Development Environment

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

## License

Licensed under the Apache License, Version 2.0.

## Support

- **Issues**: [GitHub Issues](https://github.com/akileshthuniki/PreApply/issues)

## Contributing

Contributions are welcome! Please see our contributing guidelines for more information.

---

**PreApply** - Understand your infrastructure changes before you apply them.
