# PACTS 5-Agent Technical Architecture

**Version**: 2.0  
**Date**: October 28, 2025  
**Status**: CORRECTED - 5 Agents Not 3  
**Purpose**: Complete technical blueprint for 5-agent PACTS system

---

## CRITICAL CORRECTION

**PACTS uses 5 agents, not 3:**

1. **Planner Agent** - Test Discovery & Flow Control
2. **POMBuilder Agent** - Multi-Strategy Locator Discovery  
3. **Generator Agent** - Code Synthesis
4. **Executor Agent** - Test Execution & Reporting
5. **OracleHealer Agent** - Autonomous Test Repair

**Agent Pipeline**: Planner → POMBuilder → Generator → Executor → OracleHealer

---

## 1. System Architecture Overview

### 1.1 Five-Layer Architecture with 5-Agent Orchestration

```
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 1: INPUT LAYER                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Excel Requirements Registry (External Ground Truth)     │ │
│  │ - Test scenarios, expected outcomes, business rules     │ │
│  │ - NOT code-derived (prevents circular dependency)       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│        LAYER 2: LANGGRAPH ORCHESTRATION (5 AGENTS)           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         5-Agent State Machine Pipeline                  │ │
│  │                                                           │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐             │ │
│  │  │ Planner  │→ │ POMBuilder│→ │Generator │             │ │
│  │  │  Agent   │  │   Agent   │  │  Agent   │             │ │
│  │  └──────────┘  └───────────┘  └──────────┘             │ │
│  │                                      ↓                    │ │
│  │                   ┌─────────────────────┐                │ │
│  │                   │    Executor         │                │ │
│  │                   │     Agent           │                │ │
│  │                   └─────────────────────┘                │ │
│  │                            ↓                              │ │
│  │                   ┌─────────────────────┐                │ │
│  │                   │  OracleHealer       │                │ │
│  │                   │     Agent           │                │ │
│  │                   └─────────────────────┘                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  LangGraph 1.0: Durable state with PostgreSQL persistence   │
│  Human-in-Loop: Interrupt gates for approval workflows      │
│  Multi-Session: Resume from any checkpoint                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         LAYER 3: RUNTIME & POLICY LAYER (MCP + PW)          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Universal Web Adapter (UWA)                             │ │
│  │ - Policy-driven configuration (JSON files)              │ │
│  │ - Site-agnostic testing logic                           │ │
│  │ - 5-10 lines config per new site                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 5-Point Actionability Gate                              │ │
│  │ 1. Unique    2. Visible    3. Enabled                   │ │
│  │ 4. Stable    5. Interactable                            │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│            LAYER 4: MEMORY & STATE LAYER                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Episodic    │  │   Working    │  │   Procedural     │  │
│  │   Memory     │  │   Memory     │  │     Memory       │  │
│  │ (PostgreSQL) │  │  (Redis 7+)  │  │  (Strategies)    │  │
│  │              │  │              │  │                  │  │
│  │ Last 100     │  │ Session      │  │ Healing tactics  │  │
│  │ test runs    │  │ caching      │  │ w/ success rates │  │
│  │ per req      │  │ 1hr TTL      │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│      LAYER 5: OBSERVABILITY & DEEP PROBES                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ LangSmith Integration (Full Trace Visibility)           │ │
│  │ - Every agent execution traced                          │ │
│  │ - Strategy selection rationale                          │ │
│  │ - Confidence scores & success/failure patterns          │ │
│  │ - Token costs & performance metrics                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Five Agent Specifications

### 2.1 Agent 1: Planner

**Purpose**: Test Discovery & Flow Control

**Responsibilities**:
- Read Excel requirements
- Query episodic memory for historical patterns
- Generate comprehensive plan.json
- Orchestrate LangGraph state machine
- Handle errors and workflow resumption

**Interface**:
```typescript
interface PlannerAgent {
  execute(state: PACSState): Promise<PACSState>;
  
