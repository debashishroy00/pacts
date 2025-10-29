# PACTS 5-Agent Development Starter Guide

**Version**: 2.0  
**Date**: October 28, 2025  
**Purpose**: Implementation guide for 5-agent PACTS system

---

## 1. CRITICAL: 5 Agents, Not 3

**Correct Agent Pipeline**:
```
Planner → POMBuilder → Generator → Executor → OracleHealer
```

**Previous Incorrect** (3 agents): ~~Planner → Generator → Healer~~

---

## 2. Quick Start

### 2.1 Project Structure (Updated)

```
pacts/
├── src/                    # TypeScript (CLI, MCP, UWA)
│   ├── agents/
│   │   └── types.ts       # Agent interfaces (5 agents)
│   ├── cli.ts
│   ├── llm/
│   ├── mcp/
│   ├── policy/
│   └── uwa/               # Universal Web Adapter
├── python/                 # Python (LangGraph orchestration)
│   └── agents/
│       ├── planner.py
│       ├── pom_builder.py
│       ├── generator.py
│       ├── executor.py
│       └── oracle_healer.py
├── policies/               # Site configurations
├── specs/                  # Test plans
└── tests/                  # Generated tests
```

### 2.2 Technology Decision

**HYBRID APPROACH** (Recommended):

```
TypeScript Side:
- CLI interface (already working)
- MCP server (already working)
- Universal Web Adapter (element discovery)
- Playwright browser automation
- Policy engine (already working)

Python Side:
- LangGraph state machine (5 agents)
- Agent orchestration
- Memory management (PostgreSQL, Redis)
- LangSmith observability

Communication:
- REST API bridge (FastAPI)
- Shared state via JSON files
- WebSocket for real-time updates
```

---

## 3. Agent-by-Agent Implementation Guide

### 3.1 Agent 1: Planner (SIMPLEST - START HERE)

**Purpose**: Test Discovery & Flow Control

**Dependencies**:
```bash
# Python
pip install openpyxl pandas pydantic

# Already have:
# - LangGraph
# - LangChain
```

**Implementation**: `python/agents/planner.py`

