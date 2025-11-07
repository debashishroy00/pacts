# PACTS Quick Start Guide - For Business Users

## Running Tests (Super Simple!)

### Windows
```cmd
pacts test contact
pacts test opportunity
pacts test wikipedia
```

### Mac/Linux
```bash
./pacts test contact
./pacts test opportunity
./pacts test wikipedia
```

## Available Tests

Just use simple names - PACTS finds the right test automatically:

| Simple Name | What It Tests |
|-------------|---------------|
| `contact` | Create a Salesforce Contact |
| `opportunity` | Create a Salesforce Opportunity |
| `account` | Create a Salesforce Account |
| `wikipedia` | Search Wikipedia |
| `amazon` | Search Amazon |
| `github` | Search GitHub |
| `reddit` | Search Reddit |
| `youtube` | Search YouTube |

## Advanced Options

### Clear cache before running (for clean test)
```bash
pacts test contact --clear-cache
```

### Run in visible browser (watch the test)
```bash
pacts test contact --headed
```

### Slow motion (see what's happening)
```bash
pacts test contact --slow-mo 500
```

### Combine options
```bash
pacts test contact --clear-cache --headed --slow-mo 500
```

## That's It!

No complex commands, no Docker knowledge needed. Just type the test name and PACTS does the rest!

---

**Need help?** Contact your test automation team or see the full [README.md](README.md)
