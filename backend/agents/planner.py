from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from ..graph.state import RunState
from ..telemetry.tracing import traced
from ..runtime.step_utils import get_step_target
import json
import os
import re
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Look for .env in project root (two levels up from backend/agents)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Week 5: Context-aware planner (UX heuristics)
try:
    from ..runtime.heuristics.ux_patterns import UX_PATTERNS
    UX_TOGGLE = os.getenv("PACTS_PLANNER_UX_RULES", "true").lower() == "true"
except ImportError:
    UX_PATTERNS = []
    UX_TOGGLE = False

# Week 8 Phase B: Scope-first discovery
SCOPE_TOGGLE = os.getenv("PACTS_SCOPE_FEATURE", "true").lower() == "true"

def _extract_ordinal_info(element_name: str) -> Tuple[Optional[int], Optional[str], str]:
    """
    Extract ordinal position from element names like 'first video', 'second result', '3rd link'.

    Args:
        element_name: The element name from the plan (e.g., "first video result")

    Returns:
        Tuple of (ordinal_index, element_type, cleaned_name)
        - ordinal_index: 0 for first, 1 for second, etc. None if no ordinal found
        - element_type: Extracted type (video, result, link, button) or None
        - cleaned_name: Element name with ordinal removed

    Examples:
        "first video result" → (0, "video", "result")
        "second link" → (1, "link", "")
        "3rd button" → (2, "button", "")
        "Login button" → (None, "button", "Login")
    """
    if not element_name:
        return None, None, element_name

    element_lower = element_name.lower().strip()

    # Ordinal patterns: first, second, third, 1st, 2nd, 3rd, 4th, etc.
    ordinal_patterns = {
        r'\bfirst\b': 0,
        r'\bsecond\b': 1,
        r'\bthird\b': 2,
        r'\bfourth\b': 3,
        r'\bfifth\b': 4,
        r'\b1st\b': 0,
        r'\b2nd\b': 1,
        r'\b3rd\b': 2,
        r'\b(\d+)(?:th|st|nd|rd)\b': None,  # Will extract number
    }

    ordinal_index = None
    for pattern, index in ordinal_patterns.items():
        match = re.search(pattern, element_lower)
        if match:
            if index is None:  # Numeric pattern (4th, 5th, etc.)
                ordinal_index = int(match.group(1)) - 1  # Convert 1-based to 0-based
            else:
                ordinal_index = index
            # Remove the ordinal from the element name
            element_lower = re.sub(pattern, '', element_lower).strip()
            break

    # Extract element type keywords (video, result, link, button, item, etc.)
    type_keywords = {
        'video', 'result', 'link', 'button', 'item', 'card', 'tile',
        'article', 'post', 'comment', 'image', 'thumbnail', 'product',
        'option', 'choice', 'row', 'column', 'entry'
    }

    element_type = None
    for keyword in type_keywords:
        if re.search(rf'\b{keyword}s?\b', element_lower):  # Match singular or plural
            element_type = keyword
            # Remove the type keyword from cleaned name
            element_lower = re.sub(rf'\b{keyword}s?\b', '', element_lower).strip()
            break

    # Clean up remaining text
    cleaned_name = element_lower.strip()

    return ordinal_index, element_type, cleaned_name