```python
from typing import Dict, List, Any
from pydantic import BaseModel
import openpyxl
import json

class TestScenario(BaseModel):
    id: str
    feature: str
    scenario: str
    steps: List[Dict[str, str]]
    expectedOutcome: str
    priority: str

class TestPlan(BaseModel):
    scenarios: List[TestScenario]
    dataBindings: Dict[str, Any]
    policies: List[str]
    retryStrategies: Dict[str, int]

class PlannerAgent:
    """
    Agent 1: Planner - Test Discovery & Flow Control
    
    Reads Excel requirements, queries episodic memory,
    generates comprehensive plan.json
    """
    
    def __init__(self, memory_connector):
        self.memory = memory_connector
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method called by LangGraph"""
        
        # 1. Read Excel requirements
        excel_path = state.get("excelRequirements")
        scenarios = self.read_excel_requirements(excel_path)
        
        # 2. Query episodic memory for patterns
        patterns = await self.query_episodic_memory(scenarios)
        
        # 3. Generate test plan
        plan = self.generate_plan(scenarios, patterns)
        
        # 4. Select policies
        policies = self.select_policies(state.get("targetUrl"))
        
        # 5. Define retry strategies
        retries = self.define_retry_strategies(scenarios)
        
        # 6. Create plan.json
        test_plan = TestPlan(
            scenarios=scenarios,
            dataBindings=self.extract_data_bindings(scenarios),
            policies=policies,
            retryStrategies=retries
        )
        
        # 7. Save to file
        with open("plan.json", "w") as f:
            json.dump(test_plan.dict(), f, indent=2)
        
        # 8. Update state
        state["testPlan"] = test_plan.dict()
        state["phase"] = "pom-builder"
        
        return state
    
    def read_excel_requirements(self, excel_path: str) -> List[TestScenario]:
        """Parse Excel file to extract test scenarios"""
        workbook = openpyxl.load_workbook(excel_path)
        sheet = workbook.active
        
        scenarios = []
        current_scenario = None
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            scenario_id, feature, scenario, step_num, action, target, input_val, expected = row
            
            if scenario_id and scenario_id != current_scenario:
                # New scenario
                current_scenario = scenario_id
                scenarios.append(TestScenario(
                    id=scenario_id,
                    feature=feature,
                    scenario=scenario,
                    steps=[],
                    expectedOutcome=expected,
                    priority="P1"  # Default
                ))
            
            # Add step
            if action:
                scenarios[-1].steps.append({
                    "stepNumber": step_num,
                    "action": action,
                    "target": target,
                    "input": input_val,
                    "expectedState": expected
                })
        
        return scenarios
    
    async def query_episodic_memory(self, scenarios: List[TestScenario]) -> List[Dict]:
        """Query episodic memory for historical patterns"""
        patterns = []
        
        for scenario in scenarios:
            # Query PostgreSQL for similar past runs
            similar_runs = await self.memory.query(
                feature=scenario.feature,
                limit=10
            )
            patterns.extend(similar_runs)
        
        return patterns
    
    def generate_plan(self, scenarios: List[TestScenario], patterns: List[Dict]) -> Dict:
        """Generate comprehensive test plan"""
        # Analyze patterns to optimize execution order
        # Group related scenarios
        # Identify data dependencies
        
        return {
            "executionOrder": [s.id for s in scenarios],
            "parallelizable": self.identify_parallel_scenarios(scenarios),
            "dependencies": self.identify_dependencies(scenarios)
        }
    
    def select_policies(self, url: str) -> List[str]:
        """Select appropriate policies for target URL"""
        if "saucedemo" in url:
            return ["saucedemo"]
        elif "amazon" in url:
            return ["amazon"]
        elif "github" in url:
            return ["github"]
        else:
            return ["generic"]
    
    def define_retry_strategies(self, scenarios: List[TestScenario]) -> Dict[str, int]:
        """Define retry strategies based on scenario priority"""
        return {
            "maxRetries": 3,
            "retryDelay": 1000,  # ms
            "exponentialBackoff": True
        }
    
    def extract_data_bindings(self, scenarios: List[TestScenario]) -> Dict[str, Any]:
        """Extract data bindings from scenarios"""
        bindings = {}
        
        for scenario in scenarios:
            for step in scenario.steps:
                if step.get("input"):
                    key = f"{scenario.id}_{step['target']}"
                    bindings[key] = step["input"]
        
        return bindings
    
    def identify_parallel_scenarios(self, scenarios: List[TestScenario]) -> List[str]:
        """Identify scenarios that can run in parallel"""
        # Simple heuristic: different features can run in parallel
        return [s.id for s in scenarios if s.priority == "P0"]
    
    def identify_dependencies(self, scenarios: List[TestScenario]) -> Dict[str, List[str]]:
        """Identify scenario dependencies"""
        # Login scenarios should run first
        deps = {}
        
        login_scenarios = [s.id for s in scenarios if "login" in s.scenario.lower()]
        
        for scenario in scenarios:
            if scenario.id not in login_scenarios and login_scenarios:
                deps[scenario.id] = login_scenarios
        
        return deps
```

**Testing**: `python/agents/test_planner.py`

```python
import pytest
from planner import PlannerAgent
import asyncio

@pytest.fixture
def sample_state():
    return {
        "excelRequirements": "tests/fixtures/requirements.xlsx",
        "targetUrl": "https://www.saucedemo.com"
    }

@pytest.mark.asyncio
async def test_planner_reads_excel(sample_state):
    agent = PlannerAgent(memory_connector=MockMemory())
    
    result = await agent.execute(sample_state)
    
    assert "testPlan" in result
    assert "scenarios" in result["testPlan"]
    assert len(result["testPlan"]["scenarios"]) > 0

@pytest.mark.asyncio
async def test_planner_generates_plan_json(sample_state):
    agent = PlannerAgent(memory_connector=MockMemory())
    
    result = await agent.execute(sample_state)
    
    # Verify plan.json was created
    import os
    assert os.path.exists("plan.json")
    
    # Verify structure
    import json
    with open("plan.json") as f:
        plan = json.load(f)
    
    assert "scenarios" in plan
    assert "dataBindings" in plan
    assert "policies" in plan

class MockMemory:
    async def query(self, **kwargs):
        return []
```

