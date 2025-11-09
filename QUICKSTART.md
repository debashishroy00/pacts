# PACTS Quick Start Guide - For Business Users

**PACTS v3.1s** - Universal web testing made simple. Test any website with zero code!

---

## 🚀 Running Tests (Super Simple!)

### Single Test

Just use the test filename from the `requirements/` folder:

**Windows**:
```cmd
pacts test salesforce_create_contact.txt
pacts test wikipedia_search.txt
```

**Mac/Linux**:
```bash
./pacts test salesforce_create_contact.txt
./pacts test wikipedia_search.txt
```

**Tip**: You can omit the `.txt` extension:
```bash
pacts test salesforce_create_contact
```

---

### 🆕 Run All Tests (v3.1s)

Run every test in a folder automatically:

```bash
# Run all tests in requirements/ folder
pacts test requirements/

# Run all Salesforce tests
pacts test requirements/salesforce_*.txt

# Run all tests in a specific folder
pacts test tests/smoke/
```

**Output Example**:
```
Discovering tests: requirements/
Found 8 test file(s)

Running tests... ━━━━━━━━━━━━━━━━━━━━━ 100%

                Test Results Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Test File               ┃ Status  ┃ Time   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ wikipedia_search.txt    │ ✅ PASS │ 8.2s   │
│ salesforce_contact.txt  │ ✅ PASS │ 12.5s  │
│ github_search.txt       │ ✅ PASS │ 10.1s  │
└─────────────────────────┴─────────┴────────┘

🎉 All tests passed! Total: 30.8s
```

---

## 📋 Available Tests

All test files are in the `requirements/` folder. Here are the main ones:

| Test File | What It Tests |
|-----------|---------------|
| `salesforce_create_contact.txt` | Create a Salesforce Contact |
| `salesforce_create_account.txt` | Create a Salesforce Account |
| `salesforce_opportunity_postlogin.txt` | Create a Salesforce Opportunity |
| `wikipedia_search.txt` | Search Wikipedia |
| `github_search.txt` | Search GitHub |
| `amazon_search.txt` | Search Amazon |
| `reddit_search.txt` | Search Reddit |
| `youtube_search.txt` | Search YouTube |

**See all available tests**: Check the `requirements/` folder for the complete list.

---

## 🔧 Advanced Options

### Run Tests in Parallel (Faster!)

```bash
# Run 3 tests at the same time
pacts test requirements/ --parallel=3
```

### Clear Cache (Clean Test)

```bash
pacts test salesforce_create_contact.txt --clear-cache
```

### Slow Motion (See What's Happening)

```bash
pacts test salesforce_create_contact.txt --slow-mo 500
```

### Different Browser

```bash
# Use Firefox instead of Chrome
pacts test wikipedia_search.txt --browser firefox

# Options: chromium (default), firefox, webkit
```

### Combine Options

```bash
pacts test requirements/ --parallel=2 --clear-cache
```

---

## 🆕 Data-Driven Testing (v3.1s)

Run the same test with multiple datasets - perfect for testing with different users or data!

### Example: Test Login with Multiple Users

**1. Create test template** (`tests/login.yaml`):
```yaml
name: login_test
steps:
  - go: https://example.com/login
  - fill: { selector: "#username", value: "${username}" }
  - fill: { selector: "#password", value: "${password}" }
  - assert_text: { contains: "${expected_message}" }
```

**2. Create dataset** (`tests/users.csv`):
```csv
username,password,expected_message
alice@test.com,pass123,Welcome Alice
bob@test.com,pass456,Welcome Bob
charlie@test.com,pass789,Welcome Charlie
```

**3. Run with dataset**:
```bash
pacts test tests/login.yaml --data tests/users.csv
```

**Result**: Test runs 3 times (once per user) automatically!

**Supported formats**: CSV, JSON Lines, YAML

---

## 🔐 Salesforce Session Management (Fully Automatic!)

