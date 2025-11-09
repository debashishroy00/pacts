# Requirements Test Matrix - PACTS v3.1s

**Date**: 2025-11-08
**Purpose**: Comprehensive review and testing of all test cases in `requirements/` folder
**Environment**: PACTS v3.1s with stealth mode enabled

---

## Test Categories

### Category 1: Public Sites (No Auth) ✅ Safe to Test

| File | Site | Complexity | Stealth Critical | Priority |
|------|------|------------|------------------|----------|
| `wikipedia_search.txt` | Wikipedia | Low | No | High |
| `github_search.txt` | GitHub | Low | Yes | High |
| `stackoverflow_search.txt` | Stack Overflow | Low | No | Medium |
| `reddit_search.txt` | Reddit | Medium | Yes | Medium |
| `youtube_search.txt` | YouTube | Medium | Yes | Medium |
| `amazon_search.txt` | Amazon | Medium | Yes | Medium |
| `ebay_search.txt` | eBay | Medium | Yes | Low |
| `tripadvisor_search.txt` | TripAdvisor | Medium | Yes | Low |
| `booking_search.txt` | Booking.com | Medium | Yes | Low |

**Safe to test**: ✅ All tests run in headless mode with stealth, no credentials required

---

### Category 2: Salesforce (Auth Required) ⚠️ Requires Session

| File | Purpose | Session Required | Complexity | Priority |
|------|---------|------------------|------------|----------|
| `salesforce_login.txt` | Basic login flow | No (creates session) | Low | High |
| `salesforce_login_with_2fa_pause.txt` | Login with 2FA wait | No (creates session) | Medium | High |
| `salesforce_with_manual_2fa.txt` | Manual 2FA handling | No (creates session) | Medium | Medium |
| `salesforce_full_hitl.txt` | Full HITL workflow | Yes | High | Low |
| `salesforce_post_login.txt` | Post-login navigation | Yes | Low | High |
| `salesforce_opportunity_postlogin.txt` | Create Opportunity | Yes | Medium | High |
| `salesforce_create_contact.txt` | Create Contact | Yes | Medium | High |
| `salesforce_contact_account.txt` | Contact + Account | Yes | High | Medium |
| `salesforce_create_records.txt` | Bulk record creation | Yes | High | Low |
| `salesforce_full_workflow.txt` | Complete workflow | Yes | Very High | Low |
| `salesforce_opportunity_hitl.txt` | Opportunity HITL | Yes | High | Low |

**Testing approach**:
- ✅ Use existing `hitl/salesforce_auth.json` session
- ✅ Refresh session if needed (automated via wrapper scripts)
- ⚠️ Some tests may modify data - run in dev org only

---

### Category 3: E-Commerce Flows ⚠️ Complex

| File | Purpose | Complexity | Notes |
|------|---------|------------|-------|
| `shopping_e2e.txt` | End-to-end shopping | Very High | May require checkout |
| `shopping_flow.txt` | Shopping cart flow | High | Product availability issues |
| `login_simple.txt` | Generic login | Low | Demo page |

**Testing approach**:
- ⚠️ E-commerce tests may be flaky (product availability, cart state)
- ✅ Simple login test safe to run

---

## Recommended Test Plan

### Phase 1: Quick Smoke (5 tests, ~5 minutes)

**Purpose**: Verify v3.1s works with representative samples

```bash
pacts test requirements/wikipedia_search.txt
pacts test requirements/github_search.txt
pacts test requirements/stackoverflow_search.txt
pacts test requirements/login_simple.txt
pacts test requirements/salesforce_opportunity_postlogin.txt  # If session valid
```

**Expected**: 80%+ pass rate (4/5 tests)

---

### Phase 2: Public Sites Regression (9 tests, ~15 minutes)

**Purpose**: Validate stealth mode across different sites

```bash
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

**Expected**: 75%+ pass rate (7/9 tests)
- Some sites may block or have changed UI

---

### Phase 3: Salesforce Suite (Post-Login, 3 tests, ~10 minutes)

**Purpose**: Validate Salesforce integration with session management

**Prerequisites**: Valid session in `hitl/salesforce_auth.json`

```bash
# Check session validity first
test -f hitl/salesforce_auth.json && echo "Session exists" || echo "Need to refresh"

# Run post-login tests
pacts test requirements/salesforce_post_login.txt
pacts test requirements/salesforce_opportunity_postlogin.txt
pacts test requirements/salesforce_create_contact.txt
```

**Expected**: 100% pass rate (3/3 tests)
- These are production-ready from Week 8 validation

---

### Phase 4: Full Regression (All 23 tests, ~45 minutes)

**Purpose**: Complete test coverage

```bash
# Run all tests
pacts test requirements/

