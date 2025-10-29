from __future__ import annotations
import argparse, asyncio, json
from ..graph.state import RunState
from ..graph.build_graph import ainvoke_graph

def main():
    ap = argparse.ArgumentParser(description="PACTS CLI (Planner-only bootstrap)")
    ap.add_argument("--req", required=True, help="Requirement ID")
    ap.add_argument("--url", required=True, help="Target URL")
    ap.add_argument("--steps", required=True, nargs="+", help="Steps like 'Element@Region|action|value'")
    args = ap.parse_args()

    state = RunState(req_id=args.req, context={"url": args.url, "raw_steps": args.steps})
    result = asyncio.run(ainvoke_graph(state))
    print(json.dumps(result.model_dump(), indent=2))

if __name__ == "__main__":
    main()