**Checkpoint Verification**:
```bash
# Run tests
pytest python/agents/test_planner.py -v

# Verify plan.json structure
cat plan.json | jq .

# Commit
git add python/agents/planner.py
git commit -m "Checkpoint 12: Planner Agent implementation"
git tag checkpoint-12
```

---

### 3.2 Agent 2: POMBuilder (MOST COMPLEX)

**Purpose**: Multi-Strategy Locator Discovery

**Key Challenge**: This agent needs deep integration with TypeScript UWA

**Architecture Decision**:
```
Option 1: Python calls TypeScript via REST API
Option 2: TypeScript UWA, Python orchestration only
Option 3: Rewrite UWA in Python (time-consuming)

RECOMMENDED: Option 2
- Keep UWA in TypeScript (already partially built)
- Python agent calls TypeScript UWA via REST
- POMBuilder orchestrates, UWA executes
```

**Implementation**: `python/agents/pom_builder.py`

```python
import httpx
import json
from typing import List, Dict, Any
from pydantic import BaseModel

class VerifiedElement(BaseModel):
    id: str
    type: str
    description: str
    selector: str
    fallbackSelectors: List[str]
    confidenceScore: float
    strategy: str

class FormDefinition(BaseModel):
    pageUrl: str
    elements: List[VerifiedElement]
    fallbackChains: List[Dict]
    shadowDomPaths: List[Dict]
    metadata: Dict

class POMBuilderAgent:
    """
    Agent 2: POMBuilder - Multi-Strategy Locator Discovery
    
    Analyzes page structure, selects discovery strategies,
    validates through 5-Point Gate, builds fallback chains.
    """
    
    def __init__(self, uwa_endpoint: str = "http://localhost:3000"):
        self.uwa_endpoint = uwa_endpoint
        self.client = httpx.AsyncClient()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method called by LangGraph"""
        
        # 1. Load policy
        policy = await self.load_policy(state["policies"][0])
        
        # 2. Analyze page structure via UWA
        page_analysis = await self.analyze_page_structure(
            state["targetUrl"], 
            policy
        )
        
        # 3. Detect Shadow DOM
        shadow_dom_info = page_analysis.get("shadowDomInfo", [])
        
        # 4. Detect iframes
        iframe_info = page_analysis.get("iframeInfo", [])
        
        # 5. Select discovery strategies
        strategies = self.select_strategies(page_analysis)
        
        # 6. Discover elements using selected strategies
        elements = await self.discover_elements(
            state["targetUrl"],
            strategies,
            policy
        )
        
        # 7. Validate actionability (5-Point Gate)
        verified_elements = await self.validate_elements(elements)
        
        # 8. Build fallback chains
        fallback_chains = self.build_fallback_chains(verified_elements)
        
        # 9. Generate form.json
        form_def = FormDefinition(
            pageUrl=state["targetUrl"],
            elements=verified_elements,
            fallbackChains=fallback_chains,
            shadowDomPaths=shadow_dom_info,
            metadata={
                "totalElements": len(elements),
                "verifiedElements": len(verified_elements),
                "strategiesUsed": [s["type"] for s in strategies]
            }
        )
        
        # 10. Save form.json
        with open("form.json", "w") as f:
            json.dump(form_def.dict(), f, indent=2)
        
        # 11. Update state
        state["formJSON"] = form_def.dict()
        state["phase"] = "generator"
        
        return state
    
    async def load_policy(self, policy_name: str) -> Dict:
        """Load policy from TypeScript policy engine"""
        response = await self.client.get(
            f"{self.uwa_endpoint}/api/policies/{policy_name}"
        )
        return response.json()
    
    async def analyze_page_structure(self, url: str, policy: Dict) -> Dict:
        """Call TypeScript UWA to analyze page structure"""
        response = await self.client.post(
            f"{self.uwa_endpoint}/api/analyze-page",
            json={"url": url, "policy": policy}
        )
        return response.json()
    
    def select_strategies(self, analysis: Dict) -> List[Dict]:
        """Select optimal discovery strategies based on page analysis"""
        strategies = []
        
        # Always try semantic first
        strategies.append({
            "type": "semantic",
            "priority": 1,
            "confidence": 0.9
        })
        
        # If Shadow DOM detected, add shadow strategy
        if analysis.get("shadowDomInfo"):
            strategies.append({
                "type": "shadow-dom",
                "priority": 2,
                "confidence": 0.8
            })
        
        # If iframes detected, add iframe strategy
        if analysis.get("iframeInfo"):
            strategies.append({
                "type": "iframe",
                "priority": 3,
                "confidence": 0.7
            })
        
        # Always include pattern matching as fallback
        strategies.append({
            "type": "pattern",
            "priority": 4,
            "confidence": 0.6
        })
        
        return strategies
    
    async def discover_elements(
        self, 
        url: str, 
        strategies: List[Dict],
        policy: Dict
    ) -> List[Dict]:
        """Discover elements using selected strategies"""
        
        # Call TypeScript UWA for each strategy
        all_elements = []
        
        for strategy in strategies:
            response = await self.client.post(
                f"{self.uwa_endpoint}/api/discover-elements",
                json={
                    "url": url,
                    "strategy": strategy["type"],
                    "policy": policy
                }
            )
            
            elements = response.json()["elements"]
            
            # Tag with strategy
            for elem in elements:
                elem["discoveryStrategy"] = strategy["type"]
                elem["strategyConfidence"] = strategy["confidence"]
            
            all_elements.extend(elements)
        
        return all_elements
    
    async def validate_elements(self, elements: List[Dict]) -> List[VerifiedElement]:
        """Validate elements through 5-Point Actionability Gate"""
        
        verified = []
        
        for elem in elements:
            # Call TypeScript UWA for validation
            response = await self.client.post(
                f"{self.uwa_endpoint}/api/verify-element",
                json={"element": elem}
            )
            
            validation_result = response.json()
            
            if validation_result["passed"]:
                verified.append(VerifiedElement(
                    id=elem["id"],
                    type=elem["type"],
                    description=elem["description"],
                    selector=elem["selector"],
                    fallbackSelectors=[],  # Filled by build_fallback_chains
                    confidenceScore=elem["strategyConfidence"],
                    strategy=elem["discoveryStrategy"]
                ))
        
        return verified
    
    def build_fallback_chains(self, elements: List[VerifiedElement]) -> List[Dict]:
        """Build fallback chains for resilience"""
        
        chains = []
        
        # Group elements by description
        element_groups = {}
        for elem in elements:
            if elem.description not in element_groups:
                element_groups[elem.description] = []
            element_groups[elem.description].append(elem)
        
        # Create fallback chains
        for description, elems in element_groups.items():
            if len(elems) > 1:
                # Sort by confidence
                elems.sort(key=lambda e: e.confidenceScore, reverse=True)
                
                primary = elems[0]
                alternatives = [e.selector for e in elems[1:]]
                
                chains.append({
                    "elementId": primary.id,
                    "primary": primary.selector,
                    "alternatives": alternatives,
                    "confidenceScores": [e.confidenceScore for e in elems]
                })
                
                # Update element with fallback selectors
                primary.fallbackSelectors = alternatives
        
        return chains
```