  // Core methods
  readRequirements(excelPath: string): Promise<TestScenario[]>;
  queryEpisodicMemory(scenario: string): Promise<HistoricalPattern[]>;
  generatePlan(): Promise<TestPlan>;
  selectPolicies(): Promise<PolicyConfig[]>;
  defineRetryStrategies(): Promise<RetryStrategy[]>;
}

interface TestPlan {
  scenarios: TestScenario[];      // What to test
  dataBindings: DataBinding[];    // Test data
  policies: PolicyConfig[];       // Site-specific rules
  retryStrategies: RetryStrategy[]; // Error handling
  workflowConfig: WorkflowConfig; // State machine config
}
```

**Outputs**:
- `plan.json` - Comprehensive test plan
- Updated state with workflow configuration

---

### 2.2 Agent 2: POMBuilder

**Purpose**: Multi-Strategy Locator Discovery

**Responsibilities**:
- Analyze page structure (Shadow DOM, iframes, dynamic IDs)
- Select optimal discovery strategies
- Validate through 5-Point Actionability Gate
- Build fallback chains with confidence scores
- Output form.json with verified selectors

**Interface**:
```typescript
interface POMBuilderAgent {
  execute(state: PACSState): Promise<PACSState>;
  
  // Core methods
  analyzePageStructure(): Promise<PageAnalysis>;
  detectShadowDOM(): Promise<ShadowDOMInfo[]>;
  detectIframes(): Promise<IframeInfo[]>;
  detectDynamicIds(): Promise<DynamicIdPattern[]>;
  
  // Strategy selection
  selectDiscoveryStrategies(): Promise<DiscoveryStrategy[]>;
  // Available: Semantic, Shadow DOM, Iframe, Pattern, Vision
  
  // Verification
  validateActionability(element: UIElement): Promise<ActionabilityResult>;
  // 5 gates: unique, visible, enabled, stable, interactable
  
  // Fallback chains
  buildFallbackChains(): Promise<FallbackChain[]>;
  assignConfidenceScores(): Promise<void>;
  
  // Output
  generateFormJSON(): Promise<FormDefinition>;
}

interface DiscoveryStrategy {
  type: 'semantic' | 'shadow-dom' | 'iframe' | 'pattern' | 'vision';
  priority: number;
  confidence: number;
  rationale: string;
}

interface FallbackChain {
  elementId: string;
  primary: string;           // Best selector
  alternatives: string[];    // Fallback selectors
  confidenceScores: number[]; // Confidence per selector
  strategy: string;          // Which strategy found it
}

interface FormDefinition {
  pageUrl: string;
  elements: VerifiedElement[];
  fallbackChains: FallbackChain[];
  shadowDomPaths: ShadowDOMInfo[];
  iframePaths: IframeInfo[];
  metadata: {
    totalElements: number;
    verifiedElements: number;
    discoveryStrategiesUsed: string[];
    buildTimestamp: number;
  };
}
```

**Outputs**:
- `form.json` - Verified element definitions with fallback chains
- Updated state with page object model

---

### 2.3 Agent 3: Generator

**Purpose**: Code Synthesis

**Responsibilities**:
- Take plan.json and form.json as inputs
- Generate production-ready Playwright Python tests
- Use verified selectors from POMBuilder (no guessing!)
- Create test.py with async/await patterns
- Generate fixtures.json for reusable components
- Create data loaders
- Follow modern Python standards with type hints

**Interface**:
```typescript
interface GeneratorAgent {
  execute(state: PACSState): Promise<PACSState>;
  
  // Core methods
  loadPlanJSON(path: string): Promise<TestPlan>;
  loadFormJSON(path: string): Promise<FormDefinition>;
  
  // Code generation
  generatePythonTest(): Promise<string>;
  createAsyncAwaitPatterns(): Promise<void>;
  applyTypeHints(): Promise<void>;
  
  // Supporting files
  createFixtures(): Promise<FixtureDefinition>;
  createDataLoaders(): Promise<DataLoader>;
  generateRequirements(): Promise<string[]>;
  
  // Output
  packageOutput(): Promise<GeneratedCode>;
}

