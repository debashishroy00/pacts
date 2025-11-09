PACTS v3.1s — Stealth Mode + Data-Driven Execution + Friendly CLI

Author: DR
Date: Nov 2025
Audience: Core Contributors (CC)
Objective: Make PACTS universal, robust, and user-friendly for public websites and SPAs without platform-specific logic.

🧩 Phase 1 — Stealth Mode (Universal Stability)

Goal: Ensure headless browsers behave like real users, eliminating blocks from GitHub, marketing sites, and SPAs.

Deliverables

launch_stealth.py module (drop-in for Playwright launcher)

Auto-injected stealth JavaScript patch:

Hides navigator.webdriver

Normalizes languages/platform

Fakes WebGL vendor/renderer

Grants common permissions

Persistent context per run (runs/userdata/profile_<id>)

Config flags:

STEALTH=true
PERSISTENT_PROFILES=true
TZ=America/New_York
LOCALE=en-US


Basic telemetry fields:

stealth_on

blocked_headless

first_block_sig

Testing

GitHub login (3 steps)

Static site (3 steps)

Generic React SPA (3 steps)

Success Criteria:

All pass

<10% show blocked_headless=1

Step time < baseline ×1.2

🧭 Phase 2 — Friendly CLI (Natural Commands)

Goal: Simplify user experience — “type less, do more.”

CLI Command
pacts test <file-or-folder> [options]

Features

Auto-discover tests/ folder if no path given.

Supports globbing:

pacts test tests/github_*.yaml
pacts test tests/smoke/


Optional args:

--browser chromium|firefox
--retries N
--headless true|false
--parallel N


Pretty console output:

✅ Pass / ❌ Fail per file

Progress bar with elapsed time

CI-ready exit codes:

0 if all pass

1 if any fail

Implementation

cli_runner.py: new entrypoint

discover_tests(): auto folder/glob

run_test_file(path): run + render summary

Integrate with stealth launcher

Example Usage
pacts test tests/github_login.yaml
pacts test tests/
pacts test tests/**/*.yaml --parallel=2

📊 Phase 3 — Data-Driven Execution

Goal: Allow a single test definition to run multiple times with variable data.

Syntax

Use ${var} placeholders inside test YAML.

Example:

name: github_login
vars:
  base_url: https://github.com
steps:
  - go: "${base_url}/login"
  - fill: { selector: "input[name='login']", value: "${username}" }
  - fill: { selector: "input[name='password']", value: "${password}" }
  - click: { role: button, name: "Sign in" }
  - assert_text: { contains: "${assert_after|Signed in}" }

Dataset Options

CSV

JSONL

YAML (array of objects)

Example CSV:

username,password,assert_after
user1@example.com,secret1,Signed in
user2@example.com,secret2,Verify your email

CLI Usage
pacts test tests/github_login.yaml --data tests/github_users.csv --parallel 2

Advanced Flags
--data-format csv|jsonl|yaml
--max-rows N
--vars key=value,key2=value2
--render-only
--data-select id=value

Variable Precedence

Step default → ${var|default}

Test vars: block

CLI --vars

Dataset row (highest)

Secrets

Use @env:VAR to read environment variables in test data.
Example:

username,@env:GITHUB_USER
password,@env:GITHUB_PASS

Reporting

Each data row = independent run
Folder: runs/<testname>/<row-id>/…

JUnit XML shows one testcase per row

CLI summary aggregates:

github_login.yaml [2/2 passed]
Total rows: 2  Duration: 15.4s

Implementation

dataset_loader.py: detect format → yield dicts

templating.py: replace ${var} / ${var|default}

Extend executor to loop rows + render per dataset

CLI merges dataset + flags + defaults

Add dataset, row_id, vars_hash to telemetry

🚀 Phase 4 — QA Validation

Goal: Confirm full stack stability before wider use.

Test Matrix
Category	Examples	Expected
Static	github.com, docs.python.org	✅
SPA	demo.reactjs.org, playground.angular.io	✅
Auth	login flows (GitHub, WordPress)	✅
Multi-Data	CSV login dataset	✅
Metrics

Pass rate ≥ 95 %

Average step duration < 2 s

Retry rate < 5 %

blocked_headless < 10 %

🧾 Deliverables Summary
Phase	Module / Change	Description
1	launch_stealth.py	Stealth launcher with JS patch
1	.env updates	Stealth flags
2	cli_runner.py	Friendly CLI pacts test
3	dataset_loader.py, templating.py	Data-driven test support
3	executor.py updates	Per-row runs, telemetry
4	tests/	Smoke suites + datasets
✅ Success Criteria

Run any public site test via

pacts test tests/


Same file runs multiple data sets via --data

≥ 95 % pass on GitHub + common SPAs

All headless (no Xvfb, no headed)

Zero platform-specific hacks

Next Step for CC:
Start with Phase 1 (Stealth Mode) → test on GitHub and React demo → once verified, move to Phase 2 (CLI) and Phase 3 (Data-Driven).