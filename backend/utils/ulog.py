"""
Unified Logger for Week 8 EDR Structured Logging

Emits structured tags for metrics collection:
- [PROFILE] using=STATIC|DYNAMIC
- [DISCOVERY] strategy=... stable=✓|⚠ selector=...
- [CACHE] status=... selector=... strategy=...
- [READINESS] stage=... info=...
- [HEAL] upgraded=... note=... selector=...
- [RESULT] status=PASS|FAIL
"""

from datetime import datetime


def _sym_ok(flag: bool) -> str:
    """Convert boolean to checkmark/warning symbol."""
    return "✓" if flag else "⚠"


def emit(tag: str, **fields):
    """
    Emit a structured log line.

    Format: [TAG] k=v k=v ...

    Args:
        tag: Log tag (PROFILE, DISCOVERY, CACHE, etc.)
        **fields: Key-value pairs to log
    """
    parts = [f"[{tag.upper()}]"]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    print(" ".join(parts), flush=True)


def discovery(strategy: str, selector: str, stable: bool):
    """
    Log a discovery event.

    Args:
        strategy: Discovery strategy name (aria-label, name, placeholder, etc.)
        selector: CSS/XPath selector discovered
        stable: Whether selector is stable (attribute-based) or volatile (id/role)
    """
    emit("DISCOVERY",
         strategy=strategy,
         stable=_sym_ok(stable),
         selector=selector)


def cache_saved(selector: str, strategy: str):
    """
    Log a cache save event.

    Args:
        selector: Selector being cached
        strategy: Discovery strategy used
    """
    emit("CACHE", status="💾_SAVED", selector=selector, strategy=strategy)


def cache_skipped(selector: str, reason: str = "VOLATILE"):
    """
    Log a cache skip event.

    Args:
        selector: Selector NOT being cached
        reason: Why it was skipped (VOLATILE, etc.)
    """
    emit("CACHE", status="⏩_SKIPPED", reason=f"({reason})", selector=selector)


def profile(using: str, detail: str = ""):
    """
    Log a profile detection event.

    Args:
        using: Profile name (STATIC or DYNAMIC)
        detail: Optional detail about detection (URL pattern, framework, etc.)
    """
    emit("PROFILE", using=using, detail=detail or "-")


def readiness(stage: str, info: str = ""):
    """
    Log a readiness gate stage.

    Args:
        stage: Readiness stage (dom-idle, element-visible, app-ready-hook)
        info: Optional additional info
    """
    emit("READINESS", stage=stage, info=info or "-")


def heal_upgraded(selector: str, note: str = ""):
    """
    Log a heal upgrade event.

    Args:
        selector: New selector after healing
        note: Optional note about the upgrade
    """
    emit("HEAL", upgraded="selector", note=note, selector=selector)


def result(passed: bool):
    """
    Log a test result.

    Args:
        passed: Whether test passed (True) or failed (False)
    """
    emit("RESULT", status=("PASS" if passed else "FAIL"))