interface GeneratedCode {
  testPy: string;              // test.py file content
  fixturesJson: object;        // fixtures.json
  dataLoaders: object;         // Data loading scripts
  requirements: string[];      // Python dependencies
  metadata: {
    linesOfCode: number;
    asyncFunctions: number;
    fixturesCount: number;
    generationTimestamp: number;
  };
}
```

**Outputs**:
- `test.py` - Complete Playwright Python test
- `fixtures.json` - Reusable test fixtures
- `data_loaders.py` - Data loading utilities
- `requirements.txt` - Python dependencies

---

### 2.4 Agent 4: Executor

**Purpose**: Test Execution & Reporting

**Responsibilities**:
- Run generated Playwright tests in target browser
- Manage complete test execution lifecycle
- Capture comprehensive evidence
- Generate detailed reports

**Interface**:
```typescript
interface ExecutorAgent {
  execute(state: PACSState): Promise<PACSState>;
  
  // Lifecycle management
  setupBrowser(): Promise<Browser>;
  navigateToPage(url: string): Promise<void>;
  runTestSteps(steps: TestStep[]): Promise<TestResult[]>;
  cleanupResources(): Promise<void>;
  
  // Evidence capture
  captureScreenshots(): Promise<Screenshot[]>;
  recordVideo(): Promise<string>;
  captureTraces(): Promise<string>;
  captureConsoleLogs(): Promise<ConsoleLog[]>;
  captureNetworkActivity(): Promise<NetworkLog[]>;
  measurePerformance(): Promise<PerformanceMetric[]>;
  
  // Reporting
  generateExecutionReport(): Promise<ExecutionReport>;
}

interface Evidence {
  screenshots: Screenshot[];       // At key steps and failures
  videos: string[];               // Full test execution
  traces: string[];              // Playwright trace files
  consoleLogs: ConsoleLog[];     // JavaScript errors
  networkActivity: NetworkLog[]; // API calls & responses
  performanceMetrics: PerformanceMetric[]; // Page load, interaction latency
}

interface ExecutionReport {
  runId: string;
  outcome: 'pass' | 'fail' | 'skip';
  
  // Detailed results
  assertionResults: AssertionResult[];  // Expected vs actual
  failureDetails: FailureDetail[];      // Root cause analysis
  executionTiming: TimingInfo;          // Performance tracking
  
  // Evidence references
  evidencePaths: {
    screenshots: string[];
    videos: string[];
    traces: string[];
  };
  
  // Metadata
  browserInfo: BrowserInfo;
  environmentInfo: EnvironmentInfo;
  timestamp: number;
}
```

**Outputs**:
- `run.report.json` - Detailed execution report
- Evidence files (screenshots, videos, traces)
- Performance metrics

---

### 2.5 Agent 5: OracleHealer

**Purpose**: Autonomous Test Repair

**Responsibilities**:
- Analyze test failures to identify root causes
- Query procedural memory for proven healing strategies
- Apply healing tactics (reprobe, wait adjustments, etc.)
- Validate fixes
- Request human approval when needed (via LangGraph interrupt gates)
- Achieve 70% autonomous healing success

**Interface**:
```typescript
interface OracleHealerAgent {
  execute(state: PACSState): Promise<PACSState>;
  
  // Failure analysis
  analyzeFailures(failures: TestFailure[]): Promise<FailureAnalysis[]>;
  identifyRootCause(failure: TestFailure): Promise<RootCause>;
  classifyFailureType(): Promise<FailureType>;
  
  // Memory queries
  queryProceduralMemory(failureType: string): Promise<HealingStrategy[]>;
  getHistoricalSuccessRates(): Promise<StrategySuccessRate[]>;
  
  // Healing tactics
  applyReprobeStrategy(element: string): Promise<HealingResult>;
  adjustWaitStrategy(timeout: number): Promise<HealingResult>;
  changeViewportConfig(viewport: ViewportConfig): Promise<HealingResult>;
  correctTestData(data: TestData): Promise<HealingResult>;
  
  // Validation
  validateFix(): Promise<boolean>;
  
  // Human-in-loop
  requestHumanApproval(failure: TestFailure): Promise<ApprovalResult>;
  explainHealingDecision(): Promise<string>;
}

