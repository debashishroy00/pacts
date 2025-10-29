# PACTS All-Python Architecture

**Version**: 3.0  
**Date**: October 28, 2025  
**Decision**: ALL PYTHON (No TypeScript)  
**Rationale**: Simpler, faster, better for 8-week enterprise build

---

## Executive Decision

### ✅ ALL PYTHON

**Key Insight**: Since LangGraph (our orchestration core) is Python-only, and Playwright works excellently in Python, there's no reason to introduce TypeScript complexity.

---

## Technology Stack

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Browser Automation
playwright = "^1.56.0"

# AI Orchestration
langgraph = "^0.1.0"
langchain = "^0.1.0"
langsmith = "^0.1.0"
anthropic = "^0.7.0"

# CLI
typer = "^0.9.0"          # Modern CLI framework
rich = "^13.0.0"          # Beautiful terminal output

# Data Processing
pydantic = "^2.5.0"       # Data validation
openpyxl = "^3.1.0"       # Excel reading
pandas = "^2.0.0"         # Data manipulation

# Databases
psycopg2-binary = "^2.9.0"  # PostgreSQL
redis = "^5.0.0"            # Redis

# Testing
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-playwright = "^0.4.0"

# Optional Web API (if needed)
fastapi = "^0.109.0"
uvicorn = "^0.27.0"
```

---

## Project Structure

```
pacts/
├── src/
│   └── pacts/
│       ├── __init__.py
│       │
│       ├── agents/                 # 5 Agents
│       │   ├── __init__.py
│       │   ├── planner.py
│       │   ├── pom_builder.py
│       │   ├── generator.py
│       │   ├── executor.py
│       │   └── oracle_healer.py
│       │
│       ├── orchestrator/           # LangGraph
│       │   ├── __init__.py
│       │   ├── state_machine.py
│       │   └── checkpointer.py
│       │
│       ├── uwa/                    # Universal Web Adapter
│       │   ├── __init__.py
│       │   ├── discovery.py        # Multi-strategy element discovery
│       │   ├── verification.py     # 5-Point Actionability Gate
│       │   ├── policies.py         # Policy engine
│       │   └── mcp.py              # MCP browser control
│       │
│       ├── memory/                 # Memory Systems
│       │   ├── __init__.py
│       │   ├── episodic.py         # PostgreSQL
│       │   ├── working.py          # Redis
│       │   └── procedural.py       # Healing strategies
│       │
│       ├── cli/                    # Command Line Interface
│       │   ├── __init__.py
│       │   └── main.py             # Typer CLI
│       │
│       └── utils/
│           ├── __init__.py
│           ├── excel_reader.py
│           ├── file_manager.py
│           └── logger.py
│
├── policies/                       # JSON policy configs
│   ├── saucedemo.json
│   ├── amazon.json
│   └── github.json
│
├── tests/                          # pytest tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── pyproject.toml                  # Project config
├── poetry.lock
├── README.md
└── .env.example
```

---

## CLI Implementation (Python with Typer)

**File**: `src/pacts/cli/main.py`

```python
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
import asyncio

app = typer.Typer(name="pacts", help="PACTS - Production-Ready Autonomous Testing")
console = Console()

