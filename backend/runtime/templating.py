"""
PACTS v3.1s - Template Variable Substitution

Supports ${var} and ${var|default} syntax in test files.

Variable precedence (highest to lowest):
1. Dataset row (from CSV/JSONL/YAML)
2. CLI --vars overrides
3. Test vars: block
4. Step default (${var|default})

Special syntax:
- ${var} - Required variable (error if missing)
- ${var|default} - Optional variable with default value
- @env:VAR - Read from environment variable

Examples:
    go: "${base_url}/login"
    fill: { value: "${username}" }
    assert_text: { contains: "${assert_after|Signed in}" }
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import re
import os


class TemplateEngine:
    """Variable substitution engine for test templates."""

    # Regex patterns
    VAR_PATTERN = re.compile(r'\$\{([^}|]+)(?:\|([^}]+))?\}')  # ${var} or ${var|default}
    ENV_PATTERN = re.compile(r'@env:(\w+)')  # @env:VAR_NAME

    def __init__(self, variables: Optional[Dict[str, Any]] = None):
        """
        Initialize template engine with variable context.

        Args:
            variables: Dictionary of variables to use for substitution
        """
        self.variables = variables or {}

    def render(self, template: str, extra_vars: Optional[Dict[str, Any]] = None) -> str:
        """
        Render template string with variable substitution.

        Args:
            template: Template string with ${var} placeholders
            extra_vars: Additional variables for this render (highest precedence)

        Returns:
            Rendered string with variables substituted

        Raises:
            ValueError: If required variable is missing
        """
        # Merge variables (extra_vars has highest precedence)
        merged_vars = {**self.variables, **(extra_vars or {})}

        # First pass: Replace environment variables
        result = self._replace_env_vars(template)

        # Second pass: Replace template variables
        result = self._replace_template_vars(result, merged_vars)

        return result

    def _replace_env_vars(self, text: str) -> str:
        """
        Replace @env:VAR references with environment variable values.

        Args:
            text: Text containing @env:VAR patterns

        Returns:
            Text with environment variables substituted

        Raises:
            ValueError: If environment variable is not found
        """
        def replacer(match):
            env_var = match.group(1)
            value = os.getenv(env_var)
            if value is None:
                raise ValueError(f"Environment variable not found: {env_var}")
            return value

        return self.ENV_PATTERN.sub(replacer, text)

    def _replace_template_vars(self, text: str, variables: Dict[str, Any]) -> str:
        """
        Replace ${var} and ${var|default} patterns.

        Args:
            text: Text containing ${var} patterns
            variables: Variable dictionary

        Returns:
            Text with variables substituted

        Raises:
            ValueError: If required variable is missing
        """
        def replacer(match):
            var_name = match.group(1).strip()
            default_value = match.group(2)  # None if no default

            # Check if variable exists
            if var_name in variables:
                return str(variables[var_name])

            # Use default if provided
            if default_value is not None:
                return default_value.strip()

            # Error: required variable missing
            raise ValueError(f"Required template variable missing: {var_name}")

        return self.VAR_PATTERN.sub(replacer, text)

    def render_dict(self, obj: Dict[str, Any], extra_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Recursively render all string values in a dictionary.

        Args:
            obj: Dictionary with potential template strings
            extra_vars: Additional variables for this render

        Returns:
            Dictionary with all template variables substituted
        """
        result = {}
        for key, value in obj.items():
            if isinstance(value, str):
                result[key] = self.render(value, extra_vars)
            elif isinstance(value, dict):
                result[key] = self.render_dict(value, extra_vars)
            elif isinstance(value, list):
                result[key] = self.render_list(value, extra_vars)
            else:
                result[key] = value
        return result

    def render_list(self, lst: list, extra_vars: Optional[Dict[str, Any]] = None) -> list:
        """
        Recursively render all string values in a list.

        Args:
            lst: List with potential template strings
            extra_vars: Additional variables for this render

        Returns:
            List with all template variables substituted
        """
        result = []
        for item in lst:
            if isinstance(item, str):
                result.append(self.render(item, extra_vars))
            elif isinstance(item, dict):
                result.append(self.render_dict(item, extra_vars))
            elif isinstance(item, list):
                result.append(self.render_list(item, extra_vars))
            else:
                result.append(item)
        return result


def extract_required_vars(template: str) -> list[str]:
    """
    Extract all required variable names from a template.

    Args:
        template: Template string

    Returns:
        List of required variable names (without defaults)
    """
    required_vars = []
    for match in TemplateEngine.VAR_PATTERN.finditer(template):
        var_name = match.group(1).strip()
        default_value = match.group(2)

        # Only required if no default
        if default_value is None:
            required_vars.append(var_name)

    return required_vars


def validate_variables(template: str, variables: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Check if all required variables are provided.

    Args:
        template: Template string
        variables: Available variables

    Returns:
        Tuple of (is_valid, missing_vars)
    """
    required = extract_required_vars(template)
    missing = [var for var in required if var not in variables]
    return (len(missing) == 0, missing)


# Convenience functions
def render(template: str, variables: Dict[str, Any]) -> str:
    """
    Quick render function without creating engine instance.

    Args:
        template: Template string
        variables: Variables for substitution

    Returns:
        Rendered string
    """
    engine = TemplateEngine(variables)
    return engine.render(template)


def render_test_spec(spec: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Render an entire test specification with variables.

    Args:
        spec: Test specification dictionary (from YAML/JSON)
        variables: Variables for substitution

    Returns:
        Rendered test specification
    """
    engine = TemplateEngine(variables)
    return engine.render_dict(spec)
