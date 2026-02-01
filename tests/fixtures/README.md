# Sample Terraform Plans

This directory contains sample Terraform plan JSON files for testing and development.

## Files

- `low_risk.json`: Simple create operation with minimal impact
- `medium_risk.json`: Update operations affecting a VPC module
- `high_risk.json`: Shared resource modifications and delete operations

These sample plans can be used to test PreApply analysis and CLI commands.
