# 🚀 PACTS 2-Week Enterprise Implementation Plan

**Version**: 1.0
**Date**: 2025-11-01
**Goal**: Achieve 85-95% success rate on Salesforce and enterprise applications
**Effort**: 80 hours (2 weeks, 1 developer)
**Confidence**: 80% ⭐⭐⭐⭐

---

## 📋 Executive Summary

PACTS currently achieves **100% success** on simple websites but **fails on enterprise apps** like Salesforce due to:
1. ❌ Using wrong Playwright APIs (`query_selector` instead of `locator`)
2. ❌ Shadow DOM strategy is a stub (returns `None`)
3. ❌ No iframe handling
4. ❌ No Salesforce-specific patterns

**Solution**: Refactor to use Playwright's native Shadow DOM piercing and add enterprise patterns.

**Expected Outcome**: 85-95% Salesforce success rate with local Playwright (no MCP needed).

---

## 🎯 Implementation Strategy

### **Core Principles**

1. **Use Native Playwright APIs** - No MCP dependencies
2. **Shadow DOM Auto-Piercing** - `locator()` API pierces automatically
3. **iframe Context Handling** - `frame_locator()` for cross-frame operations
4. **Salesforce-Specific Patterns** - Pre-built patterns for common scenarios
5. **Defensive Waiting** - Always wait for Lightning/spinners to settle

### **Why Not MCP?**

- ❌ Connection bugs (documented in PACTS codebase)
- ❌ False positives (tests report pass but nothing happened)
- ❌ Still in preview (v0.9.0 for CDP, v1.0 with regressions)
- ❌ Separate browser instance (context mismatch)
- ✅ Local Playwright handles Shadow DOM natively

---

## 📅 Week 1: Foundation & Core Capabilities

### **Day 1 (Monday): API Refactoring**

**Duration**: 8 hours
**Goal**: Switch from `query_selector()` to `locator()` API

#### **Morning (4h): Refactor BrowserClient**

**File**: `backend/runtime/browser_client.py`

**Changes**:
1. Replace `ElementHandle` with `Locator`
2. Add `locator()` method with Shadow DOM piercing
3. Add `frame_locator()` for iframe support
4. Add multi-browser support (Chromium, Firefox, WebKit)

**Key Code**:
```python
from playwright.async_api import async_playwright, Browser, Page, Locator

class BrowserClient:
    """Manages persistent browser with Shadow DOM & iframe support."""

    async def launch(self):
        """Launch browser with multi-browser support."""
        self.pw = await async_playwright().start()

        # Multi-browser support
        browser_type = self.config.get("browser", "chromium")
        headless = self.config.get("headless", True)
        slow_mo = self.config.get("slow_mo", 0)

        if browser_type == "firefox":
            self.browser = await self.pw.firefox.launch(headless=headless, slow_mo=slow_mo)
        elif browser_type == "webkit":
            self.browser = await self.pw.webkit.launch(headless=headless, slow_mo=slow_mo)
        else:
            self.browser = await self.pw.chromium.launch(headless=headless, slow_mo=slow_mo)

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.context.set_default_timeout(30000)  # 30s for Salesforce
        self.page = await self.context.new_page()

    def locator(self, selector: str, **kwargs) -> Locator:
        """
        Get locator with automatic Shadow DOM piercing.

        Examples:
            locator("button")  # Simple
            locator("lightning-button >> button")  # Shadow DOM
            locator("text=Login")  # Text matching (pierces Shadow DOM)
            locator("role=button[name='Login']")  # Role-based (pierces Shadow DOM)
        """
        return self.page.locator(selector, **kwargs)

    def frame_locator(self, selector: str):
        """Get frame locator for iframe navigation."""
        return self.page.frame_locator(selector)

    async def find_by_role(self, role: str, pattern: Pattern) -> Optional[Locator]:
        """Find element by ARIA role (Shadow DOM aware)."""
        candidates = self.page.get_by_role(role)
        count = await candidates.count()

        for i in range(count):
            element = candidates.nth(i)
            text = await element.inner_text()

            if pattern.search(text):
                return element

        return None

    async def pierce_shadow(self, host_selector: str, shadow_selector: str) -> Optional[Locator]:
        """Explicitly pierce Shadow DOM using >> combinator."""
        combined = f"{host_selector} >> {shadow_selector}"
        loc = self.page.locator(combined)
        count = await loc.count()
        return loc if count > 0 else None
```

**Testing**:
```python
async def test_new_api():
    browser = BrowserClient({"headless": False})
    await browser.launch()
    await browser.goto("https://www.saucedemo.com")

    # New API works with Shadow DOM
    username = browser.locator("input#user-name")
    await username.fill("standard_user")

    print("✅ API refactoring successful!")
```

