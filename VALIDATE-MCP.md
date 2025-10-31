# MCP Playground Integration - Validation Runbook

**Dead-Simple Validation Guide** - No new code, just run and confirm.

---

## 0️⃣ Quick Sanity Check

### Verify Environment

```bash
# Confirm flags are loaded
echo $USE_MCP
echo $MCP_PW_SERVER_URL

# Expected output:
# USE_MCP: true (or false)
# MCP_PW_SERVER_URL: http://localhost:8765
```

### MCP Server Health Check

```bash
# MCP health (should return 200/OK JSON)
curl -s -X POST "$MCP_PW_SERVER_URL/health" | head
```

**Expected**: `{"status": "ok"}` or similar

**✅ Proceed only if health returns OK**
**❌ If health fails, skip to Scenario B (fallback validation)**

---

## 1️⃣ Enable Ultra-Visible Logs

Run headed mode with output capture for easy inspection:

```bash
# Headed, slow motion, verbose output
python run_e2e_headed.py 2>&1 | tee out_mcp_on.txt

# Quick view of proof lines
grep -E "(MCP|POMBuilder|ROUTER|Verdict|Generated|Heal Rounds|Steps Executed)" out_mcp_on.txt
```

### What You Should See:

```
MCP discovered selector for 'Username': #user-name (strategy: mcp_testId)
MCP actionable gates for '#user-name': {'unique': True, 'visible': True, ...}
[ROUTER] All steps complete (6/6) -> verdict_rca
Verdict: pass
Steps Executed: 6/6
Heal Rounds: 0
Generated Test Artifact: generated_tests/test_req_shopping_001.py
```

---

## 2️⃣ Scenario A — MCP ON (Headed Mode)

**Goal**: Prove 6/6 steps on SauceDemo without any Excel changes.

### Run Test

```bash
export USE_MCP=true
python run_e2e_headed.py 2>&1 | tee out_mcp_on.txt
```

### Quick Validation

```bash
grep -E "MCP|Verdict|Steps Executed|Generated" out_mcp_on.txt
```

### ✅ Expected Results

| Check | Expected Value |
|-------|---------------|
| **MCP calls visible** | `MCP discovered selector`, `MCP actionable gates`, `MCP reveal` |
| **Verdict** | `pass` |
| **Steps Executed** | `6/6` |
| **Artifact Generated** | `generated_tests/test_req_shopping_001.py` |
| **Browser Visible** | Yes (headed mode) |
| **Cart/Checkout** | Resolved without Excel changes |

### Inspect Generated Artifact

```bash
# View generated test file
cat generated_tests/test_req_shopping_001.py | head -50

# Look for MCP comments (if MCP suggest_locator worked)
grep -i "mcp\|getByRole\|recorder" generated_tests/test_req_shopping_001.py
```

---

## 3️⃣ Scenario B — MCP OFF (Fallback Mode)

**Goal**: Prove graceful fallback when MCP unavailable.

### Disable MCP

```bash
export USE_MCP=false
# OR stop MCP server:
# docker stop mcp-playwright
```

### Run Test

```bash
python run_e2e_headed.py 2>&1 | tee out_mcp_off.txt
```

### Quick Validation

```bash
grep -E "MCP|Verdict|Steps Executed|Generated" out_mcp_off.txt
```

### ✅ Expected Results

| Check | Expected Value |
|-------|---------------|
| **MCP calls** | **None** (all local heuristics) |
| **Verdict** | `pass` or `partial` |
| **Steps Executed** | `4/4` (if no cart CSS) or `6/6` (with `css:.shopping_cart_link`) |
| **Artifact Generated** | Yes |
| **No Crashes** | Process completes cleanly |

**Note**: If Excel lacks `css:.shopping_cart_link` for Cart, expect 4/4 steps (login flow only).

---

## 4️⃣ Scenario C — Healer Proof (Force a Heal)

**Goal**: Verify OracleHealer v2 + MCP reprobe work together.

### Force a Typo

Temporarily edit `specs/saucedemo_test_scripts.xlsx`:
- Change step target from `"Add to cart"` → `"Add to card"` (typo)