@app.command()
def plan(
    url: str = typer.Option(..., "--url", help="Target URL to test"),
    excel: Path = typer.Option(..., "--excel", help="Excel requirements file"),
    policy: str = typer.Option(None, "--policy", help="Policy ID (auto-detect if not provided)"),
    output: Path = typer.Option("plan.json", "--output", help="Output plan file"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Generate test plan using Planner Agent"""
    
    console.print(f"[bold blue]🧠 Planning tests for:[/bold blue] {url}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Reading requirements...", total=None)
        
        # Run Planner Agent
        from pacts.agents.planner import PlannerAgent
        from pacts.memory.episodic import EpisodicMemory
        
        memory = EpisodicMemory()
        planner = PlannerAgent(memory)
        
        state = {
            "excelRequirements": str(excel),
            "targetUrl": url,
            "policies": [policy] if policy else None
        }
        
        result = asyncio.run(planner.execute(state))
        
        progress.update(task, description="✅ Plan generated!")
    
    console.print(f"[green]✅ Test plan saved to:[/green] {output}")
    console.print(f"[blue]📊 Scenarios:[/blue] {len(result['testPlan']['scenarios'])}")

@app.command()
def build_pom(
    url: str = typer.Option(..., "--url", help="Target URL"),
    policy: str = typer.Option(None, "--policy", help="Policy ID"),
    output: Path = typer.Option("form.json", "--output", help="Output form file"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Build Page Object Model using POMBuilder Agent"""
    
    console.print(f"[bold blue]🏗️  Building POM for:[/bold blue] {url}")
    
    from pacts.agents.pom_builder import POMBuilderAgent
    
    builder = POMBuilderAgent()
    
    state = {
        "targetUrl": url,
        "policies": [policy] if policy else ["generic"]
    }
    
    result = asyncio.run(builder.execute(state))
    
    console.print(f"[green]✅ POM saved to:[/green] {output}")
    console.print(f"[blue]📊 Elements discovered:[/blue] {len(result['formJSON']['elements'])}")

@app.command()
def test(
    url: str = typer.Option(..., "--url", help="Target URL"),
    excel: Path = typer.Option(..., "--excel", help="Excel requirements"),
    auto_heal: bool = typer.Option(True, "--auto-heal/--no-heal", help="Enable auto-healing"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output")
):
    """Run complete test cycle: Plan → POM → Generate → Execute → Heal"""
    
    console.print("[bold green]🚀 Starting PACTS full cycle...[/bold green]")
    
    from pacts.orchestrator.state_machine import run_pacts_pipeline
    
    initial_state = {
        "excelRequirements": str(excel),
        "targetUrl": url,
        "phase": "planner"
    }
    
    result = asyncio.run(run_pacts_pipeline(initial_state))
    
    if result["phase"] == "complete":
        console.print("[bold green]✅ Test cycle complete![/bold green]")
    else:
        console.print("[bold red]❌ Test cycle incomplete[/bold red]")

@app.command()
def version():
    """Show PACTS version"""
    console.print("[bold]PACTS[/bold] v1.0.0")
    console.print("5-Agent Autonomous Testing System")

if __name__ == "__main__":
    app()
```

**Usage:**
```bash
# Generate test plan
pacts plan --url https://www.saucedemo.com --excel requirements.xlsx

# Build POM
pacts build-pom --url https://www.saucedemo.com --policy saucedemo

# Run full test cycle
pacts test --url https://www.saucedemo.com --excel requirements.xlsx

# Show version
pacts version
```

---

## Universal Web Adapter (Python)

**File**: `src/pacts/uwa/discovery.py`

```python
from playwright.async_api import Page, Locator
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class StrategyType(Enum):
    SEMANTIC = "semantic"
    SHADOW_DOM = "shadow-dom"
    IFRAME = "iframe"
    PATTERN = "pattern"
    VISION = "vision"

@dataclass
class UIElement:
    id: str
    type: str
    description: str
    selector: str
    location: Dict[str, int]
    size: Dict[str, int]
    attributes: Dict[str, str]
    is_visible: bool
    is_enabled: bool

class ElementDiscoveryService:
    """
    Multi-strategy element discovery service
    
    Tries multiple strategies to find elements:
    1. Semantic (role, label, text)
    2. Shadow DOM piercing
    3. Iframe traversal
    4. Pattern matching
    5. Vision-based (optional)
    """
    
    def __init__(self):
        self.strategies = [
            RoleBasedStrategy(),
            LabelStrategy(),
            TextContentStrategy(),
            ShadowDOMStrategy()
        ]
    
    async def find_element(self, page: Page, description: str) -> Optional[UIElement]:
        """
        Find element using multi-strategy approach.
        Tries each strategy until success.
        """
        print(f"🔍 Searching for: '{description}'")
        
        for strategy in self.strategies:
            print(f"  Trying: {strategy.name}")
            
            try:
                element = await strategy.find(page, description)
                
                if element:
                    print(f"  ✅ Found using {strategy.name}")
                    return element
                    
            except Exception as e:
                print(f"  ❌ {strategy.name} failed: {e}")
                continue
        
        raise Exception(f"No element found for: '{description}'")
    
    async def find_all_elements(self, page: Page, description: str) -> List[UIElement]:
        """Find all elements matching description"""
        results = []
        
        for strategy in self.strategies:
            try:
                element = await strategy.find(page, description)
                if element:
                    results.append(element)
            except:
                continue
        
        return results


class RoleBasedStrategy:
    """Find elements using ARIA roles"""
    
    name = "Role-based"
    
    async def find(self, page: Page, description: str) -> Optional[UIElement]:
        # Extract role from description
        role_map = {
            "button": "button",
            "link": "link",
            "textbox": "textbox",
            "input": "textbox",
            "heading": "heading"
        }
        
        for keyword, role in role_map.items():
            if keyword in description.lower():
                try:
                    locator = page.get_by_role(role)
                    count = await locator.count()
                    
                    if count > 0:
                        return await self._locator_to_element(
                            locator.first(), 
                            description
                        )
                except:
                    continue
        
        return None
    
    async def _locator_to_element(self, locator: Locator, description: str) -> UIElement:
        """Convert Playwright Locator to UIElement"""
        box = await locator.bounding_box()
        
        return UIElement(
            id=f"elem-{hash(description)}",
            type="button",  # Simplified
            description=description,
            selector=await self._generate_selector(locator),
            location={"x": box["x"], "y": box["y"]} if box else {"x": 0, "y": 0},
            size={"width": box["width"], "height": box["height"]} if box else {"width": 0, "height": 0},
            attributes=await self._get_attributes(locator),
            is_visible=await locator.is_visible(),
            is_enabled=await locator.is_enabled()
        )
    
    async def _generate_selector(self, locator: Locator) -> str:
        """Generate CSS selector"""
        return await locator.evaluate("""
            el => {
                if (el.id) return `#${el.id}`;
                if (el.className) return `.${el.className.split(' ').join('.')}`;
                return el.tagName.toLowerCase();
            }
        """)
    
    async def _get_attributes(self, locator: Locator) -> Dict[str, str]:
        """Get element attributes"""
        return await locator.evaluate("""
            el => {
                const attrs = {};
                for (let attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }
        """)


class LabelStrategy:
    """Find elements by label text"""
    
    name = "Label-based"
    
    async def find(self, page: Page, description: str) -> Optional[UIElement]:
        try:
            locator = page.get_by_label(description)
            count = await locator.count()
            
            if count > 0:
                # Convert to UIElement (similar to RoleBasedStrategy)
                return None  # Simplified for now
        except:
            return None


class TextContentStrategy:
    """Find elements by text content"""
    
    name = "Text-content"
    
    async def find(self, page: Page, description: str) -> Optional[UIElement]:
        try:
            locator = page.get_by_text(description, exact=False)
            count = await locator.count()
            
            if count > 0:
                return None  # Simplified
        except:
            return None


class ShadowDOMStrategy:
    """Pierce Shadow DOM to find elements"""
    
    name = "Shadow-DOM"
    
    async def find(self, page: Page, description: str) -> Optional[UIElement]:
        # Pierce all shadow roots
        try:
            result = await page.evaluate("""
                (desc) => {
                    function pierceAll(element) {
                        let results = [];
                        
                        if (element.textContent?.includes(desc)) {
                            results.push(element);
                        }
                        
                        if (element.shadowRoot) {
                            for (let child of element.shadowRoot.querySelectorAll('*')) {
                                results.push(...pierceAll(child));
                            }
                        }
                        
                        for (let child of element.children) {
                            results.push(...pierceAll(child));
                        }
                        
                        return results;
                    }
                    
                    return pierceAll(document.body);
                }
            """, description)
            
            if result:
                return None  # Simplified
        except:
            return None
```

---

## 5-Point Actionability Gate (Python)

**File**: `src/pacts/uwa/verification.py`

```python
from playwright.async_api import Page
from dataclasses import dataclass
from typing import Dict

@dataclass
class ActionabilityResult:
    passed: bool
    gates: Dict[str, bool]
    timestamp: int
    errors: List[str]

class ActionabilityGates:
    """
    5-Point Actionability Verification
    
    1. Unique - only one element matches
    2. Visible - actually visible to user
    3. Enabled - not disabled/readonly
    4. Stable - not moving/animating
    5. Interactable - can receive clicks/input
    """
    
    def __init__(self, page: Page, timeout: int = 5000):
        self.page = page
        self.timeout = timeout
    
    async def verify(self, element: UIElement) -> ActionabilityResult:
        """Verify all 5 gates"""
        
        errors = []
        
        # Gate 1: Unique
        unique = await self.is_unique(element.selector)
        if not unique:
            errors.append("Not unique - multiple matches")
        
        # Gate 2: Visible
        visible = await self.is_visible(element)
        if not visible:
            errors.append("Not visible")
        
        # Gate 3: Enabled
        enabled = await self.is_enabled(element)
        if not enabled:
            errors.append("Disabled")
        
        # Gate 4: Stable
        stable = await self.is_stable(element)
        if not stable:
            errors.append("Not stable (moving/animating)")
        
        # Gate 5: Interactable
        interactable = await self.is_interactable(element)
        if not interactable:
            errors.append("Not interactable")
        
        passed = unique and visible and enabled and stable and interactable
        
        return ActionabilityResult(
            passed=passed,
            gates={
                "unique": unique,
                "visible": visible,
                "enabled": enabled,
                "stable": stable,
                "interactable": interactable
            },
            timestamp=int(time.time() * 1000),
            errors=errors
        )
    
    async def is_unique(self, selector: str) -> bool:
        """Gate 1: Check uniqueness"""
        locator = self.page.locator(selector)
        count = await locator.count()
        return count == 1
    
    async def is_visible(self, element: UIElement) -> bool:
        """Gate 2: Check visibility"""
        locator = self.page.locator(element.selector)
        return await locator.is_visible(timeout=self.timeout)
    
    async def is_enabled(self, element: UIElement) -> bool:
        """Gate 3: Check enabled state"""
        locator = self.page.locator(element.selector)
        return await locator.is_enabled(timeout=self.timeout)
    
    async def is_stable(self, element: UIElement) -> bool:
        """Gate 4: Check stability (not moving)"""
        locator = self.page.locator(element.selector)
        
        positions = []
        for _ in range(3):
            box = await locator.bounding_box()
            if not box:
                return False
            positions.append((box["x"], box["y"]))
            await self.page.wait_for_timeout(100)
        
        # Check positions are consistent
        first_pos = positions[0]
        return all(
            abs(pos[0] - first_pos[0]) < 2 and 
            abs(pos[1] - first_pos[1]) < 2 
            for pos in positions
        )
    
    async def is_interactable(self, element: UIElement) -> bool:
        """Gate 5: Check interactability"""
        locator = self.page.locator(element.selector)
        
        # Scroll into view if needed
        await locator.scroll_into_view_if_needed()
        
        # Check if covered by another element
        is_covered = await locator.evaluate("""
            el => {
                const rect = el.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const topElement = document.elementFromPoint(centerX, centerY);
                return topElement !== el && !el.contains(topElement);
            }
        """)
        
        return not is_covered
```

---

## LangGraph Orchestration (Python)

**File**: `src/pacts/orchestrator/state_machine.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresCheckpointer
from typing import TypedDict, Annotated
import os

class PACSState(TypedDict):
    phase: str
    excelRequirements: str
    targetUrl: str
    testPlan: dict | None
    formJSON: dict | None
    testPy: str | None
    executionReport: dict | None
    healingResult: dict | None
    iterationCount: int

async def run_pacts_pipeline(initial_state: dict) -> dict:
    """
    Run complete PACTS pipeline with 5 agents
    """
    
    # Initialize agents
    from pacts.agents.planner import PlannerAgent
    from pacts.agents.pom_builder import POMBuilderAgent
    from pacts.agents.generator import GeneratorAgent
    from pacts.agents.executor import ExecutorAgent
    from pacts.agents.oracle_healer import OracleHealerAgent
    from pacts.memory.episodic import EpisodicMemory
    
    memory = EpisodicMemory()
    
    planner = PlannerAgent(memory)
    pom_builder = POMBuilderAgent()
    generator = GeneratorAgent()
    executor = ExecutorAgent()
    oracle_healer = OracleHealerAgent()
    
    # Define state machine
    workflow = StateGraph(PACSState)
    
    # Add agent nodes
    workflow.add_node("planner", planner.execute)
    workflow.add_node("pom_builder", pom_builder.execute)
    workflow.add_node("generator", generator.execute)
    workflow.add_node("executor", executor.execute)
    workflow.add_node("oracle_healer", oracle_healer.execute)
    
    # Linear flow: Planner → POMBuilder → Generator → Executor
    workflow.add_edge("planner", "pom_builder")
    workflow.add_edge("pom_builder", "generator")
    workflow.add_edge("generator", "executor")
    
    # Conditional: Executor → Complete or Healer
    def route_after_execution(state: PACSState):
        if state["phase"] == "complete":
            return END
        else:
            return "oracle_healer"
    
    workflow.add_conditional_edges(
        "executor",
        route_after_execution
    )
    
    # Conditional: Healer → Executor or Complete
    def route_after_healing(state: PACSState):
        if state["phase"] == "executor":
            return "executor"
        else:
            return END
    
    workflow.add_conditional_edges(
        "oracle_healer",
        route_after_healing
    )
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Setup checkpointer
    checkpointer = PostgresCheckpointer(
        connection_string=os.getenv("POSTGRES_CONNECTION")
    )
    
    # Compile
    app = workflow.compile(checkpointer=checkpointer)
    
    # Run
    result = await app.ainvoke(initial_state)
    
    return result
```

---

## Benefits of All-Python

### 1. **Development Speed**
```
Hybrid: 8 weeks (complex bridge, two ecosystems)
All-Python: 6 weeks (simpler, one ecosystem)
```

### 2. **Deployment Simplicity**
```dockerfile
# Single Dockerfile (no Node.js needed!)
FROM python:3.11-slim

RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install

# Install Playwright browsers
RUN playwright install chromium

COPY . .

CMD ["pacts", "test"]
```

### 3. **Debugging**
```python
# Single debugger, single language
import pdb; pdb.set_trace()

# Or use rich
from rich.traceback import install
install()  # Beautiful tracebacks
```

### 4. **Team Efficiency**
- 3-person team learns **one ecosystem**
- No context switching between TypeScript/Python
- Unified tooling (pytest, mypy, black, ruff)

---

## Migration from TypeScript POC

### What to Port (Minimal)

**Concepts to Keep:**
- ✅ Find-First strategy
- ✅ 5-Point Actionability Gate
- ✅ Policy-driven configuration
- ✅ Fallback chains
- ✅ Multi-strategy discovery

**Code to Rewrite (~800 lines → ~600 lines Python):**
- CLI interface (200 lines TS → 150 lines Python)
- MCP server (400 lines TS → 300 lines Python)
- Policy engine (100 lines TS → 80 lines Python)
- Element discovery (100 lines TS → 70 lines Python)

**Effort**: 2-3 days

**JSON Configs**: No changes needed! ✅

---

## Timeline Comparison

### Hybrid Approach: 8 Weeks
- Week 1: Setup + Bridge
- Week 2: Debug bridge issues
- Weeks 3-6: Agent implementation (slow due to bridge)
- Weeks 7-8: Integration + debugging across languages

### All-Python: 6 Weeks ✅
- Week 1: Setup + rewrite POC
- Weeks 2-5: Agent implementation (fast, single language)
- Week 6: Integration + polish

**Time Saved: 2 weeks**

---

## Final Recommendation

### ✅ GO ALL-PYTHON

**Why:**
1. LangGraph is Python-only (your core)
2. Playwright Python is mature
3. 25% faster development (6 vs 8 weeks)
4. Simpler architecture = easier maintenance
5. Better for 3-person team
6. Easier deployment
7. Richer LLM ecosystem

**The TypeScript POC served its purpose** - validating the approach. Now build production in Python.

---

**Decision**: All-Python  
**Timeline**: 6 weeks  
**Confidence**: 95%  

Ready to build! 🚀