---

#### **Afternoon (4h): Update Discovery Strategies**

**File**: `backend/runtime/discovery.py`

**Changes**:
1. Update `_try_role_name()` to use Locator API
2. Update `_try_label()` to use `get_by_label()`
3. Update `_try_placeholder()` to use Locator
4. Add Shadow DOM awareness flags to metadata

**Key Code**:
```python
async def _try_role_name(browser, intent) -> Optional[Dict[str, Any]]:
    """Role-based discovery with Shadow DOM piercing."""
    name = (intent.get("element") or "").strip()
    action = (intent.get("action") or "").lower()

    if not name:
        return None

    normalized_name = normalize_text(name)
    role = "button" if action == "click" else None

    # Use Locator API (automatically pierces Shadow DOM!)
    loc = browser.page.get_by_role(role or "button", name=re.compile(re.escape(normalized_name), re.I))
    count = await loc.count()

    if count > 0:
        first = loc.first
        is_visible = await first.is_visible()

        if not is_visible:
            return None

        # Generate stable selector
        element_id = await first.get_attribute("id")
        if element_id:
            selector = f"#{element_id}"
        else:
            selector = f'[role="{role}"]'

            # Check if Lightning component
            tag = await first.evaluate("el => el.tagName.toLowerCase()")
            if tag.startswith("lightning-") or tag.startswith("c-"):
                selector = f"{tag} >> {selector}"

        return {
            "selector": selector,
            "score": 0.95,
            "meta": {
                "strategy": "role_name",
                "role": role,
                "shadow_safe": True,
                "normalized": normalized_name
            }
        }

    return None
```

---

### **Day 2 (Tuesday): Shadow DOM Strategy**

**Duration**: 8 hours
**Goal**: Implement comprehensive Shadow DOM handling

#### **Morning (4h): Shadow DOM Piercing Strategy**

**File**: `backend/runtime/shadow_dom.py` (NEW)

**Features**:
1. Automatic piercing via Locator API
2. Explicit `>>` combinator for complex nesting
3. Deep shadow search for edge cases
4. Salesforce Lightning component patterns

**Key Code**:
```python
"""Shadow DOM Handling for Enterprise Apps."""

from playwright.async_api import Page, Locator
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

SALESFORCE_SHADOW_HOSTS = [
    "lightning-input",
    "lightning-button",
    "lightning-combobox",
    "lightning-textarea",
    "lightning-checkbox",
    "c-*",  # Custom components
    "lwc-*",
]

class ShadowDOMStrategy:
    """Handles Shadow DOM piercing with multiple fallback strategies."""

    def __init__(self, page: Page):
        self.page = page

    # Strategy 1: Automatic Piercing (Recommended)
    async def find_by_text(self, text: str, exact: bool = False) -> Optional[Locator]:
        """Find element by text, automatically piercing Shadow DOM."""
        if exact:
            loc = self.page.get_by_text(text, exact=True)
        else:
            loc = self.page.get_by_text(text)

        count = await loc.count()
        if count > 0:
            logger.info(f"[Shadow] Found '{text}' via text piercing")
            return loc

        return None

    async def find_by_role_and_name(self, role: str, name: str) -> Optional[Locator]:
        """Find by ARIA role and accessible name (pierces Shadow DOM)."""
        loc = self.page.get_by_role(role, name=re.compile(re.escape(name), re.I))
        count = await loc.count()

        if count > 0:
            logger.info(f"[Shadow] Found role={role} name={name}")
            return loc

        return None

    # Strategy 2: Explicit Shadow Piercing
    async def pierce_lightning_component(self, component_type: str, inner_selector: str) -> Optional[Locator]:
        """Pierce Salesforce Lightning component explicitly."""
        selector = f"{component_type} >> {inner_selector}"
        loc = self.page.locator(selector)
        count = await loc.count()

        if count > 0:
            logger.info(f"[Shadow] Pierced {component_type} -> {inner_selector}")
            return loc

        return None

    async def pierce_nested_shadow(self, shadow_path: List[str]) -> Optional[Locator]:
        """Pierce multiple nested shadow roots."""
        selector = " >> ".join(shadow_path)
        loc = self.page.locator(selector)
        count = await loc.count()

        if count > 0:
            logger.info(f"[Shadow] Pierced nested path: {selector}")
            return loc

        return None

    # Strategy 3: Deep Shadow Search
    async def deep_search_by_attribute(self, attribute: str, value: str) -> Optional[Locator]:
        """Search ALL shadow roots for element with specific attribute."""
        selector = f'* >> [{attribute}="{value}"]'
        loc = self.page.locator(selector)
        count = await loc.count()

        if count > 0:
            logger.info(f"[Shadow] Deep search found [{attribute}={value}]")
            return loc

        return None

    async def deep_search_salesforce_component(self, target_text: str) -> Optional[Locator]:
        """Search all Salesforce Lightning components for target."""
        for host_pattern in SALESFORCE_SHADOW_HOSTS:
            for inner in ["button", "input", "a", "span"]:
                selector = f"{host_pattern} >> {inner}:has-text('{target_text}')"
                loc = self.page.locator(selector)
                count = await loc.count()

                if count > 0:
                    logger.info(f"[Shadow] Found in {host_pattern} >> {inner}")
                    return loc

        return None


# Discovery Integration
async def discover_in_shadow_dom(browser, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Shadow DOM discovery strategy for PACTS integration."""
    target = (intent.get("element") or "").strip()
    action = intent.get("action", "click")

    if not target:
        return None

    shadow = ShadowDOMStrategy(browser.page)

    # Strategy 1: Automatic text/role piercing
    if action == "click":
        loc = await shadow.find_by_text(target)
        if loc:
            return {
                "selector": f'text="{target}"',
                "score": 0.92,
                "meta": {
                    "strategy": "shadow_text_pierce",
                    "auto_pierce": True
                }
            }

        loc = await shadow.find_by_role_and_name("button", target)
        if loc:
            return {
                "selector": f'role=button[name="{target}"]',
                "score": 0.94,
                "meta": {"strategy": "shadow_role_pierce"}
            }

    # Strategy 2: Explicit Lightning piercing
    loc = await shadow.deep_search_salesforce_component(target)
    if loc:
        return {
            "selector": str(loc),
            "score": 0.88,
            "meta": {"strategy": "shadow_deep_lightning"}
        }

    return None
```