### Run Test with MCP

```bash
export USE_MCP=true
python run_e2e_headed.py 2>&1 | tee out_heal.txt
```

### Quick Validation

```bash
grep -E "oracle_healer|Heal Rounds|heal_events|MCP reprobe|Verdict" out_heal.txt
```

### ✅ Expected Results

| Check | Expected Value |
|-------|---------------|
| **OracleHealer invoked** | `[oracle_healer] run` or `ROUTER -> oracle_healer` |
| **Heal Rounds** | `1-3` |
| **MCP reprobe** | `MCP reprobe for 'Add to card'` |
| **Verdict** | `pass` or `partial` (healed successfully) |
| **heal_events** | Array with `success: True` entries |

### Inspect RCA

```bash
# Check for MCP debug probe in RCA
python -c "
import json
with open('out_heal.txt') as f:
    if 'mcp_probe' in f.read():
        print('✅ MCP debug probe attached to RCA')
"
```

### Revert Typo

```bash
# Restore Excel file to original
git restore specs/saucedemo_test_scripts.xlsx
```

---

## 5️⃣ Minimal Acceptance Gate

**All of these MUST be visible in console/files:**

- [ ] **Headed browser opens** (visual confirmation)
- [ ] **MCP calls logged** (Scenario A: `MCP discovered selector`)
- [ ] **Verdict: pass** (at least Scenarios A & B)
- [ ] **Steps Executed: 6/6** (with MCP) or **4/4** (fallback)
- [ ] **Artifact generated** (`generated_tests/test_*.py` exists)
- [ ] **MCP probe on failure** (Scenario C: `rca.mcp_probe` present)
- [ ] **No crashes** (all 3 scenarios complete)

---

## 6️⃣ Triage Checklist (If Tests Fail)

### Health Check Fails

```bash
curl -X POST $MCP_PW_SERVER_URL/health
```

**If not OK**:
- Verify MCP server is running: `docker ps | grep mcp-playwright`
- Check server logs: `docker logs mcp-playwright`
- Verify port 8765 accessible: `netstat -an | grep 8765`

### Flag Not Set

```bash
echo $USE_MCP
```

**If empty or "false"**:
- You're in fallback mode (expected behavior)
- To enable: `export USE_MCP=true`

### URL Mismatch

**Check**: Test uses `https://www.saucedemo.com` (not `http://`)

```bash
grep -i "saucedemo.com" specs/*.xlsx specs/*.json
```

### Excel Target Issues

**Preferred human names**:
- ✅ `Username`, `Password`, `Login`, `Add to cart`, `Checkout`
- ❌ Avoid `#user-name`, `.login-button` (these are selectors, not targets)

**For cart icon without label**:
- **With MCP**: Auto-resolved via `testId` or `role`
- **Without MCP**: Add `css:.shopping_cart_link` to Excel

### Healer Ceiling Hit

```bash
grep "Heal Rounds: [0-9]" out_*.txt
```

**If `Heal Rounds: 3`** and still failing:
- Check logs for failure reason (overlay, visibility, not_unique)
- Verify element exists: manually inspect page in browser
- Check for JavaScript errors blocking element

### Artifact Import Test

```bash
# Verify generated test is valid Python
python -m py_compile generated_tests/test_*.py

# Check for syntax errors
python -m pyflakes generated_tests/test_*.py
```

---

## 7️⃣ One-Liner Smoke Scripts

### MCP Health Smoke Test

Create `mcp_smoke.py`:

```python
import os
import requests

url = os.getenv("MCP_PW_SERVER_URL", "http://localhost:8765").rstrip("/")
try:
    r = requests.post(f"{url}/health", json={}, timeout=2)
    print(f"✅ MCP Health: {r.status_code} - {r.text[:120]}")
except Exception as e:
    print(f"❌ MCP Unreachable: {e}")
```

**Run**:
```bash
python mcp_smoke.py
```

### Artifact Smoke Test

Create `plan_smoke.py`:

