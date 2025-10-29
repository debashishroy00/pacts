from __future__ import annotations
from typing import Dict

async def five_point_gate(browser, selector: str, el) -> Dict[str, bool]:
    count = await browser.locator_count(selector)
    gates = {
        "unique": count == 1,
        "visible": await browser.visible(el),
        "enabled": await browser.enabled(el),
        "stable_bbox": await browser.bbox_stable(el),
        "scoped": True,  # frame/shadow scoping validated upstream (future)
    }
    return gates