**TypeScript REST API** (bridge): `src/api/server.ts`

```typescript
import express from 'express';
import { PolicyEngine } from '../policy/PolicyEngine';
import { ElementDiscoveryService } from '../uwa/ElementDiscovery';
import { ActionabilityGates } from '../uwa/ActionabilityGates';
import { chromium } from '@playwright/test';

const app = express();
app.use(express.json());

const policyEngine = new PolicyEngine();

// Get policy
app.get('/api/policies/:name', async (req, res) => {
  const policy = await policyEngine.loadPolicy(req.params.name);
  res.json(policy);
});

// Analyze page structure
app.post('/api/analyze-page', async (req, res) => {
  const { url, policy } = req.body;
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  await page.goto(url);
  
  // Detect Shadow DOM
  const shadowDomInfo = await page.evaluate(() => {
    const elements = document.querySelectorAll('*');
    const shadowHosts = [];
    
    elements.forEach(el => {
      if (el.shadowRoot) {
        shadowHosts.push({
          selector: el.tagName.toLowerCase(),
          depth: 1
        });
      }
    });
    
    return shadowHosts;
  });
  
  // Detect iframes
  const iframes = await page.$$eval('iframe', (frames) => 
    frames.map(f => ({ src: f.src, name: f.name }))
  );
  
  await browser.close();
  
  res.json({
    shadowDomInfo,
    iframeInfo: iframes
  });
});

// Discover elements
app.post('/api/discover-elements', async (req, res) => {
  const { url, strategy, policy } = req.body;
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(url);
  
  const discovery = new ElementDiscoveryService();
  // Use strategy-specific discovery
  // ... implementation details
  
  await browser.close();
  
  res.json({ elements: [] }); // Populated elements
});

// Verify element
app.post('/api/verify-element', async (req, res) => {
  const { element } = req.body;
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(element.pageUrl);
  
  const gates = new ActionabilityGates(page);
  const result = await gates.verify(element);
  
  await browser.close();
  
  res.json(result);
});

app.listen(3000, () => {
  console.log('UWA API server running on port 3000');
});
```