interface RootCause {
  type: 'element-not-found' | 'timeout' | 'assertion-failed' | 'environment';
  confidence: number;
  evidence: string[];
  suggestedFix: string;
}

interface HealingStrategy {
  tactic: 'reprobe' | 'wait-adjustment' | 'viewport-change' | 'data-correction';
  description: string;
  historicalSuccessRate: number;  // From procedural memory
  estimatedTime: number;
  requiresApproval: boolean;
  steps: HealingStep[];
}

interface HealingResult {
  status: 'success' | 'failure' | 'needs-approval';
  attemptCount: number;
  strategyUsed: string;
  modifications: CodeModification[];
  validationResult: ValidationResult;
  timestamp: number;
}
```

**Outputs**:
- `healing.report.json` - Healing attempt details
- Modified test code (if healing successful)
- Approval requests (if human input needed)

---

## 3. State Machine Specification

### 3.1 PACSState Definition

```typescript
interface PACSState {
  // Current phase (5 agents)
  phase: 'planner' | 'pom-builder' | 'generator' | 'executor' | 'oracle-healer' | 'complete';
  
  // Input from Excel
  testScenario: TestScenario;
  targetUrl: string;
  excelRequirements: string;  // Path to Excel file
  
  // Planner outputs
  testPlan?: TestPlan;
  dataBindings?: DataBinding[];
  policies?: PolicyConfig[];
  retryStrategies?: RetryStrategy[];
  
  // POMBuilder outputs
  formJSON?: FormDefinition;
  verifiedSelectors?: VerifiedElement[];
  fallbackChains?: FallbackChain[];
  discoveryStrategies?: DiscoveryStrategy[];
  
  // Generator outputs
  testPy?: string;
  fixturesJson?: object;
  dataLoaders?: object;
  generatedCode?: GeneratedCode;
  
  // Executor outputs
  testResults?: TestResult[];
  evidence?: Evidence;
  executionReport?: ExecutionReport;
  
  // OracleHealer outputs
  failures?: TestFailure[];
  healingAttempts?: HealingAttempt[];
  healingResult?: HealingResult;
  
  // Memory references
  episodicMemory?: HistoricalPattern[];
  proceduralMemory?: HealingStrategy[];
  
  // Metadata
  timestamp: number;
  iterationCount: number;
  humanApproval?: boolean;
  checkpointId?: string;  // LangGraph checkpoint ID
  
  // Observability
  traces?: LangSmithTrace[];
  metrics?: PerformanceMetric[];
}
```

### 3.2 State Transitions

```typescript
type StateTransition = 
  // Forward flow
  | { from: 'planner', to: 'pom-builder', condition: 'plan-complete' }
  | { from: 'pom-builder', to: 'generator', condition: 'pom-verified' }
  | { from: 'generator', to: 'executor', condition: 'code-generated' }
  | { from: 'executor', to: 'complete', condition: 'test-passed' }
  | { from: 'executor', to: 'oracle-healer', condition: 'test-failed' }
  
  // Healing loop
  | { from: 'oracle-healer', to: 'generator', condition: 'code-fix-needed' }
  | { from: 'oracle-healer', to: 'executor', condition: 'retry-execution' }
  | { from: 'oracle-healer', to: 'complete', condition: 'max-retries-reached' }
  
  // Human intervention
  | { from: 'oracle-healer', to: 'human-approval', condition: 'needs-approval' }
  | { from: 'human-approval', to: 'oracle-healer', condition: 'approved' }
  | { from: 'human-approval', to: 'complete', condition: 'rejected' };