**Update discovery.py**:
```python
from .shadow_dom import discover_in_shadow_dom

# Replace stub
async def _try_shadow_pierce(browser, intent) -> Optional[Dict[str, Any]]:
    return await discover_in_shadow_dom(browser, intent)
```

---

#### **Afternoon (4h): Shadow DOM Testing**

**File**: `backend/tests/integration/test_shadow_dom.py`

```python
import pytest
from backend.runtime.browser_client import BrowserClient
from backend.runtime.shadow_dom import ShadowDOMStrategy

@pytest.mark.asyncio
async def test_shadow_dom_automatic_piercing():
    """Test Playwright automatic Shadow DOM piercing."""
    browser = BrowserClient({"headless": False})
    await browser.launch()

    # Test site with Shadow DOM
    await browser.goto("https://shop.polymer-project.org/")

    # Try automatic piercing
    shop_button = browser.page.get_by_text("SHOP")
    assert await shop_button.count() > 0, "Failed to pierce Shadow DOM"

    print("✅ Automatic Shadow DOM piercing works!")
    await browser.close()

@pytest.mark.asyncio
async def test_lightning_component_piercing():
    """Test Salesforce Lightning component piercing."""
    browser = BrowserClient({"headless": False})
    await browser.launch()

    # Navigate to Salesforce
    await browser.goto("https://login.salesforce.com")

    # Manual login for first time
    await browser.page.pause()

    # Test Lightning component
    shadow = ShadowDOMStrategy(browser.page)
    app_launcher = await shadow.pierce_lightning_component(
        "lightning-button-icon",
        "button"
    )

    assert app_launcher is not None, "Failed to pierce Lightning button"
    print("✅ Lightning component piercing works!")

    await browser.close()
```

---

### **Day 3 (Wednesday): iframe Handling**

**Duration**: 8 hours
**Goal**: Implement iframe support for Salesforce Visualforce

#### **Morning (4h): iframe Strategy Implementation**

**File**: `backend/runtime/iframe_handler.py` (NEW)

**Features**:
1. `frame_locator()` for iframe operations
2. Nested iframe navigation
3. Automatic frame detection
4. Salesforce Visualforce patterns

