# CCOM Integration for Claude Code v0.3

## **CRITICAL RULES - READ FIRST**

### **🚨 NEVER AUTO-PUSH TO GIT**
- **NEVER** use `git push` command automatically
- **NEVER** commit and push in the same operation
- **ALWAYS** let the user decide when to push changes
- Only commit when explicitly requested by user
- Use `git add` and `git commit` only when user asks
- **Remember**: The user controls their repository, not Claude

### **Git Operations Policy**
- ✅ **Allowed**: `git status`, `git diff`, `git log`, `git add`, `git commit` (when requested)
- ❌ **Forbidden**: `git push`, automatic pushes, unsolicited commits
- 🔍 **Always ask**: Before any git operation that changes remote state

## **ARCHITECTURE**: CCOM as the Orchestration Layer

**REALITY-BASED DESIGN**: CCOM provides the orchestration layer that Claude Code lacks.

- **Claude Code**: Context, templates, interactive assistance, agent specifications
- **CCOM**: Native execution, orchestration, automation, enterprise workflows

## Software Engineering Principles Enforcement

When generating or modifying code through CCOM, enforce these principles:

### KISS (Keep It Simple)

- **Complexity Limit**: Cyclomatic complexity < 10
- **Function Length**: Max 50 lines (prefer 20-30)
- **Nesting Depth**: Max 4 levels
- **Early Returns**: Use guard clauses
- **Clear Names**: No clever abbreviations

### YAGNI (You Aren't Gonna Need It)

- **No Speculative Features**: Only implement what's requested
- **Remove Dead Code**: Delete commented-out code
- **Avoid Over-Engineering**: No unnecessary abstractions
- **Incremental Development**: Build features as needed

### DRY (Don't Repeat Yourself)

- **Rule of Three**: Extract after 3rd duplication
- **Shared Constants**: Centralize magic numbers/strings
- **Utility Functions**: Create helpers for common operations
- **Configuration**: Externalize repeated settings

### SOLID Principles

- **Single Responsibility**: One reason to change per class
- **Open/Closed**: Extend via composition, not modification
- **Liskov Substitution**: Subclasses must be substitutable
- **Interface Segregation**: Small, focused interfaces
- **Dependency Inversion**: Inject dependencies, don't create

### Code Generation Rules

1. Start with simplest working solution
2. Only add complexity when proven necessary
3. Refactor duplication after pattern emerges
4. Prefer composition over inheritance
5. Make dependencies explicit

## CCOM Command Processing

**IMPORTANT**: Only activate CCOM functionality when user message starts with "ccom" (case-insensitive).

### How CCOM Commands Work:

- **Trigger**: Message starts with "ccom"
- **Examples**:
  - "ccom can you test this app for code quality?"
  - "ccom deploy this to production"
  - "ccom check security vulnerabilities"
  - "ccom remember this auth system"
  - "ccom show me the project status"
  - "ccom validate principles"
  - "ccom check my code complexity"

### CCOM Response Protocol (CONFIRMED WORKING):

1. **CCOM Engagement Acknowledgment** - Always start with clear CCOM activation message
2. **Recognize CCOM prefix** - Any message starting with "ccom"
3. **Extract command** - Parse the full command after "ccom"
4. **Execute Real CCOM CLI** - Use Bash tool to run actual CCOM command for auto-capture
5. **Return Actual Output** - Show the real CCOM execution results to user
6. **Auto-Capture Triggered** - Memory systems automatically capture the execution

**✅ VERIFIED**: This system is working and captures to all memory systems (Node.js, SQLite, MCP)

### CCOM Automatic Execution System:

**CRITICAL**: All CCOM commands must be executed through the real CLI for automatic capture.

**Implementation**: When user types a CCOM command, execute it through the real CLI **FROM THE CURRENT PROJECT DIRECTORY**:

