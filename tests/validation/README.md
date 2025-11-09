# PACTS v3.1s - Phase 4 Validation Suite

This directory contains the complete QA validation matrix for PACTS v3.1s, testing universal web compatibility, stealth mode effectiveness, and data-driven execution.

---

## Quick Start

### Run Full Validation

**Linux/Mac**:
```bash
chmod +x run_validation.sh
./run_validation.sh
```

**Windows**:
```cmd
run_validation.bat
```

### Run Individual Suites

```bash
# Static sites (GitHub, Python Docs, Wikipedia)
pacts test static_sites.yaml

# SPAs (React, Vue, Angular)
pacts test spa_sites.yaml

# Authentication flows
pacts test auth_flows.yaml

# Data-driven with CSV
pacts test multi_dataset.yaml --data users.csv

# All suites in parallel
pacts test . --parallel=3
```

---

## Test Suites

### 1. Static Sites (`static_sites.yaml`)

**Purpose**: Verify PACTS works on traditional static websites
**Sites**: GitHub, Python Docs, Wikipedia
**Expected**: 100% pass rate, <2s per step

**What it tests**:
- Basic page navigation
- Content verification (assert_visible)
- URL validation
- Stealth mode (no "enable JavaScript" blocks)

---

### 2. SPA Sites (`spa_sites.yaml`)

**Purpose**: Verify PACTS handles dynamic Single Page Applications
**Sites**: React.dev, Vue.js, Angular.io
**Expected**: 100% pass rate, <3s per step

**What it tests**:
- SPA rendering and hydration
- Dynamic content loading
- Stealth mode on modern frameworks
- No stuck loading spinners

---

### 3. Auth Flows (`auth_flows.yaml`)

**Purpose**: Verify PACTS handles login forms and authentication
**Sites**: GitHub login page, The Internet (demo site)
**Expected**: 90% pass rate (auth can be flaky)

**What it tests**:
- Login page navigation
- Form field discovery and filling
- Submit button interaction
- Success message verification

**Note**: Uses demo credentials for the-internet.herokuapp.com. For real auth testing, set environment variables:
```bash
export GITHUB_TEST_USER=your_test_user
export GITHUB_TEST_PASS=your_test_pass
```

---

### 4. Multi-Dataset (`multi_dataset.yaml` + `users.csv`)

**Purpose**: Verify data-driven execution with template variables
**Rows**: 3 (1 valid user, 2 invalid scenarios)
**Expected**: 100% pass rate, consistent results across rows

**What it tests**:
- Template variable substitution (`${username}`, `${password}`)
- CSV dataset loading
- Independent execution per row
- Correct error message verification

**Dataset**:
```csv
username,password,expected_message
tomsmith,SuperSecretPassword!,You logged into a secure area
fakeuser,wrongpass,Your username is invalid
tomsmith,wrongpass,Your password is invalid
```

---

### 5. Full Parallel (All suites with `--parallel=3`)

**Purpose**: Verify concurrent execution stability
**Expected**: 100% pass rate, total runtime <10 minutes

**What it tests**:
- Browser instance isolation
- No resource conflicts
- CLI output stability under load
- Parallel dataset processing

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Pass Rate | ≥ 95% | Total passed / total run |
| Avg Step Duration (Static) | < 2s | From executor logs |
| Avg Step Duration (SPA) | < 3s | From executor logs |
| Retry Rate | < 5% | Heals / total steps |
| Blocked Headless | < 10% | Stealth detection failures |

---

## Environment Setup

### Required Environment Variables

```bash
# Stealth mode (default: true)
export PACTS_STEALTH=true

# Timezone and locale
export PACTS_TZ=America/New_York
export PACTS_LOCALE=en-US

# Optional: Test credentials for real auth flows
export GITHUB_TEST_USER=your_test_user
export GITHUB_TEST_PASS=your_test_pass
```

### Docker Mode (Recommended)

