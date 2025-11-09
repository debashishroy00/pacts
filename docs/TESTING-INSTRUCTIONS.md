# PACTS v3.1s - Testing Instructions

**Status**: Ready for comprehensive testing
**Test Suite**: 23 test files in `requirements/` folder
**Documentation**: See [docs/REQUIREMENTS-TEST-MATRIX.md](docs/REQUIREMENTS-TEST-MATRIX.md)

---

## Quick Start - Run Tests Now

### Step 1: Start Docker (if using containerized mode)

```bash
docker compose up -d postgres redis
```

**Wait 10 seconds**, then verify:
```bash
docker compose ps
```

### Step 2: Run Quick Smoke Test (5 tests, ~5 minutes)

**Safe public sites - no credentials needed**:

```bash
# Wikipedia (simple, always works)
pacts test requirements/wikipedia_search.txt

# GitHub (stealth mode validation)
pacts test requirements/github_search.txt

# Stack Overflow (public search)
pacts test requirements/stackoverflow_search.txt

# Simple login demo
pacts test requirements/login_simple.txt
```

**Expected**: 3-4 tests should pass (75-100%)

### Step 3: Run v3.1s Validation Suite

```bash
cd tests/validation
./run_validation.sh      # Linux/Mac
run_validation.bat       # Windows
```

This tests:
- Static sites (GitHub, Python Docs, Wikipedia)
- SPAs (React, Vue, Angular)
- Auth flows
- Data-driven execution

**Expected**: ≥95% pass rate

---

## Comprehensive Testing Plan

### Phase 1: Quick Smoke (Recommended First)

Run 5 quick tests to verify v3.1s basics:

```bash
pacts test requirements/wikipedia_search.txt
pacts test requirements/github_search.txt
pacts test requirements/stackoverflow_search.txt
```

**Time**: ~5 minutes
**Expected**: 80%+ pass rate

---

### Phase 2: Public Sites Regression

Test all public sites to validate stealth mode:

```bash
# Run all search tests
pacts test requirements/*_search.txt

# Or individually
pacts test requirements/wikipedia_search.txt
pacts test requirements/github_search.txt
pacts test requirements/stackoverflow_search.txt
pacts test requirements/reddit_search.txt
pacts test requirements/youtube_search.txt
pacts test requirements/amazon_search.txt
pacts test requirements/ebay_search.txt
pacts test requirements/tripadvisor_search.txt
pacts test requirements/booking_search.txt
```

**Time**: ~15 minutes
**Expected**: 75%+ pass rate (some sites have changed since tests were written)

---

### Phase 3: Salesforce Tests (Requires Session)

**Prerequisites**:
1. Valid Salesforce session in `hitl/salesforce_auth.json`
2. Session must be < 2 hours old

**Check session**:
```bash
test -f hitl/salesforce_auth.json && echo "Session exists" || echo "Need to refresh"
```

**Refresh session if needed** (wrapper scripts handle this automatically):
```bash
pacts test requirements/salesforce_login_with_2fa_pause.txt
```

**Run Salesforce tests**:
```bash
# Production-ready tests (from Week 8 validation)
pacts test requirements/salesforce_post_login.txt
pacts test requirements/salesforce_opportunity_postlogin.txt
pacts test requirements/salesforce_create_contact.txt

# All Salesforce tests
pacts test requirements/salesforce_*.txt
```

**Time**: ~10-15 minutes
**Expected**: 90%+ pass rate (these are production-ready)

---

### Phase 4: Full Regression (All 23 Tests)

Run complete test suite:

```bash
# Sequential execution
pacts test requirements/

# Parallel execution (faster, 3 workers)
pacts test requirements/ --parallel=3
```

**Time**: ~30-45 minutes (sequential), ~15-20 minutes (parallel)
**Expected**: 70%+ overall pass rate

**Breakdown**:
- Public sites: 75%+
- Salesforce: 90%+
- E-commerce: 50%+ (flaky due to product availability)

---

## Test Categories & Risk Assessment

### ✅ Low Risk - Safe to Run Anytime

| Test | Site | Notes |
|------|------|-------|
| wikipedia_search.txt | Wikipedia | Always safe, simple |
| stackoverflow_search.txt | Stack Overflow | Public, no auth |
| login_simple.txt | Demo site | Test credentials built-in |

---

### ⚠️ Medium Risk - May Encounter Bot Detection

| Test | Site | Risk |
|------|------|------|
| github_search.txt | GitHub | May show CAPTCHA on repeated runs |
| reddit_search.txt | Reddit | Bot detection possible |
| youtube_search.txt | YouTube | Consent dialogs may appear |
| amazon_search.txt | Amazon | Strong bot detection |
| ebay_search.txt | eBay | Bot detection possible |
| tripadvisor_search.txt | TripAdvisor | May block automated access |
| booking_search.txt | Booking.com | Bot detection possible |

**Mitigation**: Stealth mode reduces risk, but wait 5-10 minutes between runs

---

### 🔐 Auth Required - Salesforce Tests