**Key Code**:
```python
"""iframe Handling for Enterprise Apps."""

from playwright.async_api import Page, FrameLocator
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class IframeStrategy:
    """Handles iframe navigation and element discovery."""

    def __init__(self, page: Page):
        self.page = page

    # Strategy 1: frame_locator (Recommended)
    def get_frame_locator(self, frame_selector: str) -> FrameLocator:
        """Get frame locator for iframe operations."""
        return self.page.frame_locator(frame_selector)

    async def find_in_frame(self, frame_selector: str, element_selector: str) -> Optional[FrameLocator]:
        """Find element within specific iframe."""
        frame = self.get_frame_locator(frame_selector)
        element = frame.locator(element_selector)
        count = await element.count()

        if count > 0:
            logger.info(f"[iframe] Found '{element_selector}' in '{frame_selector}'")
            return element

        return None

    # Strategy 2: Nested iframe Navigation
    def navigate_nested_frames(self, frame_path: List[str]) -> FrameLocator:
        """Navigate through nested iframes."""
        current = self.page.frame_locator(frame_path[0])

        for frame_selector in frame_path[1:]:
            current = current.frame_locator(frame_selector)

        return current

    # Strategy 3: Automatic Frame Detection
    async def find_in_any_frame(self, element_selector: str) -> Optional[Dict[str, Any]]:
        """Search for element across ALL iframes."""
        # Try main page first
        main_element = self.page.locator(element_selector)
        if await main_element.count() > 0:
            return {
                "frame_selector": "main",
                "element": main_element,
                "frame_path": []
            }

        # Try all frames
        frames = self.page.frames
        for frame in frames:
            if frame == self.page.main_frame:
                continue

            frame_name = frame.name
            if not frame_name:
                continue

            frame_selector = f'iframe[name="{frame_name}"]'
            frame_loc = self.page.frame_locator(frame_selector)
            element = frame_loc.locator(element_selector)

            if await element.count() > 0:
                logger.info(f"[iframe] Found in frame: {frame_selector}")
                return {
                    "frame_selector": frame_selector,
                    "element": element,
                    "frame_path": [frame_selector]
                }

        return None

    # Salesforce-Specific
    async def find_visualforce_frame(self) -> Optional[str]:
        """Detect Salesforce Visualforce iframe."""
        vf_patterns = [
            'iframe[name^="vf"]',
            'iframe[id^="vf"]',
            'iframe[src*="visualforce"]',
        ]

        for pattern in vf_patterns:
            if await self.page.locator(pattern).count() > 0:
                logger.info(f"[iframe] Found Visualforce: {pattern}")
                return pattern

        return None


# Discovery Integration
async def discover_in_iframe(browser, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """iframe discovery strategy for PACTS integration."""
    target = (intent.get("element") or "").strip()
    action = intent.get("action", "click")

    if not target:
        return None

    iframe_handler = IframeStrategy(browser.page)

    # Build selector
    if action == "click":
        selector = f'button:has-text("{target}")'
    elif action == "fill":
        selector = f'input[placeholder*="{target}"]'
    else:
        selector = f'text="{target}"'

    # Search all frames
    result = await iframe_handler.find_in_any_frame(selector)

    if result:
        frame_path = result["frame_path"]

        if frame_path:
            full_selector = " >> ".join(frame_path + [selector])
        else:
            full_selector = selector

        return {
            "selector": full_selector,
            "score": 0.87,
            "meta": {
                "strategy": "iframe_search",
                "frame": result["frame_selector"]
            }
        }

    return None
```

---

#### **Afternoon (4h): Update Discovery with iframe**

**File**: `backend/runtime/discovery.py`

```python
from .iframe_handler import discover_in_iframe

# Add to discover_selector() priority list
async def discover_selector(browser, intent) -> Optional[Dict[str, Any]]:
    # ... existing strategies ...

    # Priority 5: iframe search
    cand = await discover_in_iframe(browser, intent)
    if cand:
        return cand

    # Priority 6: Fallback
    for name in STRATEGIES[5:]:
        cand = await STRATEGY_FUNCS[name](browser, intent)
        if cand:
            return cand

    return None
```

---

### **Day 4 (Thursday): Salesforce Patterns**

**Duration**: 8 hours
**Goal**: Handle Salesforce-specific quirks

#### **Morning (4h): Salesforce Pattern Library**

**File**: `backend/runtime/salesforce_patterns.py` (NEW)

**Features**:
1. App Launcher navigation
2. Modal/dialog handling
3. Lightning spinner waiting
4. Form filling with Shadow DOM