// Maximum iterations per phase
const MAX_HEALING_ATTEMPTS = 3;
const MAX_GENERATION_RETRIES = 2;
const MAX_EXECUTION_RETRIES = 3;
```

### 3.3 LangGraph Configuration

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresCheckpointer

# Define state machine
workflow = StateGraph(PACSState)

# Add agent nodes
workflow.add_node("planner", planner_agent)
workflow.add_node("pom_builder", pom_builder_agent)
workflow.add_node("generator", generator_agent)
workflow.add_node("executor", executor_agent)
workflow.add_node("oracle_healer", oracle_healer_agent)

# Define edges (transitions)
workflow.add_edge("planner", "pom_builder")
workflow.add_edge("pom_builder", "generator")
workflow.add_edge("generator", "executor")

# Conditional edges for healing
workflow.add_conditional_edges(
    "executor",
    lambda state: "complete" if state.testResults.passed else "oracle_healer"
)

workflow.add_conditional_edges(
    "oracle_healer",
    lambda state: route_healing_result(state)
)

# Set entry point
workflow.set_entry_point("planner")

# Configure checkpointer for state persistence
checkpointer = PostgresCheckpointer(
    connection_string=os.getenv("POSTGRES_CONNECTION")
)

# Compile with checkpointer
app = workflow.compile(checkpointer=checkpointer)
```

---

## 4. Memory Architecture

### 4.1 Three Memory Systems

**Episodic Memory (PostgreSQL)**
- **Purpose**: Long-term storage of test runs
- **Retention**: Last 100 test runs per requirement
- **Contents**: 
  - Agent decisions at each phase
  - State transitions
  - Execution traces
  - Success/failure outcomes
- **Used by**: Planner Agent (pattern recognition)

**Working Memory (Redis 7+)**
- **Purpose**: High-speed session caching
- **Retention**: 1 hour TTL
- **Contents**:
  - Current test context
  - Discovered locators
  - Intermediate agent outputs
  - Browser state snapshots
- **Used by**: All agents (current run data)

**Procedural Memory (In-memory/Database)**
- **Purpose**: Healing strategy repository
- **Contents**:
  - Healing tactics with success rates
  - Strategy selection rules
  - Failure type classifications
  - Historical effectiveness data
- **Used by**: OracleHealer Agent (strategy selection)

### 4.2 Memory Interfaces

```typescript
interface EpisodicMemory {
  store(runData: TestRunData): Promise<void>;
  query(requirement: string, limit: number): Promise<HistoricalPattern[]>;
  analyze(patterns: HistoricalPattern[]): Promise<PatternAnalysis>;
}

interface WorkingMemory {
  set(key: string, value: any, ttl?: number): Promise<void>;
  get(key: string): Promise<any>;
  delete(key: string): Promise<void>;
  flush(): Promise<void>;
}

interface ProceduralMemory {
  getStrategies(failureType: string): Promise<HealingStrategy[]>;
  updateSuccessRate(strategy: string, success: boolean): Promise<void>;
  rankStrategies(failureType: string): Promise<RankedStrategy[]>;
}
```

---

## 5. Observability with LangSmith

### 5.1 Trace Capture

```typescript
interface LangSmithTrace {
  // Agent execution
  agentName: string;
  phase: string;
  
  // Timing
  startTime: number;
  endTime: number;
  duration: number;
  
  // Decision making
  strategySelection: StrategyDecision;
  confidence: number;
  rationale: string;
  
  // Results
  success: boolean;
  output: any;
  errors?: Error[];
  
  // Costs
  tokenCount: number;
  tokenCost: number;
  
  // Context
  state: Partial<PACSState>;
  metadata: Record<string, any>;
}
```

### 5.2 Metrics Collection

```typescript
interface ObservabilityMetrics {
  // Agent performance
  agentExecutionTime: Record<string, number>;
  agentSuccessRate: Record<string, number>;
  
  // Discovery
  discoveryTime: number;
  strategiesAttempted: number;
  fallbackChainsGenerated: number;
  
  // Healing
  healingAttempts: number;
  healingSuccessRate: number;
  averageHealingTime: number;
  
  // Costs
  totalTokens: number;
  totalCost: number;
  costPerAgent: Record<string, number>;
  
  // Quality
  testPassRate: number;
  falsePositiveRate: number;
  coverageMetrics: CoverageMetric[];
}
```

---

## 6. Technology Stack

### 6.1 Core Components

**LangGraph Orchestration (Python)**
```
langgraph==0.1.0         # State machine
langchain==0.1.0         # LLM integration  
langsmith==0.1.0         # Observability
pydantic==2.5.0          # Data validation
```

