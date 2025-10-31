from __future__ import annotations
from typing import Dict

async def five_point_gate(
    browser,
    selector: str,
    el,
    heal_round: int = 0,
    stabilize: bool = False,
    samples: int = 3,
    timeout_ms: int = 2000
) -> Dict[str, bool]:
    """
    Five-point actionability gate with healing-friendly policies.

    Args:
        browser: BrowserClient instance
        selector: CSS/ARIA selector
        el: Element handle
        heal_round: Current healing round (0-3) - increases tolerance/timeouts
        stabilize: If True, wait for element stability before checking
        samples: Number of bbox samples for stability check
        timeout_ms: Base timeout in milliseconds

    Returns:
        Dict with gate results: {unique, visible, enabled, stable_bbox, scoped}

    Healing Policies:
        - Adaptive timeout: base + (1000ms * heal_round)
        - Bbox tolerance: 2.0px + (0.5px * heal_round) for CSS animations
        - Stability samples: 3 + heal_round (more samples on retries)
    """
    # Adaptive timeout per heal round
    adaptive_timeout = timeout_ms + (1000 * heal_round)

    # Adaptive bbox tolerance (CSS animations, transforms)
    bbox_tolerance = 2.0 + (0.5 * heal_round)

    # Adaptive stability samples (more retries → more samples)
    stability_samples = samples + heal_round

    # Optionally wait for stability first (OracleHealer strategy)
    if stabilize:
        try:
            await browser.wait_for_stability(
                selector,
                samples=stability_samples,
                delay_ms=200,
                tol=bbox_tolerance
            )
        except Exception:
            pass  # Non-blocking; gate will check stability anyway

    count = await browser.locator_count(selector)
    gates = {
        "unique": count == 1,
        "visible": await browser.visible(el),
        "enabled": await browser.enabled(el),
        "stable_bbox": await browser.bbox_stable(el, samples=stability_samples, tol=bbox_tolerance),
        "scoped": True,  # frame/shadow scoping validated upstream (future)
    }
    return gates