**Key Code**:
```python
"""Salesforce-specific patterns and quirks."""

from playwright.async_api import Page, Locator
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

SALESFORCE_PATTERNS = {
    "App Launcher": {
        "activator": 'button[title*="App Launcher" i]',
        "dialog": 'role=dialog[name*="app launcher" i]',
        "search": 'role=combobox[name*="search" i]'
    },
    "Save": {
        "selectors": [
            'lightning-button >> button:has-text("Save")',
            'button[name="SaveEdit"]',
        ]
    },
    "Edit": {
        "selectors": [
            'lightning-button >> button:has-text("Edit")',
            'button[name="Edit"]',
        ]
    },
}

class SalesforcePatternHandler:
    """Handles Salesforce-specific UI patterns."""

    def __init__(self, page: Page):
        self.page = page

    async def open_app_launcher(self) -> bool:
        """Open Salesforce App Launcher."""
        activator = self.page.locator(SALESFORCE_PATTERNS["App Launcher"]["activator"])
        await activator.click()

        dialog = self.page.locator(SALESFORCE_PATTERNS["App Launcher"]["dialog"])
        await dialog.wait_for(state="visible", timeout=5000)

        logger.info("[Salesforce] App Launcher opened")
        return True

    async def navigate_to_object(self, object_name: str) -> bool:
        """Navigate to standard/custom object."""
        await self.open_app_launcher()

        dialog = self.page.locator(SALESFORCE_PATTERNS["App Launcher"]["dialog"])
        search = dialog.locator(SALESFORCE_PATTERNS["App Launcher"]["search"])

        await search.fill(object_name)
        await self.page.wait_for_timeout(500)

        object_locator = dialog.locator(f'role=link[name="{object_name}" i]')
        if await object_locator.count() > 0:
            await object_locator.first.click()
            logger.info(f"[Salesforce] Navigated to: {object_name}")
            return True

        return False

    async def wait_for_lightning_ready(self, timeout: int = 30000):
        """Wait for Salesforce Lightning to be fully loaded."""
        await self.page.wait_for_load_state("domcontentloaded")

        # Wait for Lightning framework
        await self.page.wait_for_function(
            "window.Sfdc && window.Sfdc.canvas",
            timeout=timeout
        )

        # Wait for spinners
        await self.wait_for_spinners_gone()
        await self.page.wait_for_load_state("networkidle")

        logger.info("[Salesforce] Lightning ready")

    async def wait_for_spinners_gone(self, timeout: int = 10000):
        """Wait for all loading spinners to disappear."""
        spinners = ['lightning-spinner', '.slds-spinner']

        for spinner_selector in spinners:
            spinner = self.page.locator(spinner_selector)
            if await spinner.count() > 0:
                await spinner.first.wait_for(state="hidden", timeout=timeout)

    async def fill_lightning_input(self, label: str, value: str):
        """Fill Lightning input field by label (Shadow DOM safe)."""
        input_locator = self.page.get_by_label(label)
        await input_locator.focus()
        await input_locator.fill(value)

        logger.info(f"[Salesforce] Filled '{label}' = '{value}'")

    async def click_action_button(self, action: str) -> bool:
        """Click standard action button (Save, Edit, etc.)."""
        if action in SALESFORCE_PATTERNS:
            pattern = SALESFORCE_PATTERNS[action]

            for selector in pattern["selectors"]:
                btn = self.page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    logger.info(f"[Salesforce] Clicked {action}")
                    return True

        return False


# Discovery Integration
async def discover_salesforce_pattern(browser, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Salesforce pattern matching for PACTS discovery."""
    target = (intent.get("element") or "").strip()

    if target in SALESFORCE_PATTERNS:
        pattern = SALESFORCE_PATTERNS[target]

        if target == "App Launcher":
            return {
                "selector": pattern["activator"],
                "score": 0.98,
                "meta": {"strategy": "salesforce_pattern"}
            }

        if "selectors" in pattern:
            return {
                "selector": pattern["selectors"][0],
                "score": 0.95,
                "meta": {
                    "strategy": "salesforce_pattern",
                    "fallbacks": pattern["selectors"][1:]
                }
            }

    return None
```

---

#### **Afternoon (4h): Executor Updates**

**File**: `backend/agents/executor.py`

```python
# Add Salesforce special selector handling

from backend.runtime.salesforce_patterns import SalesforcePatternHandler

async def _perform_action(browser, action: str, selector: str, value: Optional[str] = None) -> bool:
    """Execute action with Salesforce special handling."""

    # Handle special Salesforce selectors
    if selector.startswith("SALESFORCE_NAV:"):
        object_name = selector.split(":", 1)[1]
        sf = SalesforcePatternHandler(browser.page)
        return await sf.navigate_to_object(object_name)

    # Normal execution
    locator = browser.page.locator(selector)

    if action == "click":
        await locator.click(timeout=5000)
        return True
    elif action == "fill":
        await locator.fill(value, timeout=5000)
        return True
    # ... rest of actions ...
```

---

### **Day 5 (Friday): Integration & Testing**

**Duration**: 8 hours
**Goal**: Integrate all strategies and validate

#### **Full Day: End-to-End Testing**

**File**: `backend/tests/integration/test_salesforce_e2e.py`