| Test | Requires Session | Modifies Data |
|------|------------------|---------------|
| salesforce_login.txt | No (creates session) | No |
| salesforce_login_with_2fa_pause.txt | No | No |
| salesforce_post_login.txt | Yes | No |
| salesforce_opportunity_postlogin.txt | Yes | Yes (creates Opportunity) |
| salesforce_create_contact.txt | Yes | Yes (creates Contact) |
| salesforce_contact_account.txt | Yes | Yes (creates Contact + Account) |
| salesforce_create_records.txt | Yes | Yes (bulk records) |
| salesforce_full_workflow.txt | Yes | Yes (complete workflow) |
| salesforce_full_hitl.txt | Yes | Yes (HITL workflow) |
| salesforce_opportunity_hitl.txt | Yes | Yes (HITL Opportunity) |
| salesforce_with_manual_2fa.txt | No | No |

**Notes**:
- ✅ Session management is fully automatic (wrapper scripts)
- ⚠️ Tests that create records should run in dev org only
- ✅ Week 8 validation confirmed 100% pass rate for core tests

---

### 🛒 E-Commerce - High Flakiness

| Test | Site | Issues |
|------|------|--------|
| shopping_e2e.txt | Generic e-commerce | Product availability |
| shopping_flow.txt | Shopping cart | Cart state persistence |

**Expected**: 50% pass rate (flaky due to external factors)

---

## Interpreting Results

### Success Output

```
[PACTS] 🥷 Stealth mode enabled (headless=True)
[RESULT] test=wikipedia_search status=PASS steps=2 heals=0 duration=8.2s
✅ Test completed successfully
```

### Failure Output

```
[RESULT] test=github_search status=FAIL steps=1/2 heals=0 duration=5.1s
❌ Test failed: Selector not found
```

**Check**:
1. Logs in `runs/` folder
2. Screenshots in `screenshots/` folder
3. Error messages in console output

---

## Common Issues & Solutions

### Issue: Docker Not Running

```
error during connect: Get "http://...": The system cannot find the file specified.
```

**Solution**:
```bash
# Start Docker Desktop
# Then start services
docker compose up -d postgres redis
```

---

### Issue: "blocked_headless" - Site Detects Automation

```
[STEALTH] Detected: "Please enable JavaScript"
```

**Solution**:
1. Verify `PACTS_STEALTH=true` in environment
2. Wait 5-10 minutes before retrying
3. Some sites have very aggressive detection (expected)

---

### Issue: Salesforce Session Expired

```
[SF] Session expired or invalid
```

**Solution**:
```bash
# Wrapper scripts handle this automatically
pacts test requirements/salesforce_login_with_2fa_pause.txt

# Then retry your test
pacts test requirements/salesforce_opportunity_postlogin.txt
```

---

### Issue: Test Fails Due to Site Changes

```
[Discovery] No matches found for: "Search box"
```

**Solution**:
1. Site may have changed UI since test was written
2. Check if element exists manually
3. Update test file if needed
4. This is expected for some public sites

---

## Validation Checklist

After running tests, verify:

- [ ] **Quick Smoke** (Phase 1): ≥80% pass (4/5 tests)
- [ ] **Public Sites** (Phase 2): ≥75% pass (7/9 tests)
- [ ] **Salesforce** (Phase 3): ≥90% pass (with valid session)
- [ ] **v3.1s Validation**: ≥95% pass (from validation suite)
- [ ] **Stealth Mode**: <10% blocked_headless rate
- [ ] **No Regressions**: Core tests still pass from Week 8

---

## Reporting Results

### Update Documentation

1. **Results Summary**: Update [docs/REQUIREMENTS-TEST-MATRIX.md](docs/REQUIREMENTS-TEST-MATRIX.md)
2. **Validation Report**: Update [docs/PACTS-v3.1s-VALIDATION.md](docs/PACTS-v3.1s-VALIDATION.md)
3. **Issues Found**: Document in GitHub issues

### Template

```markdown
## Test Run: [Date]

**Environment**: Docker / Native
**PACTS Version**: v3.1s
**Stealth Mode**: Enabled
**Tester**: [Name]

### Results

| Category | Tests | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| Public Sites | 9 | X | Y | Z% |
| Salesforce | 11 | X | Y | Z% |
| E-commerce | 3 | X | Y | Z% |
| **Total** | **23** | **X** | **Y** | **Z%** |

### Issues Found

1. [Issue description]
2. [Issue description]

### Recommendations

1. [Recommendation]
2. [Recommendation]
```

---

## Next Steps

### Immediate (Today)

1. ✅ Start Docker: `docker compose up -d`
2. ✅ Run Quick Smoke: `pacts test requirements/wikipedia_search.txt`
3. ✅ Run v3.1s Validation: `cd tests/validation && ./run_validation.sh`
4. 📝 Document results

### Short-Term (This Week)

1. Run full regression: `pacts test requirements/ --parallel=3`
2. Update test matrix with actual results
3. Fix any high-priority failures
4. Create GitHub release v3.1s

### Long-Term (Next Sprint)

1. Update tests for sites that have changed
2. Add more validation tests
3. Implement CI/CD integration
4. Performance benchmarking

---

## Files & Documentation

- **Test Matrix**: [docs/REQUIREMENTS-TEST-MATRIX.md](docs/REQUIREMENTS-TEST-MATRIX.md)
- **Validation Suite**: [tests/validation/](tests/validation/)
- **Implementation**: [docs/PACTS-v3.1s-IMPLEMENTATION.md](docs/PACTS-v3.1s-IMPLEMENTATION.md)
- **User Guide**: [QUICKSTART.md](QUICKSTART.md)
- **Test Files**: [requirements/](requirements/)

---

**Ready to test!** Start with Quick Smoke tests, then move to full validation. 🚀