```python
import pathlib

artifacts_dir = pathlib.Path("generated_tests")
artifacts = list(artifacts_dir.glob("*.py"))

print(f"📁 Artifacts Directory: {artifacts_dir}")
print(f"📄 Found {len(artifacts)} test file(s):")
for f in artifacts:
    print(f"   - {f.name} ({f.stat().st_size} bytes)")

if artifacts:
    print("✅ Artifacts generated successfully")
else:
    print("❌ No artifacts found")
```

**Run**:
```bash
python plan_smoke.py
```

---

## 8️⃣ All-In-One Validation Script

Create `validate_mcp.sh`:

```bash
#!/bin/bash
set -e

echo "=================================================="
echo "MCP Playwright Integration - Full Validation"
echo "=================================================="
echo ""

# Step 0: Sanity
echo "Step 0: Environment Check"
echo "  USE_MCP: ${USE_MCP:-not set}"
echo "  MCP_PW_SERVER_URL: ${MCP_PW_SERVER_URL:-not set}"
echo ""

# Step 1: Health check
echo "Step 1: MCP Health Check"
if curl -s -X POST "${MCP_PW_SERVER_URL:-http://localhost:8765}/health" > /dev/null 2>&1; then
    echo "  ✅ MCP server responding"
else
    echo "  ⚠️ MCP server not responding (will test fallback)"
fi
echo ""

# Step 2: Scenario A - MCP ON
echo "Step 2: Scenario A - MCP Enabled"
export USE_MCP=true
python run_e2e_headed.py 2>&1 | tee out_mcp_on.txt > /dev/null
echo "  Output saved to: out_mcp_on.txt"
echo "  MCP calls: $(grep -c 'MCP' out_mcp_on.txt || echo 0)"
echo "  Verdict: $(grep 'Verdict:' out_mcp_on.txt | tail -1)"
echo "  Steps: $(grep 'Steps Executed:' out_mcp_on.txt | tail -1)"
echo ""

# Step 3: Scenario B - MCP OFF
echo "Step 3: Scenario B - MCP Disabled (Fallback)"
export USE_MCP=false
python run_e2e_headed.py 2>&1 | tee out_mcp_off.txt > /dev/null
echo "  Output saved to: out_mcp_off.txt"
echo "  MCP calls: $(grep -c 'MCP' out_mcp_off.txt || echo 0) (should be 0)"
echo "  Verdict: $(grep 'Verdict:' out_mcp_off.txt | tail -1)"
echo "  Steps: $(grep 'Steps Executed:' out_mcp_off.txt | tail -1)"
echo ""

# Step 4: Artifacts check
echo "Step 4: Artifacts Check"
python plan_smoke.py
echo ""

echo "=================================================="
echo "✅ Validation Complete"
echo "=================================================="
echo ""
echo "Next Steps:"
echo "  1. Review logs: out_mcp_on.txt, out_mcp_off.txt"
echo "  2. Inspect artifacts: ls generated_tests/"
echo "  3. Run Scenario C (healer) manually if needed"
```

**Run**:
```bash
chmod +x validate_mcp.sh
./validate_mcp.sh
```

---

## 9️⃣ Success Criteria Summary

| Scenario | MCP Enabled | Expected Outcome | Log Proof |
|----------|-------------|------------------|-----------|
| **A: MCP ON** | ✅ Yes | 6/6 steps pass | `MCP discovered selector` |
| **B: Fallback** | ❌ No | 4-6/6 steps pass | No MCP lines |
| **C: Healer** | ✅ Yes | Heal + pass | `MCP reprobe`, `heal_events` |

**All 3 scenarios must complete without crashes.**

---

## 🔟 Quick Reference Commands

```bash
# Enable MCP
export USE_MCP=true

# Disable MCP
export USE_MCP=false

# Health check
curl -X POST http://localhost:8765/health

# Run headed test
python run_e2e_headed.py

# View MCP calls
grep -i "mcp" out_mcp_on.txt

# Check verdict
grep "Verdict:" out_*.txt

# List artifacts
ls -lh generated_tests/
```

---

**Last Updated**: October 31, 2025
**Tested On**: Windows 11 + WSL2, Python 3.11, Playwright 1.40+