```python
"""End-to-end Salesforce testing."""

import pytest
from backend.runtime.browser_client import BrowserClient
from backend.runtime.salesforce_patterns import SalesforcePatternHandler

@pytest.mark.asyncio
async def test_salesforce_complete_flow():
    """Test complete Salesforce workflow."""
    browser = BrowserClient({"headless": False, "slow_mo": 500})
    await browser.launch()

    # 1. Login
    await browser.goto("https://login.salesforce.com")
    await browser.locator("#username").fill("your-email@example.com")
    await browser.locator("#password").fill("your-password")
    await browser.locator("#Login").click()

    # 2. Wait for Lightning
    sf = SalesforcePatternHandler(browser.page)
    await sf.wait_for_lightning_ready()

    # 3. Navigate to Accounts
    success = await sf.navigate_to_object("Accounts")
    assert success, "Failed to navigate to Accounts"

    # 4. Click New
    success = await sf.click_action_button("New")
    assert success, "Failed to click New"

    # 5. Fill form (Shadow DOM piercing)
    await sf.fill_lightning_input("Account Name", "Test Account")

    # 6. Save
    save_btn = browser.page.get_by_role("button", name="Save")
    await save_btn.click()

    # 7. Wait for completion
    await sf.wait_for_spinners_gone()

    print("✅ Salesforce E2E test passed!")
    await browser.close()
```

---

## 📅 Week 2: Production Readiness

### **Day 6 (Monday): LangGraph Checkpointing**

**Duration**: 8 hours
**Goal**: Add state persistence for crash recovery

**File**: `backend/memory/postgres_checkpointer.py` (NEW)

```python
"""Postgres checkpointer for LangGraph state persistence."""

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import AsyncConnectionPool
import os
import logging

logger = logging.getLogger(__name__)

async def create_checkpointer():
    """Create Postgres checkpointer with automatic setup."""
    db_url = os.getenv("DATABASE_URL", "postgresql://pacts:pacts@localhost/pacts")

    # Create async connection pool
    pool = AsyncConnectionPool(db_url)

    # Initialize checkpointer
    checkpointer = PostgresSaver(pool)

    # Setup tables (idempotent)
    await checkpointer.setup()

    logger.info("[Checkpointer] Initialized Postgres checkpointer")
    return checkpointer
```

**File**: `backend/graph/build_graph.py` - Update

```python
from backend.memory.postgres_checkpointer import create_checkpointer

async def build_graph_with_persistence():
    """Build graph with state persistence."""
    g = StateGraph(RunState)

    # ... add all nodes and edges (existing code) ...

    # Add checkpointing
    checkpointer = await create_checkpointer()

    return g.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_wait"]  # Pause for HITL
    )

async def ainvoke_graph(state: RunState, thread_id: str = None) -> RunState:
    """Invoke graph with state persistence."""
    app = await build_graph_with_persistence()

    # Generate thread ID from req_id
    thread_id = thread_id or f"test-{state.req_id}"

    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": 100
    }

    return await app.ainvoke(state, config=config)
```

**Benefits**:
- ✅ Crash recovery - resume from last checkpoint
- ✅ HITL improvements - proper pause/resume
- ✅ Time travel debugging - inspect any step
- ✅ Cross-run memory - reuse login sessions

---

### **Day 7 (Tuesday): Multi-Browser Support**

**Already implemented in Day 1!**

**Configuration**:
```bash
# .env additions
BROWSER=chromium  # or firefox, webkit
HEADLESS=true
SLOW_MO=0
```

**Usage**:
```python
# Test with Firefox
browser = BrowserClient({"browser": "firefox", "headless": False})

# Test with WebKit (Safari)
browser = BrowserClient({"browser": "webkit"})
```

---

### **Days 8-9 (Wed-Thu): Reporting & Documentation**

**Day 8: Reporting**

1. **JUnit XML Output**
   ```python
   # pytest --junitxml=reports/junit.xml
   ```

2. **HTML Reports**
   ```python
   # pytest --html=reports/report.html
   ```

3. **Custom Report Generator**
   - Test execution summary
   - Screenshot gallery
   - Failure analysis

**Day 9: Documentation**

1. **API Documentation** - Docstrings for all public methods
2. **Architecture Diagrams** - Updated with new strategies
3. **Troubleshooting Guide** - Common issues and solutions
4. **Quick Start Guide** - 5-minute Salesforce testing setup

---

### **Day 10 (Friday): Final Validation**

**Morning: Run Full Test Suite**

1. Login flows (Standard, SSO, 2FA)
2. Object navigation (Accounts, Contacts, Opportunities)
3. CRUD operations (Create, Read, Update, Delete)
4. Complex forms (Multi-step, dependent fields)
5. Multi-page workflows (Quote-to-Cash)