```bash
# Start infrastructure
docker compose up -d postgres redis

# Run validation in container
docker compose run --rm pacts-runner bash -c "cd tests/validation && ./run_validation.sh"
```

---

## Artifacts Generated

After running validation, artifacts are saved to:

```
runs/validation_YYYYMMDD_HHMMSS/
├── summary.txt                  # Overall pass/fail summary
├── static_sites.log             # Individual suite logs
├── spa_sites.log
├── auth_flows.log
├── multi_dataset.log
├── full_parallel.log
└── screenshots/                 # Auto-captured on failures
    ├── static_sites/
    ├── spa_sites/
    ├── auth_flows/
    └── multi_dataset/
        ├── row_0/               # Per-row screenshots
        ├── row_1/
        └── row_2/
```

---

## Interpreting Results

### Success Output

```
======================================================================
  VALIDATION SUMMARY
======================================================================

Total Tests: 5
Passed: 5
Failed: 0

Pass Rate: 100.0%

🎉 All validation tests passed! v3.1s is production-ready.
```

### Failure Output

```
❌ spa_sites FAILED

Pass Rate: 80.0%

❌ Validation failed (<95% pass rate). Review logs and fix issues.
```

**Next Steps**:
1. Check logs in `runs/validation_*/`
2. Review screenshots for visual debugging
3. Look for error patterns in executor output
4. Fix issues and re-run validation

---

## Common Issues

### Issue: "blocked_headless" Detected

**Symptom**: Pages show "enable JavaScript" or CAPTCHA challenges

**Cause**: Stealth mode not working or disabled

**Fix**:
```bash
export PACTS_STEALTH=true
./run_validation.sh
```

### Issue: SPA Loading Spinners Stuck

**Symptom**: SPAs don't fully render, tests timeout

**Cause**: DOM idle timeout too short for slow networks

**Fix**: Increase wait times in `spa_sites.yaml`:
```yaml
- wait: 5000  # Increase from 3000
```

### Issue: Auth Flows Fail with CAPTCHA

**Symptom**: Login pages show CAPTCHA challenges

**Cause**: Site detected automation despite stealth mode

**Fix**: This is expected for some sites. Use test accounts with CAPTCHA bypass or mark as known limitation.

### Issue: Dataset Rows Not Running Independently

**Symptom**: Variables from one row leak into another

**Cause**: Template engine context not isolated

**Fix**: Check that each row execution uses fresh context (this should be automatic).

---

## Sign-Off Checklist

After validation completes, verify:

- [ ] Pass rate ≥ 95%
- [ ] No stealth mode regressions (<10% blocked)
- [ ] Step durations within targets
- [ ] Retry rate < 5%
- [ ] Total runtime < 10 minutes
- [ ] CLI output clean and readable
- [ ] Screenshots captured on failures
- [ ] All logs saved to `runs/validation_*/`

**If all criteria met**: Document results in [docs/PACTS-v3.1s-VALIDATION.md](../../docs/PACTS-v3.1s-VALIDATION.md)

---

## Troubleshooting

### Validation Script Won't Run

```bash
# Linux/Mac: Make executable
chmod +x run_validation.sh

# Windows: Run from cmd.exe (not PowerShell)
cmd.exe
cd tests\validation
run_validation.bat
```

### Missing Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Docker Container Issues

```bash
# Rebuild container
docker compose build --no-cache pacts-runner

# Check container logs
docker compose logs pacts-runner
```

---

## Next Steps After Validation

1. **Document Results**: Update [PACTS-v3.1s-VALIDATION.md](../../docs/PACTS-v3.1s-VALIDATION.md)
2. **Fix Failures**: Address any issues found during validation
3. **Re-Run**: Ensure 100% pass rate before release
4. **Create Release**: Tag v3.1s in Git
5. **Update README**: Add validation badge to main README

---

**Questions?** See [docs/PACTS-v3.1s-IMPLEMENTATION.md](../../docs/PACTS-v3.1s-IMPLEMENTATION.md) for technical details

**Need help?** Contact the PACTS development team