# Or with parallel execution (faster)
pacts test requirements/ --parallel=3
```

**Expected**: 65%+ overall pass rate
- Public sites: 75%+ (some sites change frequently)
- Salesforce: 90%+ (with valid session)
- E-commerce: 50%+ (product availability issues)

---

## Test Execution Commands

### Individual Test

```bash
pacts test requirements/wikipedia_search.txt
```

### Multiple Tests (Pattern)

```bash
pacts test requirements/salesforce_*.txt
pacts test requirements/*_search.txt
```

### All Tests

```bash
pacts test requirements/
```

### With Options

```bash
# Clear cache
pacts test requirements/wikipedia_search.txt --clear-cache

# Slow motion
pacts test requirements/github_search.txt --slow-mo 500

# Parallel execution
pacts test requirements/ --parallel=3
```

---

## Results Template

### Test: [Test Name]

**File**: `requirements/[filename].txt`
**Category**: [Public/Salesforce/E-commerce]
**Run Command**: `pacts test requirements/[filename].txt`

**Expected Outcome**:
- [ ] Test completes successfully
- [ ] All steps execute without errors
- [ ] Expected result visible
- [ ] No stealth mode detection

**Actual Results**:
```
[Paste output here]
```

**Status**: ✅ PASS / ❌ FAIL / ⚠️ FLAKY

**Issues**:
- [List any issues found]

**Screenshots**: `screenshots/[filename]/`

**Logs**: `runs/[timestamp]/`

---

## Known Issues & Limitations

### Public Sites

1. **GitHub Search**: May require CAPTCHA on repeated runs
   - **Mitigation**: Stealth mode reduces frequency
   - **Workaround**: Wait 5 minutes between runs

2. **YouTube Search**: Consent dialog may appear
   - **Mitigation**: Accept cookies programmatically
   - **Status**: Known limitation

3. **Amazon/eBay**: Product listings change frequently
   - **Mitigation**: Use generic search terms
   - **Status**: Tests may be flaky

### Salesforce

1. **Session Expiration**: 2-hour session timeout
   - **Mitigation**: Automatic refresh via wrapper scripts
   - **Status**: Production-ready

2. **Lightning UI Changes**: SF updates UI frequently
   - **Mitigation**: 8-tier discovery handles most changes
   - **Status**: 100% stable selectors (Week 8 validation)

3. **Data Accumulation**: Tests create records
   - **Mitigation**: Run in dev org, clean up manually
   - **Status**: Acceptable for testing

### E-Commerce

1. **Cart State**: Persistent shopping carts
   - **Mitigation**: Clear cookies between runs
   - **Status**: May require manual intervention

2. **Product Availability**: Out of stock items
   - **Mitigation**: Use always-available products
   - **Status**: Tests may fail intermittently

---

## Success Criteria

| Category | Target Pass Rate | Rationale |
|----------|------------------|-----------|
| Public Sites | ≥75% | Sites change frequently, some have bot detection |
| Salesforce | ≥90% | Production-ready from Week 8 |
| E-commerce | ≥50% | Product availability and cart state issues |
| **Overall** | **≥70%** | Realistic for diverse test suite |

---

## Test Execution Log

### [Date: TBD]

**Tester**: [Name]
**Environment**: [Docker/Native]
**PACTS Version**: v3.1s
**Stealth Mode**: Enabled

#### Quick Smoke (Phase 1)

| Test | Status | Duration | Notes |
|------|--------|----------|-------|
| wikipedia_search.txt | ⏳ | - | - |
| github_search.txt | ⏳ | - | - |
| stackoverflow_search.txt | ⏳ | - | - |
| login_simple.txt | ⏳ | - | - |
| salesforce_opportunity_postlogin.txt | ⏳ | - | - |

**Pass Rate**: TBD

#### Public Sites Regression (Phase 2)

| Test | Status | Duration | Notes |
|------|--------|----------|-------|
| All public sites | ⏳ | - | - |

**Pass Rate**: TBD

#### Salesforce Suite (Phase 3)

| Test | Status | Duration | Notes |
|------|--------|----------|-------|
| All Salesforce tests | ⏳ | - | - |

**Pass Rate**: TBD

---

## Recommendations

Based on test results:

1. **Production-Ready Tests**: [List tests suitable for CI/CD]
2. **Flaky Tests**: [List tests that need improvement]
3. **Deprecated Tests**: [List tests that should be removed]
4. **New Tests Needed**: [List gaps in coverage]

---

**Status**: 📋 Test plan ready, awaiting execution
**Next Action**: Run Phase 1 (Quick Smoke) tests
**Estimated Time**: 5 minutes for Phase 1, 45 minutes for full regression

---

Generated by: PACTS v3.1s Test Review
Date: 2025-11-08