**Afternoon: Performance Tuning**

1. Optimize selector strategies
2. Reduce unnecessary waits
3. Parallel test execution
4. Memory leak checks

---

## 📊 Success Metrics

Track these KPIs daily:

| Metric | Week 1 Target | Week 2 Target | How to Measure |
|--------|--------------|---------------|----------------|
| Shadow DOM Success | 70% | 95% | Run 20 Lightning components |
| iframe Success | 60% | 90% | Run 10 Visualforce pages |
| Salesforce Success | 50% | 85% | Run 30 common scenarios |
| Test Stability | 60% | 95% | 3 runs, same result |
| Avg Execution Time | <5s | <3s | Total time / step count |

---

## 🎯 Quick Reference Guides

### **Shadow DOM Cheat Sheet**

```python
# ✅ RECOMMENDED: Automatic piercing
await page.get_by_text("Login").click()  # Pierces Shadow DOM automatically!
await page.get_by_role("button", name="Save").click()  # Pierces Shadow DOM!

# ✅ GOOD: Explicit piercing
await page.locator("lightning-button >> button").click()

# ✅ GOOD: Nested shadow
await page.locator("lightning-card >> lightning-button >> button").click()

# ❌ AVOID: Old API (doesn't pierce)
await page.query_selector("button")  # Won't find Shadow DOM elements!
```

### **iframe Cheat Sheet**

```python
# ✅ RECOMMENDED: frame_locator
frame = page.frame_locator('iframe[name="vfFrame"]')
await frame.locator("button").click()

# ✅ GOOD: Nested frames
nested = page.frame_locator('iframe#outer').frame_locator('iframe#inner')
await nested.locator("button").click()

# ✅ GOOD: Combined iframe + Shadow DOM
frame = page.frame_locator('iframe[name="vf"]')
await frame.locator("lightning-button >> button").click()

# ❌ AVOID: Manual frame switching
```

### **Salesforce Pattern Cheat Sheet**

```python
from backend.runtime.salesforce_patterns import SalesforcePatternHandler

sf = SalesforcePatternHandler(page)

# Navigation
await sf.navigate_to_object("Accounts")
await sf.open_app_launcher()

# Form filling (Shadow DOM safe)
await sf.fill_lightning_input("Account Name", "Test Corp")

# Actions
await sf.click_action_button("Save")
await sf.click_action_button("Edit")

# Waiting
await sf.wait_for_lightning_ready()
await sf.wait_for_spinners_gone()
```

---

## ⚠️ Common Pitfalls & Solutions

### **Pitfall 1: Using query_selector() instead of locator()**
**Problem**: Shadow DOM elements not found
**Solution**: Replace all `query_selector()` with `locator()`

### **Pitfall 2: Not waiting for Salesforce spinners**
**Problem**: Intermittent failures, element not found
**Solution**: Always call `wait_for_lightning_ready()` after navigation

### **Pitfall 3: iframe context confusion**
**Problem**: Elements not found in iframes
**Solution**: Use `frame_locator()`, not manual frame switching

### **Pitfall 4: Hardcoded timeouts**
**Problem**: Tests fail on slow networks
**Solution**: Use Playwright auto-wait, set default timeout to 30s for Salesforce

### **Pitfall 5: Not scoping to dialogs**
**Problem**: Clicking wrong element (background vs modal)
**Solution**: Always scope to modal/dialog first
```python
modal = page.locator('role=dialog')
await modal.locator('button:has-text("Save")').click()
```

### **Pitfall 6: Assuming elements are immediately visible**
**Problem**: Lightning loads components dynamically
**Solution**: Use `wait_for()` before assertions
```python
await page.locator("#accountName").wait_for(state="visible")
```

---

## 📦 Deliverables Checklist

**Week 1:**
- [ ] Day 1: Refactored BrowserClient with Locator API
- [ ] Day 1: Updated discovery strategies
- [ ] Day 2: Shadow DOM strategy implementation
- [ ] Day 2: Shadow DOM test suite
- [ ] Day 3: iframe strategy implementation
- [ ] Day 3: iframe integration with discovery
- [ ] Day 4: Salesforce pattern library
- [ ] Day 4: Executor updates for special selectors
- [ ] Day 5: End-to-end integration tests

**Week 2:**
- [ ] Day 6: Postgres checkpointing implementation
- [ ] Day 6: Updated graph with persistence
- [ ] Day 7: Multi-browser configuration validated
- [ ] Day 8: JUnit XML and HTML reporting
- [ ] Day 9: Complete documentation update
- [ ] Day 10: Full validation suite passing at 85%+