---

### 3.3 Agent 3: Generator (MODERATE)

**Purpose**: Code Synthesis

**Implementation**: `python/agents/generator.py`

```python
import json
from typing import Dict, Any
from jinja2 import Template

class GeneratorAgent:
    """
    Agent 3: Generator - Code Synthesis
    
    Takes plan.json and form.json to generate production-ready
    Playwright Python tests with verified selectors.
    """
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Load plan.json
        with open("plan.json") as f:
            plan = json.load(f)
        
        # 2. Load form.json
        with open("form.json") as f:
            form = json.load(f)
        
        # 3. Generate test.py
        test_code = self.generate_test_code(plan, form)
        
        # 4. Generate fixtures.json
        fixtures = self.generate_fixtures(plan, form)
        
        # 5. Generate data loaders
        data_loaders = self.generate_data_loaders(plan)
        
        # 6. Save files
        with open("test.py", "w") as f:
            f.write(test_code)
        
        with open("fixtures.json", "w") as f:
            json.dump(fixtures, f, indent=2)
        
        with open("data_loaders.py", "w") as f:
            f.write(data_loaders)
        
        # 7. Update state
        state["testPy"] = test_code
        state["phase"] = "executor"
        
        return state
    
    def generate_test_code(self, plan: Dict, form: Dict) -> str:
        """Generate Playwright Python test code"""
        
        template = Template('''
import pytest
from playwright.async_api import async_playwright, Page
import json

@pytest.fixture
async def browser_page():
    """Setup browser and page"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        yield page
        await browser.close()

{% for scenario in scenarios %}
async def test_{{ scenario.id }}(browser_page: Page):
    """{{ scenario.scenario }}"""
    page = browser_page
    
    # Navigate
    await page.goto("{{ base_url }}")
    
    {% for step in scenario.steps %}
    # Step {{ step.stepNumber }}: {{ step.action }}
    {% if step.action == "Enter" %}
    await page.locator("{{ get_selector(step.target) }}").fill("{{ step.input }}")
    {% elif step.action == "Click" %}
    await page.locator("{{ get_selector(step.target) }}").click()
    {% endif %}
    
    # Verify: {{ step.expectedState }}
    await page.wait_for_load_state("networkidle")
    {% endfor %}
    
    # Final assertion
    assert "{{ scenario.expectedOutcome }}" in await page.content()
{% endfor %}
''')
        
        return template.render(
            scenarios=plan["scenarios"],
            base_url=form["pageUrl"],
            get_selector=lambda target: self.find_selector(target, form)
        )
    
    def find_selector(self, target: str, form: Dict) -> str:
        """Find selector for target from form.json"""
        for elem in form["elements"]:
            if target.lower() in elem["description"].lower():
                return elem["selector"]
        return ""
    
    def generate_fixtures(self, plan: Dict, form: Dict) -> Dict:
        """Generate fixtures.json"""
        return {
            "baseUrl": form["pageUrl"],
            "timeout": 5000,
            "retries": 3
        }
    
    def generate_data_loaders(self, plan: Dict) -> str:
        """Generate data loader code"""
        return '''
import json

def load_test_data(scenario_id: str) -> dict:
    """Load test data for scenario"""
    with open("test_data.json") as f:
        data = json.load(f)
    return data.get(scenario_id, {})
'''
```

