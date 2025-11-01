# HITL (Human-in-the-Loop) Signal Directory

This directory is used for non-TTY communication between the test runner and human operators.

## Usage:

### Method 1: Environment Variable
```bash
export PACTS_2FA_CODE=123456
python -m backend.cli.main test --req salesforce_login_hitl --headed
```

### Method 2: File with Code  
```bash
echo "123456" > hitl/2fa_code.txt
```

### Method 3: Continue Signal (manual completion in browser)
```bash
touch hitl/continue.ok
```

The test runner will poll this directory for signals and resume when one is detected.

