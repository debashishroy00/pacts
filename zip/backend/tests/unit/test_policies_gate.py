import pytest
from pacts.backend.runtime.policies import five_point_gate

class FB:
    async def locator_count(self, selector): return 1
    async def visible(self, el): return True
    async def enabled(self, el): return True
    async def bbox_stable(self, el, samples=3, delay_ms=120, tol=2.0): return True

@pytest.mark.asyncio
async def test_five_point_gate_passes():
    gates = await five_point_gate(FB(), "#id", object())
    assert all(gates.values())