---

### 3.4 Agent 4: Executor (STRAIGHTFORWARD)

**Purpose**: Test Execution & Reporting

**Implementation**: `python/agents/executor.py`

```python
import subprocess
import json
from typing import Dict, Any

class ExecutorAgent:
    """
    Agent 4: Executor - Test Execution & Reporting
    
    Runs generated Playwright tests and captures evidence.
    """
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Run pytest
        result = subprocess.run(
            ["pytest", "test.py", "--json-report", "--json-report-file=run.report.json"],
            capture_output=True,
            text=True
        )
        
        # 2. Load report
        with open("run.report.json") as f:
            report = json.load(f)
        
        # 3. Check if tests passed
        passed = report["summary"]["passed"] > 0
        failed = report["summary"]["failed"] > 0
        
        # 4. Update state
        state["executionReport"] = report
        
        if passed and not failed:
            state["phase"] = "complete"
        else:
            state["phase"] = "oracle-healer"
            state["failures"] = report["tests"]
        
        return state
```

---

### 3.5 Agent 5: OracleHealer (COMPLEX)

**Purpose**: Autonomous Test Repair

**Implementation**: `python/agents/oracle_healer.py`

```python
from typing import Dict, Any, List

class OracleHealerAgent:
    """
    Agent 5: OracleHealer - Autonomous Test Repair
    
    Analyzes failures, queries procedural memory, applies healing tactics.
    """
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        failures = state["failures"]
        
        healing_results = []
        
        for failure in failures:
            # 1. Analyze failure
            root_cause = self.identify_root_cause(failure)
            
            # 2. Query procedural memory
            strategies = await self.query_procedural_memory(root_cause)
            
            # 3. Apply healing tactic
            for strategy in strategies:
                result = await self.apply_healing(strategy, failure)
                
                if result["status"] == "success":
                    healing_results.append(result)
                    break
        
        # 4. Update state
        state["healingResult"] = healing_results
        
        if len(healing_results) == len(failures):
            # All healed, retry execution
            state["phase"] = "executor"
        else:
            # Some failures remain
            state["phase"] = "complete"
        
        return state
    
    def identify_root_cause(self, failure: Dict) -> Dict:
        """Identify failure root cause"""
        error_msg = failure["call"]["longrepr"]
        
        if "element not found" in error_msg.lower():
            return {"type": "element-not-found", "confidence": 0.9}
        elif "timeout" in error_msg.lower():
            return {"type": "timeout", "confidence": 0.8}
        else:
            return {"type": "unknown", "confidence": 0.5}
    
    async def query_procedural_memory(self, root_cause: Dict) -> List[Dict]:
        """Query procedural memory for healing strategies"""
        # Return strategies based on failure type
        if root_cause["type"] == "element-not-found":
            return [
                {
                    "tactic": "reprobe",
                    "successRate": 0.75
                },
                {
                    "tactic": "wait-adjustment",
                    "successRate": 0.60
                }
            ]
        return []
    
    async def apply_healing(self, strategy: Dict, failure: Dict) -> Dict:
        """Apply healing tactic"""
        # Implement healing logic
        return {"status": "success"}
```