---

## 🚀 Next Steps After 2 Weeks

### **If 85%+ Success Rate Achieved**
1. Move to production environment
2. Add more test coverage (edge cases)
3. Optimize performance (parallel execution)
4. Implement CI/CD pipeline enhancements
5. Add visual regression testing

### **If 70-84% Success Rate**
1. Identify specific failure patterns
2. Add more Salesforce-specific patterns
3. Consider ZeroStep AI for edge cases
4. Extend timeout for slow operations
5. Add retry logic for flaky scenarios

### **If <70% Success Rate**
1. Re-evaluate approach with detailed analysis
2. Consider commercial tools (ACCELQ, Copado)
3. Engage Salesforce testing consultants
4. Deep-dive into failed scenarios
5. Check if Salesforce org has custom security

---

## 📚 Resources & References

### **Documentation**
- **Playwright**: https://playwright.dev/python/docs/intro
- **Shadow DOM**: https://playwright.dev/python/docs/other-locators#css-matching-by-shadow-dom
- **iframes**: https://playwright.dev/python/docs/frames
- **Salesforce LWC**: https://developer.salesforce.com/docs/component-library/documentation/lwc/testing
- **LangGraph**: https://docs.langchain.com/langgraph

### **Tools**
- **Playwright Inspector**: `PWDEBUG=1 python script.py`
- **Salesforce DevTools**: Browser DevTools → Elements → Show Shadow DOM
- **LangSmith**: https://smith.langchain.com (for tracing)

### **Community**
- **Playwright Discord**: https://discord.gg/playwright
- **Salesforce Developers**: https://developer.salesforce.com/forums
- **PACTS GitHub Issues**: (for bug reports)

---

## 💡 Tips for Success

1. **Start Simple**: Test on one Salesforce org first, then expand
2. **Use Playwright Inspector**: `await page.pause()` for debugging
3. **Check Shadow DOM**: Use DevTools to verify Shadow DOM structure
4. **Validate Assumptions**: Don't trust claims - verify with tests
5. **Iterate Quickly**: Test each strategy immediately after implementation
6. **Document Failures**: Track which patterns fail and why
7. **Ask for Help**: Use Playwright Discord for complex issues

---

## 🎯 Critical Success Factors

1. ✅ **Use Locator API consistently** - Don't mix with query_selector
2. ✅ **Wait for Salesforce Lightning** - Always wait for spinners
3. ✅ **Test incrementally** - Validate each day's work before moving on
4. ✅ **Keep it simple** - Don't over-engineer, use Playwright's built-in features
5. ✅ **Measure progress** - Track KPIs daily
6. ✅ **Stay focused** - Complete Week 1 before adding extras

---

## ⏱️ Time Allocation Summary

| Activity | Hours | Percentage |
|----------|-------|------------|
| BrowserClient refactoring | 8 | 10% |
| Shadow DOM strategy | 8 | 10% |
| iframe strategy | 8 | 10% |
| Salesforce patterns | 8 | 10% |
| Integration & testing | 8 | 10% |
| Checkpointing | 8 | 10% |
| Multi-browser | 0 | 0% (done) |
| Reporting | 8 | 10% |
| Documentation | 8 | 10% |
| Validation | 8 | 10% |
| Buffer/Debugging | 8 | 10% |
| **Total** | **80** | **100%** |

---

## 🎓 Learning Outcomes

By the end of this plan, you will have:

1. ✅ Deep understanding of Playwright's Shadow DOM piercing
2. ✅ Expertise in iframe navigation strategies
3. ✅ Knowledge of Salesforce Lightning architecture
4. ✅ Production-ready test automation framework
5. ✅ LangGraph state persistence implementation
6. ✅ Enterprise testing best practices

---

## 📝 Final Notes

**Confidence Level**: 80% ⭐⭐⭐⭐

This plan is based on:
- ✅ Playwright official documentation
- ✅ Real-world Salesforce testing articles (2025)
- ✅ PACTS codebase analysis
- ✅ MCP failure analysis
- ✅ Industry best practices

**Risks**:
- ⚠️ 20% uncertainty due to untested Salesforce org specifics
- ⚠️ Possible edge cases not covered
- ⚠️ Custom Salesforce configurations might need adjustments

**Mitigation**:
- ✅ Incremental testing validates each step
- ✅ Fallback strategies for each approach
- ✅ Buffer time built into schedule

---

**Ready to start? Begin with Day 1: API Refactoring!** 🚀

*Last Updated: 2025-11-01*
*Version: 1.0*
*Author: Claude Code Implementation Team*