def _normalize_hitl_actions(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-processor safety net: Normalize obvious 2FA/CAPTCHA/verification steps to "wait" action.

    Prevents LLM from emitting "click" on verification banners/labels.
    Rewrites any step with 2FA-related keywords to use action="wait".

    Args:
        spec: PACTS JSON specification

    Returns:
        Normalized specification with HITL steps corrected
    """
    twofa_tokens = {
        "2fa", "mfa", "otp", "verify", "verification", "authenticator",
        "security key", "email code", "sms", "captcha", "one-time",
        "multi-factor", "two-factor", "security code"
    }

    for tc in spec.get("testcases", []):
        for step in tc.get("steps", []):
            # Check if step target/element or value contains 2FA-related keywords (check both fields)
            target_text = (step.get("target", "") + " " + step.get("element", "") + " " + str(step.get("value", ""))).lower()

            # If this looks like a 2FA/verification step but isn't already "wait", fix it
            if any(token in target_text for token in twofa_tokens):
                if step.get("action") != "wait":
                    original_action = step.get("action")
                    step["action"] = "wait"
                    step["value"] = "manual"
                    step["outcome"] = "human_completes_verification"
                    print(f"[Planner] Normalized HITL step: '{step.get('target')}' ({original_action} → wait)")

    return spec


def _add_region_hints(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-processor: Add "within" hints for region-scoped discovery.

    Salesforce-specific: After clicking "App Launcher", subsequent navigation steps
    should be scoped to the "App Launcher" dialog region.

    Args:
        spec: PACTS JSON specification

    Returns:
        Specification with "within" metadata added to relevant steps
    """
    for tc in spec.get("testcases", []):
        steps = tc.get("steps", [])
        in_app_launcher = False

        for i, step in enumerate(steps):
            # Use shared helper to get target (handles target/element/intent variations)
            target = get_step_target(step).lower()

            # Detect App Launcher click
            if step.get("action") == "click" and "app launcher" in target:
                in_app_launcher = True
                print(f"[Planner] Detected App Launcher click at step {i}")
                continue

            # Add "within" hint for subsequent navigation in App Launcher
            if in_app_launcher and step.get("action") == "click":
                # Common Salesforce object names that appear in App Launcher
                if any(obj in target for obj in ["accounts", "contacts", "leads", "opportunities", "cases"]):
                    step["within"] = "App Launcher"
                    print(f"[Planner] ⭐ Added within='App Launcher' to step {i}: target='{target}' element='{step.get('element')}'")

                # Stop scoping after clicking an object (navigates away from launcher)
                if any(obj in target for obj in ["accounts", "contacts"]):
                    in_app_launcher = False

    return spec


def _enrich_steps_with_ux_patterns(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Week 5: Context-aware planner (UX heuristics).

    Enrich steps with UX pattern metadata (waits, scoping, gates) based on declarative rules.
    This is a lightweight post-processor that adds context-aware hints without heavy logic.

    Args:
        spec: PACTS JSON specification

    Returns:
        Specification with UX pattern enrichments added to steps
    """
    if not UX_TOGGLE or not UX_PATTERNS:
        return spec

    for tc in spec.get("testcases", []):
        steps = tc.get("steps", [])
        prev_step_target = None

        for i, step in enumerate(steps):
            target = get_step_target(step).lower()
            action = step.get("action", "").lower()

            # Build simple matching context
            match_context = {
                "action": action,
                "target": step.get("target", ""),
                "target_lower": target,
                "prev_step_has": prev_step_target,
            }

            # Apply matching rules
            for rule in UX_PATTERNS:
                matched = True
                for key, expected in rule.get("when", {}).items():
                    actual = match_context.get(key)

                    if key == "contains_text":
                        if expected.lower() not in target:
                            matched = False
                    elif key == "prev_step_has":
                        if not prev_step_target or expected.lower() not in prev_step_target.lower():
                            matched = False
                    elif actual != expected:
                        matched = False

                if matched:
                    # Apply enrichments from rule
                    for enrich_key, enrich_value in rule.get("adds", {}).items():
                        if enrich_key not in step or not step[enrich_key]:
                            step[enrich_key] = enrich_value

                    print(f"[Planner] 🎯 Applied UX rule '{rule['id']}' to step {i}: {step.get('target')}")

            prev_step_target = step.get("target")

    return spec


def apply_ux_rules(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Week 8 Phase B: Apply scope-first UX rules to plan steps.

    Automatically injects scopes, waits, and gates for common UX patterns:
    - Modal/dialog patterns (New, Create, App Launcher)
    - Dropdown selection (combobox listbox pattern)
    - Tab navigation (tab → tabpanel activation)

    Args:
        plan: List of plan steps (output from suite processing)

    Returns:
        Plan with scope metadata added to relevant steps

    Emits:
        [PLANNER] rule=<name> action=<a> scope=<s>
    """
    from ..utils import ulog

    if not plan or not SCOPE_TOGGLE:
        return plan

    def _next_is_form(i: int) -> bool:
        """Check if next step is a form interaction"""
        return i + 1 < len(plan) and plan[i + 1].get("action") in {"type", "fill", "select", "click"}

    def _next_is_option_click(i: int) -> bool:
        """Check if next step is an option selection"""
        return i + 1 < len(plan) and plan[i + 1].get("meta", {}).get("pattern") == "option-select"

    for i, step in enumerate(plan):
        action = step.get("action", "").lower()
        element = step.get("element", "").lower()

        # Rule 1: open_modal_scope
        # After clicking New/Create/App Launcher, scope subsequent form interactions to dialog
        if action == "click" and any(trigger in element for trigger in ["new", "create", "app launcher"]):
            if _next_is_form(i):
                # Inject scope metadata for next step(s)
                step.setdefault("scope", {"type": "dialog", "name": step.get("element")})
                step.setdefault("wait", "scope_ready")
                ulog.emit("PLANNER", rule="open_modal_scope", action="click", scope=step["scope"]["type"])
                print(f"[Planner] 🎯 Applied Phase B rule 'open_modal_scope' to step {i}: {step.get('element')}")

        # Rule 2: dropdown_selection
        # After clicking dropdown/combobox, scope to listbox and wait for options
        elif action == "click" and any(role in element for role in ["combobox", "dropdown"]):
            if _next_is_option_click(i):
                step.setdefault("scope", {"type": "listbox", "name": "-"})
                step.setdefault("wait", "listbox_ready")
                ulog.emit("PLANNER", rule="dropdown_selection", action="click", scope="listbox")
                print(f"[Planner] 🎯 Applied Phase B rule 'dropdown_selection' to step {i}: {step.get('element')}")

        # Rule 3: tab_navigation
        # After clicking tab, scope to active tabpanel
        elif action == "click" and "tab" in element and element != "tabpanel":
            if _next_is_form(i):
                step.setdefault("scope", {"type": "tabpanel", "name": "-"})
                step.setdefault("wait", "tabpanel_ready")
                ulog.emit("PLANNER", rule="tab_navigation", action="click", scope="tabpanel")
                print(f"[Planner] 🎯 Applied Phase B rule 'tab_navigation' to step {i}: {step.get('element')}")

    return plan


async def parse_natural_language_to_json(natural_language_text: str, url: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Claude LLM to convert natural language test description into PACTS JSON format.

    Args:
        natural_language_text: Plain English test description from business analyst
        url: Optional target URL (can be extracted from text if not provided)

    Returns:
        PACTS-compatible JSON specification with testcases, steps, data, outcomes
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "Anthropic SDK required for natural language parsing.\n"
            "Install with: pip install anthropic"
        )

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable required for natural language parsing.\n"
            "Set it with: export ANTHROPIC_API_KEY=your_key_here"
        )

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are a test automation expert specializing in converting natural language test descriptions into structured JSON format for the PACTS (Production-Ready Autonomous Context Testing System).

Your task is to parse natural language test descriptions and output valid PACTS JSON specifications.

PACTS JSON FORMAT:
{
  "req_id": "REQ-XXX-001",
  "url": "https://example.com",
  "suite_meta": {
    "app": "Application Name",
    "area": "Feature Area",
    "priority": "P0/P1/P2",
    "description": "Brief description"
  },
  "testcases": [
    {
      "tc_id": "TC-XXX-001",
      "title": "Test case title",
      "steps": [
        {
          "id": "S1",
          "action": "fill|click|select|press|check|uncheck|hover|focus",
          "target": "Element name (e.g., Username, Login button)",
          "value": "{{variableName}}" or "literal value",
          "outcome": "expected_result"
        }
      ],
      "data": [
        {
          "row_id": "D1",
          "variableName": "value"
        }
      ]
    }
  ]
}

ACTION TYPES:
You MUST choose from: ["navigate", "fill", "click", "press", "select", "check", "uncheck", "hover", "focus", "wait"]

- fill: Fill input fields
- click: Click buttons/links
- select: Select dropdown options
- press: Press keyboard keys
- check/uncheck: Toggle checkboxes
- hover: Hover over elements
- focus: Focus on elements
- wait: Wait for manual human intervention (HITL - Human-in-the-Loop)

CRITICAL WAIT ACTION RULES:
Use "wait" action ONLY when user must perform an out-of-band manual step.
Common wait scenarios: 2FA, MFA, OTP, email verification, SMS codes, authenticator apps, security keys, CAPTCHA.

If natural language includes ANY of these keywords:
  {verify, 2FA, MFA, OTP, code, verification, authenticator, security key, email code, SMS, CAPTCHA}

You MUST emit:
  {
    "action": "wait",
    "target": "2FA Verification" (or appropriate description),
    "value": "manual",
    "outcome": "human_completes_verification"
  }

NEVER try to "click" on verification prompts, banners, or labels like:
  ❌ "Click 2FA Verification"
  ❌ "Click Verify Your Identity"
  ❌ "Click Enter verification code"

Instead emit:
  ✅ {"action": "wait", "target": "2FA Verification", "value": "manual"}

OUTCOME TYPES:
- field_populated: Input field filled
- button_text_changes:NewText
- navigates_to:PageName
- page_contains_text:ExpectedText
- element_visible:ElementName
- element_hidden:ElementName

EXTRACTION RULES:
1. Extract URL from text or use provided URL parameter
2. Identify test steps with actions (fill, click, etc.)
3. Extract test data and parameterize with {{variable}} syntax
4. Infer expected outcomes from context
5. Generate unique IDs (REQ-XXX-001, TC-XXX-001, S1, S2, etc.)
6. Group related steps into logical testcases

TARGET NAMING RULES (CRITICAL FOR DISCOVERY):
1. Use EXACT element text from UI (e.g., "Login" not "Login button")
2. For buttons: Use button text only (e.g., "Submit", "Continue", "Add to cart")
3. For input fields: Use label or placeholder text (e.g., "Username", "Email")
4. For product actions: Use format "ProductName" in value field, "Add to cart" as target
5. Avoid adding element type suffixes ("button", "field", "icon", "link")
6. Keep targets concise - don't combine product name with action

PRESS ACTION RULE (CRITICAL):
- When pressing Enter on an input field, use the SAME target as the previous fill step
- Example: If step 1 fills "Search", step 2 pressing Enter should ALSO use target="Search"
- Do NOT create a new target for press actions on the same element

EXAMPLES:
✅ GOOD:
  Step 1: action="fill", target="Search", value="query"
  Step 2: action="press", target="Search", value="Enter"

❌ BAD:
  Step 1: action="fill", target="Search box", value="query"
  Step 2: action="press", target="Enter key", value="Enter"

✅ GOOD: target="Add to cart", value="Sauce Labs Backpack"
❌ BAD: target="Sauce Labs Backpack Add to Cart"

✅ GOOD: target="Login"
❌ BAD: target="Login button"

✅ GOOD: target="Continue"
❌ BAD: target="Continue Button"

✅ GOOD (HITL for 2FA):
  Step 3: action="click", target="Log In"
  Step 4: action="wait", target="2FA Verification", value="manual"
  Step 5: action="click", target="Accounts"

✅ GOOD (HITL for CAPTCHA):
  Step 2: action="wait", target="CAPTCHA", value="manual"

Return ONLY valid JSON, no explanations."""

    user_prompt = f"""Convert this natural language test description into PACTS JSON format:

TEST DESCRIPTION:
{natural_language_text}

{f"TARGET URL: {url}" if url else ""}

Return ONLY the JSON specification, no markdown code blocks or explanations."""

    # Use Haiku 3.5 for MVP phase (cost-effective, fast)
    # Upgrade to Sonnet later for complex test scenarios
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",  # Haiku 3.5: 80% cheaper than Sonnet
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    # Extract JSON from response
    response_text = message.content[0].text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first and last line (```json and ```)
        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text

    # Parse JSON
    try:
        parsed_json = json.loads(response_text)
        # Post-processor safety net: normalize obvious 2FA/verification steps to "wait" action
        parsed_json = _normalize_hitl_actions(parsed_json)
        # Post-processor: add region hints for Salesforce App Launcher navigation
        parsed_json = _add_region_hints(parsed_json)
        # Week 5: Context-aware planner - enrich with UX pattern metadata
        parsed_json = _enrich_steps_with_ux_patterns(parsed_json)
        return parsed_json
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Claude returned invalid JSON: {e}\n"
            f"Response: {response_text[:500]}"
        )


def parse_steps(raw_steps: List[str]) -> List[Dict[str, Any]]:
    out = []
    for line in raw_steps:
        parts = [p.strip() for p in line.split("|")]
        er = parts[0].split("@")
        element = er[0].strip()
        region = er[1].strip() if len(er) > 1 else None
        action = parts[1].strip().lower() if len(parts) > 1 else "click"
        value = parts[2].strip().strip('"') if len(parts) > 2 else None
        out.append({
            "intent": f"{element}@{region}" if region else element,
            "element": element,
            "region": region,
            "action": action,
            "value": value
        })
    return out

@traced("planner")
async def run(state: RunState) -> RunState:
    """
    Planner Agent v3: Intelligent plan generation with LLM-powered natural language parsing.

    Priority:
    1. context["natural_language"] - LLM parses plain English into JSON (NEW)
    2. context["suite"] - Structured JSON format (testcases, steps, data, outcomes)
    3. context["raw_steps"] - Legacy pipe-delimited strings

    Outputs:
    - state.context["intents"] - Parsed step intents for POMBuilder
    - state.context["plan"] - Initial plan structure (updated by POMBuilder with selectors)
    - state.plan - Unified plan location
    """
    # PRIORITY 1: Natural language mode (LLM-powered)
    natural_language_text = state.context.get("natural_language")
    if natural_language_text:
        print("[Planner] Using LLM to parse natural language into JSON...")
        url = state.context.get("url")
        suite = await parse_natural_language_to_json(natural_language_text, url)
        print(f"[Planner] LLM generated spec: {suite.get('req_id', 'N/A')}")
        # Store the generated JSON spec
        state.context["suite"] = suite
        # Extract URL from LLM-generated suite if not provided by user
        if not state.context.get("url") and suite.get("url"):
            state.context["url"] = suite["url"]
            print(f"[Planner] Extracted URL from LLM output: {suite['url']}")
        # Fall through to suite processing below

    # PRIORITY 2: Authoritative suite JSON mode
    suite = state.context.get("suite")
    if suite:
        plan = []
        for tc in suite.get("testcases", []):
            data_rows = tc.get("data", [{}]) or [{}]  # Default to single row if no data
            for row in data_rows:
                for st in tc.get("steps", []):
                    element_name = st.get("target")

                    # v3.1s: Extract ordinal information from element name
                    ordinal_index, element_type, cleaned_name = _extract_ordinal_info(element_name)

                    step = {
                        "element": element_name,  # Keep original for logging
                        "action": st.get("action", "click").lower(),
                        "value": st.get("value", ""),
                        "expected": st.get("outcome"),
                        "within": st.get("within"),  # Region scope hint (added by _add_region_hints)
                        "meta": {"source": "planner_v2", "testcase": tc.get("id")}
                    }

                    # v3.1s: Add ordinal metadata if detected
                    if ordinal_index is not None:
                        step["ordinal"] = ordinal_index
                        if element_type:
                            step["element_type"] = element_type
                        if cleaned_name:
                            step["element_hint"] = cleaned_name  # Additional context for discovery
                        print(f"[Planner] 🎯 Detected ordinal: '{element_name}' → index={ordinal_index}, type={element_type}, hint='{cleaned_name}'")

                    # Bind template variables from data row (e.g., {{username}} → "testuser")
                    if step["value"]:
                        for var_name, var_value in row.items():
                            placeholder = f"{{{{{var_name}}}}}"
                            step["value"] = step["value"].replace(placeholder, str(var_value))

                        # Substitute {timestamp} with Unix timestamp for unique data
                        if "{timestamp}" in step["value"]:
                            import time
                            step["value"] = step["value"].replace("{timestamp}", str(int(time.time())))

                    plan.append(step)

        # Phase B: Apply scope-first UX rules
        plan = apply_ux_rules(plan)

        # Set intents for POMBuilder compatibility
        state.context["intents"] = [
            {
                "intent": step["element"],
                "element": step["element"],
                "action": step["action"],
                "value": step["value"],
                "expected": step.get("expected")
            }
            for step in plan
        ]

        # Write to context["plan"] (state.plan is a read-only property that reads this)
        state.context["plan"] = plan
        return state

    # PHASE 1: Legacy raw_steps fallback
    raw_steps = state.context.get("raw_steps", [])
    if not raw_steps:
        raise ValueError("Planner requires context['suite'] (v2) or context['raw_steps'] (v1)")

    intents = parse_steps(raw_steps)
    state.context["intents"] = intents
    return state