---

## 4. LangGraph Integration

**Main orchestration**: `python/main.py`

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresCheckpointer
from agents.planner import PlannerAgent
from agents.pom_builder import POMBuilderAgent
from agents.generator import GeneratorAgent
from agents.executor import ExecutorAgent
from agents.oracle_healer import OracleHealerAgent

# Initialize agents
planner = PlannerAgent(memory_connector=memory)
pom_builder = POMBuilderAgent()
generator = GeneratorAgent()
executor = ExecutorAgent()
oracle_healer = OracleHealerAgent()

# Define state machine
workflow = StateGraph(dict)

# Add nodes (5 agents)
workflow.add_node("planner", planner.execute)
workflow.add_node("pom_builder", pom_builder.execute)
workflow.add_node("generator", generator.execute)
workflow.add_node("executor", executor.execute)
workflow.add_node("oracle_healer", oracle_healer.execute)

# Add edges
workflow.add_edge("planner", "pom_builder")
workflow.add_edge("pom_builder", "generator")
workflow.add_edge("generator", "executor")

# Conditional edge from executor
def route_from_executor(state):
    return state["phase"]

workflow.add_conditional_edges(
    "executor",
    route_from_executor,
    {
        "complete": END,
        "oracle-healer": "oracle_healer"
    }
)

# Conditional edge from healer
workflow.add_conditional_edges(
    "oracle_healer",
    route_from_executor,
    {
        "executor": "executor",
        "complete": END
    }
)

# Set entry point
workflow.set_entry_point("planner")

# Compile with checkpoint
checkpointer = PostgresCheckpointer(...)
app = workflow.compile(checkpointer=checkpointer)

# Run
initial_state = {
    "excelRequirements": "requirements.xlsx",
    "targetUrl": "https://www.saucedemo.com",
    "phase": "planner"
}

result = await app.ainvoke(initial_state)
```

---

## 5. Development Sequence

### Phase 1: Setup (Week 1)
- [ ] Python environment setup
- [ ] PostgreSQL setup
- [ ] Redis setup
- [ ] TypeScript REST API server

### Phase 2: Agents (Weeks 2-6)
- [ ] Checkpoint 12: Planner Agent
- [ ] Checkpoint 13: POMBuilder Agent
- [ ] Checkpoint 14: Generator Agent
- [ ] Checkpoint 15: Executor Agent
- [ ] Checkpoint 16: OracleHealer Agent

### Phase 3: Integration (Week 7)
- [ ] LangGraph state machine
- [ ] Agent-to-agent communication
- [ ] State persistence
- [ ] Memory systems

### Phase 4: Testing (Week 8)
- [ ] End-to-end tests
- [ ] SauceDemo verification
- [ ] Amazon/GitHub tests
- [ ] Performance optimization

---

## 6. Verification Commands

```bash
# Test Planner
pytest python/agents/test_planner.py -v

# Test POMBuilder
pytest python/agents/test_pom_builder.py -v

# Test Generator
pytest python/agents/test_generator.py -v

# Test full pipeline
python python/main.py --excel requirements.xlsx --url https://www.saucedemo.com

# Verify outputs
ls -la plan.json form.json test.py run.report.json

# Check LangSmith traces
open https://smith.langchain.com/
```

---

**Version**: 2.0  
**Status**: Ready for 5-Agent Implementation  
**Next Step**: Begin Checkpoint 12 (Planner Agent)
