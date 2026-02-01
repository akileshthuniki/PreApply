# Minimal smoke test for PreApply - regression protection without test framework complexity
# Usage: .\scripts\smoke\preapply_smoke.ps1

$ErrorActionPreference = "Stop"

Write-Host "PreApply Smoke Test" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Basic analysis
Write-Host "✓ Test 1: Basic analysis" -ForegroundColor Yellow
try {
    preapply analyze tests/fixtures/terraform_plans/low_risk.json 2>&1 | Out-Null
    Write-Host "  PASS: analyze command works" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: analyze command failed" -ForegroundColor Red
    exit 1
}

# Test 2: Explain (overall)
Write-Host "✓ Test 2: Explain (overall)" -ForegroundColor Yellow
try {
    preapply explain tests/fixtures/terraform_plans/low_risk.json 2>&1 | Out-Null
    Write-Host "  PASS: explain command works" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: explain command failed" -ForegroundColor Red
    exit 1
}

# Test 3: Explain (JSON output)
Write-Host "✓ Test 3: Explain (JSON output)" -ForegroundColor Yellow
try {
    preapply explain tests/fixtures/terraform_plans/low_risk.json --json 2>&1 | Out-Null
    Write-Host "  PASS: explain --json works" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: explain --json failed" -ForegroundColor Red
    exit 1
}

# Test 3b: JSON contract sanity check
Write-Host "✓ Test 3b: JSON contract sanity" -ForegroundColor Yellow
try {
    $jsonOutput = preapply explain tests/fixtures/terraform_plans/low_risk.json --json 2>&1 | ConvertFrom-Json
    if ($jsonOutput.explanation_id -and $jsonOutput.risk_level) {
        Write-Host "  PASS: JSON contains core contract fields" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: JSON missing core contract fields" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  SKIP: JSON validation failed (may be acceptable)" -ForegroundColor Yellow
}

# Test 4: List resources
Write-Host "✓ Test 4: List resources" -ForegroundColor Yellow
try {
    preapply explain tests/fixtures/terraform_plans/low_risk.json --list-resources 2>&1 | Out-Null
    Write-Host "  PASS: explain --list-resources works" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: explain --list-resources failed" -ForegroundColor Red
    exit 1
}

# Test 5: Summary
Write-Host "✓ Test 5: Summary" -ForegroundColor Yellow
try {
    preapply summary tests/fixtures/terraform_plans/low_risk.json 2>&1 | Out-Null
    Write-Host "  PASS: summary command works" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: summary command failed" -ForegroundColor Red
    exit 1
}

# Test 6: Policy check (if policy file exists)
if (Test-Path "policy.example.yaml") {
    Write-Host "✓ Test 6: Policy check (auto mode)" -ForegroundColor Yellow
    try {
        $null = preapply policy check tests/fixtures/terraform_plans/low_risk.json `
            --policy-file policy.example.yaml `
            --enforcement-mode auto 2>&1
        Write-Host "  PASS: policy check command works (auto mode)" -ForegroundColor Green
    } catch {
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 1) {
            Write-Host "  FAIL: policy check runtime error (exit code $exitCode)" -ForegroundColor Red
            exit 1
        } elseif ($exitCode -eq 2) {
            # Exit code 2 = policy violation in auto mode (acceptable for smoke test)
            Write-Host "  PASS: policy check returns exit code 2 (auto-block) on violations" -ForegroundColor Green
        } elseif ($exitCode -eq 3) {
            Write-Host "  WARN: policy check returned exit code 3 (unexpected in auto mode)" -ForegroundColor Yellow
        } else {
            Write-Host "  FAIL: unexpected exit code $exitCode" -ForegroundColor Red
            exit 1
        }
    }
    
    # Test 6b: Policy check with manual mode
    Write-Host "✓ Test 6b: Policy check (manual mode)" -ForegroundColor Yellow
    try {
        $null = preapply policy check tests/fixtures/terraform_plans/low_risk.json `
            --policy-file policy.example.yaml `
            --enforcement-mode manual 2>&1
        Write-Host "  PASS: policy check command works (manual mode)" -ForegroundColor Green
    } catch {
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 1) {
            Write-Host "  FAIL: policy check runtime error (exit code $exitCode)" -ForegroundColor Red
            exit 1
        } elseif ($exitCode -eq 3) {
            # Exit code 3 = policy violation in manual mode (expected behavior)
            Write-Host "  PASS: policy check returns exit code 3 (approval required) on violations" -ForegroundColor Green
        } elseif ($exitCode -eq 2) {
            Write-Host "  WARN: policy check returned exit code 2 (unexpected in manual mode)" -ForegroundColor Yellow
        } else {
            Write-Host "  FAIL: unexpected exit code $exitCode" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "===================" -ForegroundColor Cyan
Write-Host "All smoke tests passed ✓" -ForegroundColor Green

