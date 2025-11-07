# PACTS Quick Start Guide - For Business Users

## Running Tests (Super Simple!)

Just use the test filename from the `requirements/` folder:

### Windows
```cmd
pacts test salesforce_create_contact.txt
pacts test salesforce_opportunity_postlogin.txt
pacts test wikipedia_search.txt
```

### Mac/Linux
```bash
./pacts test salesforce_create_contact.txt
./pacts test salesforce_opportunity_postlogin.txt
./pacts test wikipedia_search.txt
```

**Tip**: You can omit the `.txt` extension:
```bash
pacts test salesforce_create_contact
```

## Available Tests

All test files are in the `requirements/` folder. Here are the main ones:

| Test File | What It Tests |
|-----------|---------------|
| `salesforce_create_contact.txt` | Create a Salesforce Contact |
| `salesforce_opportunity_postlogin.txt` | Create a Salesforce Opportunity |
| `salesforce_create_records.txt` | Create Salesforce Account records |
| `wikipedia_search.txt` | Search Wikipedia |
| `amazon_search.txt` | Search Amazon |
| `github_search.txt` | Search GitHub |
| `reddit_search.txt` | Search Reddit |
| `youtube_search.txt` | Search YouTube |

**See all available tests**: Check the `requirements/` folder for the complete list.

## Advanced Options

### Clear cache before running (for clean test)
```bash
pacts test salesforce_create_contact.txt --clear-cache
```

### Slow motion (see what's happening)
```bash
pacts test salesforce_create_contact.txt --slow-mo 500
```

### Salesforce Session Management (Fully Automatic!)

PACTS automatically manages your Salesforce sessions! No manual steps required.

**What happens when you run a Salesforce test:**

1. **Session check**: PACTS checks if your session is valid (< 2 hours old)
2. **Auto-refresh** (if expired): Browser opens automatically for you to log in
3. **Auto-detection**: PACTS detects when you've successfully logged in
4. **Test continues**: Your test runs automatically with the fresh session

**Example workflow:**
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

### Combine options
```bash
pacts test salesforce_create_contact.txt --clear-cache --slow-mo 500
```

**Note**: All tests run in **headless mode** (browser runs in background). This is the recommended way for automated testing.

## That's It!

No complex commands, no Docker knowledge needed. Just type the test name and PACTS does the rest!

---

**Need help?** Contact your test automation team or see the full [README.md](README.md)