PACTS automatically manages your Salesforce sessions! No manual steps required.

### What Happens When You Run a Salesforce Test:

1. **Session check**: PACTS checks if your session is valid (< 2 hours old)
2. **Auto-refresh** (if expired): Browser opens automatically for you to log in
3. **Auto-detection**: PACTS detects when you've successfully logged in
4. **Test continues**: Your test runs automatically with the fresh session

### Example Workflow:

```bash
# Run a Salesforce test
pacts test salesforce_create_contact.txt

# If session is expired, you'll see:
# [PACTS] Salesforce session expired - refreshing automatically...
#
# ======================================================================
#   SALESFORCE LOGIN REQUIRED
# ======================================================================
#
#   Please complete login in the browser window:
#     1. Enter username
#     2. Enter password
#     3. Complete 2FA if prompted
#
#   PACTS will auto-detect when you're logged in...
#   (No need to create any files manually!)
#
# ======================================================================

# After you log in, PACTS automatically continues:
# [SF] ✓ Login detected!
# [SF] ✓ Session saved
# [PACTS] Session refreshed successfully! Continuing with test...
```

**That's it!** Just log in when prompted, and PACTS handles everything else. Your session is valid for ~2 hours.

---

## 🥷 Stealth Mode (v3.1s)

PACTS now runs in **stealth mode** by default - headless browsers behave like real users, avoiding detection on sites like GitHub and modern SPAs.

**What it does**:
- Hides automation indicators
- Normalizes browser fingerprint
- Avoids "headless browser detected" blocks

**It's automatic!** No configuration needed. Just run your tests normally.

---

## 🎯 Quick Reference Card

| Task | Command |
|------|---------|
| Run single test | `pacts test test_name.txt` |
| Run all tests in folder | `pacts test tests/` |
| Run with pattern | `pacts test tests/salesforce_*.txt` |
| Run in parallel | `pacts test tests/ --parallel=3` |
| Clear cache first | `pacts test test_name.txt --clear-cache` |
| Slow motion demo | `pacts test test_name.txt --slow-mo 500` |
| Use dataset | `pacts test test.yaml --data users.csv` |
| Different browser | `pacts test test.txt --browser firefox` |

---

## 💡 Tips for Success

### ✅ Do This:
- Use descriptive test filenames (`salesforce_create_contact.txt`)
- Keep test files in the `requirements/` or `tests/` folder
- Run with `--clear-cache` for clean validation
- Use `--parallel` for faster test suites

### ❌ Avoid This:
- Don't mix test types in same run (separate Salesforce from public sites)
- Don't run too many parallel tests (3-5 max for stability)
- Don't interrupt Salesforce login flow (wait for auto-detection)

---

## 🆘 Troubleshooting

### Test Failed?
```bash
# Try with fresh cache
pacts test test_name.txt --clear-cache

# Try in slow motion to see what's happening
pacts test test_name.txt --slow-mo 1000
```

### Salesforce Login Issues?
- Make sure you complete 2FA if prompted
- Wait for PACTS to detect login (don't close browser)
- Session is valid for ~2 hours - re-run test if expired

### Need More Help?
- Check test output for specific error messages
- Review screenshots in `screenshots/` folder (auto-captured on failures)
- Contact your test automation team

---

## 🎉 That's It!

No complex commands, no Docker knowledge needed, no coding required. Just type the test name and PACTS does the rest!

**New in v3.1s**:
- ✅ Run all tests with folder path or glob patterns
- ✅ Parallel execution for faster test suites
- ✅ Data-driven testing with CSV/JSON/YAML
- ✅ Stealth mode for universal compatibility
- ✅ Pretty console output with progress bars

---

**Need help?** Contact your test automation team or see the full [README.md](README.md)

**For developers**: See [docs/PACTS-v3.1s-IMPLEMENTATION.md](docs/PACTS-v3.1s-IMPLEMENTATION.md) for technical details
