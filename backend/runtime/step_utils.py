"""
Step utilities for extracting consistent fields from step dictionaries.

Provides centralized helpers to handle LLM field name variations across the codebase.
"""

def get_step_target(step: dict) -> str:
    """
    Get target element name from step, checking all field variations.

    LLM outputs may use different field names:
    - "element": Preferred (current LLM outputs)
    - "target": Legacy field name
    - "intent": Used in some spec formats

    Args:
        step: Step dictionary from LLM or planner

    Returns:
        Target element name (normalized, lowercased, stripped)
        Empty string if no target field found

    Example:
        >>> step = {"element": "New", "action": "click"}
        >>> get_step_target(step)
        'new'

        >>> step = {"target": "Save Button", "action": "click"}
        >>> get_step_target(step)
        'save button'
    """
    return (
        step.get("element") or      # Preferred (current LLM outputs)
        step.get("target") or        # Legacy
        step.get("intent") or        # Some specs use this
        ""
    ).strip()


def get_step_action(step: dict) -> str:
    """
    Get action from step dictionary.

    Args:
        step: Step dictionary

    Returns:
        Action name (normalized, lowercased)
        "click" if no action specified (default)
    """
    return (step.get("action") or "click").lower().strip()


def get_step_value(step: dict) -> str:
    """
    Get value/input from step dictionary.

    Args:
        step: Step dictionary

    Returns:
        Value to input (empty string if none)
    """
    return (step.get("value") or "").strip()


def get_step_within(step: dict) -> str:
    """
    Get region scope hint from step dictionary.

    Args:
        step: Step dictionary

    Returns:
        Region scope (e.g., "App Launcher", "Dialog")
        Empty string if no scope specified
    """
    return (step.get("within") or "").strip()


def normalize_step_fields(step: dict) -> dict:
    """
    Normalize step dictionary to use consistent field names.

    Converts legacy field names to preferred names:
    - target → element
    - intent → element

    Args:
        step: Step dictionary (may have inconsistent fields)

    Returns:
        New step dictionary with normalized field names

    Example:
        >>> step = {"target": "New", "action": "click", "value": ""}
        >>> normalize_step_fields(step)
        {'element': 'New', 'action': 'click', 'value': ''}
    """
    normalized = step.copy()

    # Get target using helper (checks all variations)
    target = get_step_target(step)

    # Always use "element" as the canonical field
    if target:
        normalized["element"] = target
        # Remove legacy fields
        normalized.pop("target", None)
        normalized.pop("intent", None)

    return normalized
