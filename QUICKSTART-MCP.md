# MCP Playwright Integration - Quick Start

**Dead-Simple 3-Minute Validation**

---

## 🚀 Ultra-Fast Validation (3 commands)

```bash
# 1. Check MCP server health
python mcp_smoke.py

# 2. Run full validation (both scenarios)
python validate_mcp.py

# 3. Check generated artifacts
python plan_smoke.py
```

**That's it!** ✅

---

## 📋 What Gets Validated

| Script | What It Checks | Output |
|--------|---------------|---------|
| `mcp_smoke.py` | MCP server health | ✅ or ❌ with troubleshooting |
| `validate_mcp.py` | Full integration (A+B scenarios) | `out_mcp_on.txt`, `out_mcp_off.txt` |
| `plan_smoke.py` | Generated test artifacts | List of `.py` files + validation |

---

## 🎯 Expected Results

### Scenario A (MCP ON)
- ✅ Browser opens (headed mode)
- ✅ Logs show `MCP discovered selector`
- ✅ Verdict: `pass`
- ✅ Steps: `6/6` executed
- ✅ Artifact: `generated_tests/test_*.py`

### Scenario B (MCP OFF - Fallback)
- ✅ Browser opens (headed mode)
- ✅ No MCP calls (local heuristics)
- ✅ Verdict: `pass` or `partial`
- ✅ Steps: `4-6/6` executed
- ✅ No crashes

---

## 🔧 Quick Setup (If MCP Server Not Running)

```bash
# Start MCP Playwright server (Docker)
docker run -d -p 8765:8765 --name mcp-playwright your/mcp-playwright:latest

# Verify it's running
docker ps | grep mcp-playwright

# Health check
curl -X POST http://localhost:8765/health
```

---

## 📖 Detailed Documentation

For complete validation runbook with all scenarios (including healing tests):

→ See **[VALIDATE-MCP.md](VALIDATE-MCP.md)**

For MCP integration architecture and configuration:

→ See **[docs/MCP-PW-INTEGRATION.md](docs/MCP-PW-INTEGRATION.md)**

---

## 🆘 Troubleshooting (30-Second Fix)

### MCP Server Not Responding

```bash
# Check if server is running
docker ps | grep mcp-playwright

# If not, start it
docker run -d -p 8765:8765 mcp-playwright

# Test again
python mcp_smoke.py
```

### Tests Fail

```bash
# Check logs
cat out_mcp_on.txt | grep -E "ERROR|FAIL|Exception"

# Verify environment
echo $USE_MCP
echo $MCP_PW_SERVER_URL

# Re-run with fallback (should always work)
USE_MCP=false python run_e2e_headed.py
```

### No Artifacts Generated

```bash
# Check if test completed
tail -20 out_mcp_off.txt

# Verify directory exists
ls -la generated_tests/

# Force regeneration
python run_e2e_headed.py
python plan_smoke.py
```

---

## 📊 Validation Checklist

Run `validate_mcp.py` and verify:

- [ ] **Environment**: `USE_MCP` and `MCP_PW_SERVER_URL` set
- [ ] **Health**: MCP server responds (or skip Scenario A)
- [ ] **Scenario A**: MCP calls visible, 6/6 steps pass
- [ ] **Scenario B**: No MCP calls, 4-6/6 steps pass
- [ ] **Artifacts**: Test files generated and valid Python

**All green?** → Ready to merge! 🎉

---

## 🏁 One-Liner for CI/CD

```bash
# Run all validations and exit with proper code
python validate_mcp.py && echo "✅ MCP Integration Validated"
```

**Exit code 0** = All validations passed
**Exit code 1** = Some validations failed (check logs)

---

**Time to Validate**: ~3 minutes (including headed browser tests)
**Last Updated**: October 31, 2025