**Runtime (TypeScript + Python hybrid)**
```
TypeScript: CLI, MCP, UWA, Playwright interactions
Python: LangGraph orchestration, agent nodes
Bridge: REST API or gRPC between TypeScript and Python
```

**Databases**
```
PostgreSQL 14+   # Episodic memory + LangGraph checkpoints
Redis 7+         # Working memory (session cache)
```

**Browser Automation**
```
Playwright 1.56+ # Python version
Chromium/Firefox/WebKit
```

---

## 7. Development Roadmap

### Phase 1: Foundation (Weeks 1-2)
- ✅ TypeScript CLI (already complete)
- ✅ MCP Server (already complete)  
- ✅ Policy system (already complete)
- ⏳ Python LangGraph setup
- ⏳ PostgreSQL + Redis setup

### Phase 2: Agent Implementation (Weeks 3-6)

**Week 3: Planner Agent**
- Excel reader
- Memory queries
- Plan generation
- State machine setup

**Week 4: POMBuilder Agent**
- Multi-strategy discovery
- 5-point verification
- Fallback chain generation
- form.json output

**Week 5: Generator Agent**
- Python code generation
- Async/await patterns
- Fixtures and data loaders
- Type hints

**Week 6: Executor Agent**
- Test execution
- Evidence capture
- Report generation

### Phase 3: Healing & Integration (Weeks 7-8)

**Week 7: OracleHealer Agent**
- Failure analysis
- Procedural memory
- Healing strategies
- Validation

**Week 8: Integration**
- Connect all agents
- State persistence
- Human-in-loop gates
- End-to-end testing

### Phase 4: Production (Weeks 9-12)
- Performance optimization
- Observability
- Documentation
- Deployment

---

## 8. Success Criteria

### Technical Metrics
- **Selector Verification**: 95%+ pass rate
- **Healing Success**: 70%+ autonomous fixes
- **Test Pass Rate**: 90%+ on first run
- **False Positives**: <5%

### Performance Metrics
- **Plan Generation**: <60 seconds
- **POM Building**: <30 seconds per page
- **Code Generation**: <20 seconds
- **Healing**: <60 seconds per failure

### Target Sites
- **SauceDemo**: 75% (proven in prototype)
- **GitHub**: 95%
- **Amazon**: 90%

---

## 9. Key Differentiators

### vs Traditional AI Testing (70-80% success)

**PACTS Advantages**:
1. **Find-First** (not guess-and-check) - 95%+ success
2. **5-Point Verification** - guaranteed actionability
3. **Multi-Strategy Discovery** - Shadow DOM, iframes, patterns
4. **Fallback Chains** - resilience built-in
5. **External Ground Truth** (Excel) - no circular dependency
6. **Three Memory Systems** - learns from history
7. **70% Healing Success** - autonomous recovery

---

## 10. File Outputs Summary

### By Agent

**Planner**:
- `plan.json`

**POMBuilder**:
- `form.json`

**Generator**:
- `test.py`
- `fixtures.json`
- `data_loaders.py`
- `requirements.txt`

**Executor**:
- `run.report.json`
- `screenshots/*.png`
- `videos/*.webm`
- `traces/*.zip`

**OracleHealer**:
- `healing.report.json`
- `modified_test.py` (if healing succeeded)

---

## 11. Next Steps for Implementation

### Critical Decision: TypeScript vs Python

**Recommended Hybrid Approach**:
```
Python (LangGraph):
- 5 agent nodes
- State machine
- Memory management
- Observability

TypeScript:
- CLI interface
- MCP server
- UWA (element discovery)
- Playwright interaction

Bridge:
- REST API (FastAPI)
- Shared state via JSON
```

### Start with:
1. Setup Python LangGraph environment
2. Implement Planner agent (simplest)
3. Setup PostgreSQL + Redis
4. Build REST bridge to TypeScript
5. Implement remaining agents sequentially

---

**Document Version**: 2.0  
**Status**: CORRECTED - 5 Agents  
**Ready for**: Claude Code implementation

---
