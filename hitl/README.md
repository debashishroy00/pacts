# PACTS HITL (Human-in-the-Loop) Guide

## Overview

PACTS HITL enables manual intervention during automated tests for operations that require human input (2FA, CAPTCHA, etc.). This folder contains tools and automation state to make HITL as frictionless as possible.

## Quick Start - FASTEST Methods

When a test pauses for HITL, use ONE of these methods:

### ⚡ Method 1: Double-Click Script (Recommended)
1. Complete the manual action in browser (e.g., enter 2FA code, click Verify)
2. Double-click **`pacts_continue.ps1`** in this folder
3. Automation resumes immediately!

### ⚡ Method 2: Keyboard Hotkey (Advanced)
1. Install AutoHotkey v2 from https://www.autohotkey.com/
2. Right-click **`pacts_hotkey.ahk`** → Run Script
3. When HITL pauses: Press **Ctrl+Alt+C**
4. Automation resumes instantly!

### Method 3: Manual File Creation
```bash
touch hitl/continue.ok
```

### Method 4: Environment Variable
```bash
export PACTS_2FA_CODE=123456
```

### Method 5: File with Code
```bash
echo "123456" > hitl/2fa_code.txt
```

## Session Reuse - Skip 2FA After First Run!

**PACTS automatically saves your Salesforce session after successful 2FA**

### First Run (With 2FA)
```bash
python -m backend.cli.main test --req salesforce_opportunity_hitl --headed

# When HITL pauses:
# 1. Enter 2FA code in browser
# 2. Click Verify
# 3. Wait for homepage load
# 4. Double-click pacts_continue.ps1

# ✅ Session saved to hitl/salesforce_auth.json
```

### Subsequent Runs (No 2FA!)
```bash
# Session automatically restored - skips login entirely!
python -m backend.cli.main test --req salesforce_opportunity_hitl --headed

# No HITL pause - goes straight to test execution 🎉
```

**Session lasts ~24 hours** (Salesforce timeout). Delete `salesforce_auth.json` to force fresh login.

## Performance Tips

### Remove Slow-Mo (3x Faster)
```bash
# Before (slow):
python -m backend.cli.main test --req salesforce_opportunity_hitl --headed --slow-mo 800

# After (fast):
python -m backend.cli.main test --req salesforce_opportunity_hitl --headed
```

All critical waits are explicit - slow-mo is unnecessary except for debugging.

## Files in This Folder

| File | Purpose | Auto-Generated? |
|------|---------|-----------------|
| `pacts_continue.ps1` | Double-click to resume HITL | No (provided) |
| `pacts_hotkey.ahk` | Ctrl+Alt+C hotkey for resume | No (provided) |
| `salesforce_auth.json` | Saved Salesforce session | Yes (after 2FA) |
| `continue.ok` | Signal file | Yes (temporary) |
| `2fa_code.txt` | Optional 2FA code | No (manual) |

**Security Note**: Never commit `salesforce_auth.json` to Git (already in `.gitignore`)

## Troubleshooting

### Session Expired
**Symptom**: Test fails with "Not logged in" error
**Solution**: `rm hitl/salesforce_auth.json` and re-run test

### Hotkey Not Working
**Symptom**: Ctrl+Alt+C does nothing
**Solution**: Right-click `pacts_hotkey.ahk` → Run Script (check system tray icon)

### HITL Timeout
**Symptom**: "Timeout reached (900s), continuing anyway..."
**Solution**: Complete action within 15 minutes, or use `pacts_continue.ps1` immediately

### Storage State Not Saving
**Symptom**: 2FA required every run
**Solution**:
1. Check `hitl/` folder is writable
2. Ensure HITL completes without errors
3. Verify `salesforce_auth.json` is created after 2FA

## Technical Details

### How Session Reuse Works
1. After successful HITL (2FA), PACTS saves cookies/localStorage to `salesforce_auth.json`
2. Next run loads this file before browser starts
3. Salesforce recognizes the session - no re-auth required
4. Works until Salesforce expires the session (~24 hours)

### Code Integration
- **Save**: `backend/graph/build_graph.py:233` (after HITL)
- **Load**: `backend/runtime/browser_manager.py:25` (browser init)
- **API**: `backend/runtime/browser_client.py:92` (Playwright storageState)

## Best Practices

1. **Morning Routine**: Run one test with 2FA, rest of day skips login
2. **Hotkey Setup**: Install AutoHotkey once, save 5-10 seconds per HITL
3. **No Slow-Mo**: Only use `--slow-mo` for debugging, never production
4. **Batch Tests**: Group Salesforce tests to maximize session reuse
5. **Delete Auth**: Clear `salesforce_auth.json` if switching test users

