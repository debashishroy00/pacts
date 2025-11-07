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

### Salesforce Session Management

PACTS automatically checks if your Salesforce session is valid (less than 2 hours old) before running tests.

**If session is expired**, you'll see:
```
[AUTH] WARNING: Salesforce session missing or expired (>2 hours old)
[AUTH] Please run: python scripts/session_capture_sf.py
[AUTH] Then re-run your test
```

**To refresh your session**:
```bash
python scripts/session_capture_sf.py
```

This will open a browser for you to log in to Salesforce (username + password + 2FA). After logging in, create a file called `hitl/session_done.txt` (just type "done" into the file), and your session will be saved for the next 2 hours.

### Combine options
```bash
pacts test salesforce_create_contact.txt --clear-cache --slow-mo 500
```

**Note**: All tests run in **headless mode** (browser runs in background). This is the recommended way for automated testing.

## That's It!

No complex commands, no Docker knowledge needed. Just type the test name and PACTS does the rest!

---

**Need help?** Contact your test automation team or see the full [README.md](README.md)