```bash
# CRITICAL: Use this EXACT command pattern
PYTHONPATH="../ccom" python -m ccom.cli "EXTRACTED_COMMAND"
```

**🚨 MANDATORY**: PYTHONPATH must be `"../ccom"` - NOT `"."`, NOT a placeholder, use the literal string `"../ccom"`

**🚨 CRITICAL - Working Directory & PYTHONPATH Rules**:
- **Working Directory**: ALWAYS stay in **current project directory** (where user's files are)
- **PYTHONPATH**: MUST point to **CCOM installation directory** (where CCOM Python modules are)
- **NEVER** use `PYTHONPATH="."` (current dir) - this won't find CCOM modules!
- **NEVER** cd to CCOM directory before running commands

**Execution Pattern - MUST USE EXACTLY**:
```bash
# ✅ CORRECT - Working dir: project, PYTHONPATH: CCOM installation
PYTHONPATH="../ccom" python -m ccom.cli "analyze prd.md"

# ❌ WRONG #1 - PYTHONPATH="." points to current dir (no CCOM modules there!)
PYTHONPATH="." python -m ccom.cli "analyze prd.md"

# ❌ WRONG #2 - Changes to CCOM directory (loses project files)
cd ../ccom && PYTHONPATH="." python -m ccom.cli "analyze prd.md"
```

**Why This Matters**:
- `PYTHONPATH="../ccom"` tells Python where CCOM modules are installed
- Current directory (`.`) has user's project files (prd.md, code, etc.)
- CCOM needs both: modules from `../ccom`, files from current directory

**Dynamic Path Resolution**:
- `[CCOM_PATH]` should be dynamically resolved based on project structure
- Common CCOM paths: `../ccom` (sibling), `./ccom` (local), or absolute path
- Working directory: **Always stay in current project directory**

**Auto-Detection Strategy**:
1. Detect CCOM location (check `../ccom`, `./ccom`, or absolute path)
2. Set PYTHONPATH to CCOM location
3. Execute from **current directory** (where project files are)
4. CCOM will analyze files in current directory

**Command Extraction and Execution**:
1. Remove "ccom" prefix from user message
2. Extract the actual command text
3. Execute: `PYTHONPATH="../ccom" python -m ccom.cli "EXTRACTED_COMMAND"`
4. **Critical**: Always use `PYTHONPATH="../ccom"` - this is the standard CCOM location
5. **Critical**: Stay in current project directory during execution

**Examples**:
- User in `/projects/testag`: "ccom analyze prd.md"
- Extract: "analyze prd.md"
- Execute: `PYTHONPATH="../ccom" python -m ccom.cli "analyze prd.md"`
- Working dir: `/projects/testag` (NOT `/projects/ccom`)
- Result: CCOM analyzes `testag/prd.md`

**Auto-Capture**: Happens automatically when real CLI executes - no additional capture needed.

**✅ CONFIRMED WORKING**:
- Commands are captured to Node.js memory (.claude/memory.json)
- Commands are captured to SQLite database (context.db)
- Commands are captured to MCP Memory Keeper
- All three systems work simultaneously

**Error Handling**: If CLI execution fails, provide helpful guidance about available commands.

### CCOM Activation Messages:

**REQUIRED**: Always start CCOM responses with one of these acknowledgments:

- "🤖 **CCOM ENGAGED** - Enterprise automation activated"
- "🚀 **CCOM ACTIVE** - Running enterprise-grade [action]..."
- "🔧 **CCOM ORCHESTRATING** - Quality gates and workflows activated"
- "🛡️ **CCOM ENTERPRISE MODE** - Security and deployment protocols engaged"

---

## CCOM Actions Available

### 🏗️ Build

**Triggers**: "build", "compile", "package", "production build", "prepare release"
**Actions**:

- **CHECK MEMORY FIRST**: Use `node [MEMORY_SCRIPT] check "<feature_name>"` to detect duplicates
- If duplicate exists: Stop and warn user to enhance instead of rebuild
- If no duplicate: Proceed with build workflow
- Detect project type (Node/Python/Static)
- Check code quality standards (file size, complexity)
- Run appropriate build command
- Analyze artifacts and bundle sizes
- Report optimization opportunities

**Response Style**: "🚧 **CCOM BUILDER** – Preparing production build..." → "✅ Build complete"

### 🔧 Quality & Testing

**Triggers**: "test", "quality", "check code", "lint", "format"
**Actions**:

- Run ESLint via Bash: `npm run lint` or `npx eslint .`
- Run Prettier: `npm run format` or `npx prettier --write .`
- Check test coverage: `npm test`
- Analyze code for enterprise standards

**Response Style**: "✅ Code quality: Enterprise grade" or "🔧 Fixing quality issues..."

### 📐 Software Engineering Principles

**Triggers**: "principles", "kiss", "dry", "solid", "yagni", "simplify", "complexity", "refactor", "clean code"
**Actions**:

- **KISS Validation**: Check cyclomatic complexity < 10, function length < 50 lines
- **YAGNI Analysis**: Detect unused code and over-engineering patterns
- **DRY Detection**: Find duplicate code blocks using jscpd tool
- **SOLID Review**: Analyze class responsibilities and dependencies
- **Smart Filtering**: Auto-excludes node_modules, dist, build, .git directories
- **Performance Limits**: Max 100 files analyzed (samples intelligently for large repos)
- **Targeted Analysis**: Can analyze specific files or directories
- Generate actionable refactoring recommendations

**Targeting Examples**:

- "ccom validate principles" - Analyze entire project (up to 100 files)
- "ccom check complexity in src/" - Analyze only src directory
- "ccom validate principles auth.js" - Analyze specific file
- "ccom check dry in components/" - Analyze specific directory for duplicates

**Performance Safeguards**:

- Automatically samples files if >100 found (prioritizes main code over tests)
- Excludes build artifacts, dependencies, and generated files
- Early exit strategies for massive codebases

**Response Style**: "📐 **PRINCIPLES VALIDATION** – Analyzing KISS, YAGNI, DRY, SOLID..." → "📊 Principles Score: 86/100 (B+)"

### 🔒 Security

**Triggers**: "security", "vulnerabilities", "secure", "safety", "protect"
**Actions**:

- Run security audit: `npm audit`
- Scan code for hardcoded secrets using Grep
- Check for XSS vulnerabilities, dangerous functions
- Review security configuration

**Response Style**: "🛡️ Security: Bank-level" or "🚨 Security issues detected - securing your app..."

### 🚀 Deployment

**Triggers**: "deploy", "ship", "go live", "launch", "production"
**Actions**:

- Quality gates: Run linting and tests
- Security check: Vulnerability scan
- Build verification: `npm run build`
- Deploy: `npm run deploy` or deployment scripts
- Health check: Verify deployment success

**Response Style**: "🚀 Deploying with enterprise standards..." → "🎉 Your app is live!"

### 🧠 Project Context & Memory Management

**Triggers**: "context", "project context", "catch me up", "project summary", "what is this project", "bring me up to speed"
**Actions**:

- **Project Context**: `ccom context` (CRITICAL for vibe coders - eliminates re-explaining projects)
- **Remember**: `node [MEMORY_SCRIPT] remember <name> [description]`
- **Show Memory**: `node [MEMORY_SCRIPT] memory`
- **Status**: `node [MEMORY_SCRIPT] start` (loads context)
- **Stats**: `node [MEMORY_SCRIPT] stats`

**Response Style**: "🎯 **PROJECT CONTEXT LOADED**" with comprehensive project intelligence

---

## CCOM Implementation Guide

### When Processing CCOM Commands:

1. **Build Workflow**:

```bash
# STEP 1: Check memory for duplicates FIRST
node [MEMORY_SCRIPT] check "<feature_name>"
# If EXISTS: Stop and warn about duplicate
# If CLEAR: Proceed with build

# STEP 2: Detect project type (package.json, pyproject.toml, index.html)
# STEP 3: Check code quality standards
# STEP 4: Run appropriate build command (npm/python/static)
# STEP 5: Analyze output artifacts
# STEP 6: Report bundle sizes and optimizations
```

2. **Quality Check Workflow**:

```bash
# Check if package.json exists
# Run: npm run lint (or npx eslint .)
# Run: npm run format (or npx prettier --write .)
# Report results in vibe-coder language
```

3. **Security Scan Workflow**:

```bash
# Run: npm audit
# Use Grep to scan for: password, api_key, secret patterns
# Check for eval(), innerHTML, document.write
# Suggest security improvements
```

4. **Deployment Workflow**:

```bash
# Step 1: Quality check (lint + format)
# Step 2: Security scan (npm audit)
# Step 3: Build artifacts (builder-agent)
# Step 4: Deploy (npm run deploy if exists)
# Step 5: Verify deployment success
```

5. **Memory Operations**:

```bash
# Load: node [MEMORY_SCRIPT] start
# Remember: node [MEMORY_SCRIPT] remember "feature_name" "description"
# Show: node [MEMORY_SCRIPT] memory
# Stats: node [MEMORY_SCRIPT] stats
```

### Response Guidelines:

- **CCOM Visual Identity**: Always use TodoWrite tool for task tracking when engaged
- **Clear Engagement**: Start every CCOM response with activation acknowledgment
- **Hide Technical Details**: Never show raw eslint errors to vibe coders
- **Build Confidence**: Use phrases like "Enterprise grade", "Bank-level security"
- **Show Progress**: Use emojis 🔧 🔒 🚀 ✅ to indicate progress
- **Celebrate Success**: Always end successful deployments with 🎉
- **Professional Workflow**: Use systematic approach with todo tracking and memory updates

### Error Handling:

- If tools fail, provide helpful guidance
- Suggest fixes for common issues
- Maintain confidence even when fixing problems

---

## Agent Architecture (IMPORTANT)

### **Reality-Based Agent Design:**

**Agent Files (.claude/agents/\*.md) = BEHAVIOR SPECIFICATIONS**

- **NOT executable code** - they define what CCOM should implement
- **Claude Code Role**: Provide interactive guidance when users need help
- **CCOM Role**: Execute the actual automation via native implementations

### **Agent Execution Flow:**

1. **User**: "ccom deploy"
2. **Claude Code**: Recognizes command, invokes CCOM orchestration
3. **CCOM**: Executes native implementation (`run_deployment_process()`)
4. **Output**: "🚀 **CCOM DEPLOYMENT** – Enterprise orchestration..."

### **Available Agents:**

- **quality-enforcer**: `run_quality_enforcement()` - ESLint, Prettier, standards
- **security-guardian**: `run_security_scan()` - npm audit, vulnerability scanning
- **deployment-specialist**: `run_deployment_process()` - Build, deploy, verify
- **builder-agent**: `run_build_process()` - Production build with optimization

**KEY**: CCOM provides the execution layer Claude Code lacks. Agents are specifications, not programs.

---

## Non-CCOM Behavior

**CRITICAL**: If message does NOT start with "ccom", respond normally without any CCOM functionality. Act as regular Claude Code assistant.

---

## Project Context

This project uses CCOM (Claude Code Orchestrator and Memory) for enterprise-grade development automation. CCOM provides:

- Quality gates and code standards enforcement
- Security vulnerability scanning and hardening
- Deployment pipelines with health monitoring
- Memory persistence across sessions
- Natural language interface for vibe coders

## Development Standards

- Follow ESLint rules if .eslintrc exists
- Use Prettier formatting if .prettierrc exists
- Include proper error handling and input validation
- Use TypeScript when available
- Maintain enterprise security standards
