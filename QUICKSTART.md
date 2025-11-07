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

### Combine options
```bash
pacts test salesforce_create_contact.txt --clear-cache --slow-mo 500
```

**Note**: All tests run in **headless mode** (browser runs in background). This is the recommended way for automated testing.

## That's It!

No complex commands, no Docker knowledge needed. Just type the test name and PACTS does the rest!

---

**Need help?** Contact your test automation team or see the full [README.md](README.md)
