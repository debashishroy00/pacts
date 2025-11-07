import os, re, json
from datetime import datetime
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.abspath(__file__))  # Project root directory
RUNS_DIR = os.path.join(ROOT, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

DISCOVERY_RE = re.compile(r"\[DISCOVERY\].*?stable=(?P<stable>✓|⚠).*?selector=(?P<selector>.+)$")
CACHE_SAVED_RE = re.compile(r"\[CACHE\].*?SAVED")
CACHE_SKIPPED_RE = re.compile(r"\[CACHE\].*?SKIPPED")
HEAL_RE = re.compile(r"\[HEAL\]")
PROFILE_RE = re.compile(r"\[PROFILE\].*?using=(?P<profile>STATIC|DYNAMIC)")
READINESS_RE = re.compile(r"\[READINESS\]")
PASS_RE = re.compile(r"\[RESULT\]\s*status=PASS")
FAIL_RE = re.compile(r"\[RESULT\]\s*status=FAIL")

def parse_log(path):
    stats = {
        "stable_selectors": 0,
        "volatile_selectors": 0,
        "cache_saved": 0,
        "cache_skipped": 0,
        "heal_events": 0,
        "profiles": Counter(),
        "readiness_events": 0,
        "passes": 0,
        "fails": 0,
    }
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = DISCOVERY_RE.search(line)
            if m:
                if m.group("stable") == "✓":
                    stats["stable_selectors"] += 1
                else:
                    stats["volatile_selectors"] += 1
            if CACHE_SAVED_RE.search(line):
                stats["cache_saved"] += 1
            if CACHE_SKIPPED_RE.search(line):
                stats["cache_skipped"] += 1
            if HEAL_RE.search(line):
                stats["heal_events"] += 1
            m = PROFILE_RE.search(line)
            if m:
                stats["profiles"][m.group("profile")] += 1
            if READINESS_RE.search(line):
                stats["readiness_events"] += 1
            if PASS_RE.search(line):
                stats["passes"] += 1
            if FAIL_RE.search(line):
                stats["fails"] += 1
    return stats

def collect():
    per_app = {}
    if not os.path.isdir(RUNS_DIR):
        return per_app, {}
    for app in sorted(os.listdir(RUNS_DIR)):
        app_dir = os.path.join(RUNS_DIR, app)
        if not os.path.isdir(app_dir):
            continue
        agg = defaultdict(int)
        profiles_counter = Counter()
        logs = [os.path.join(app_dir, p) for p in os.listdir(app_dir) if p.endswith(".log")]
        for lp in logs:
            s = parse_log(lp)
            for k, v in s.items():
                if k == "profiles":
                    profiles_counter.update(v)
                else:
                    agg[k] += v
        agg["profiles"] = dict(profiles_counter)
        agg["num_runs"] = len(logs)
        per_app[app] = dict(agg)
    overall = defaultdict(int)
    overall_profiles = Counter()
    for app, s in per_app.items():
        for k, v in s.items():
            if k == "profiles":
                overall_profiles.update(v)
            elif isinstance(v, int):
                overall[k] += v
    overall["profiles"] = dict(overall_profiles)
    return per_app, overall

def compute_metrics(overall):
    runs = max(overall.get("num_runs", 0), 1)
    total_assertions = overall.get("passes", 0) + overall.get("fails", 0)
    stable = overall.get("stable_selectors", 0)
    volatile = overall.get("volatile_selectors", 0)
    stable_ratio = (stable / max(stable + volatile, 1)) * 100.0
    cold_run_pass = (overall.get("passes", 0) / max(total_assertions, 1)) * 100.0
    avg_heal_rounds = overall.get("heal_events", 0) / runs
    return {
        "cold_run_pass_rate_pct": round(cold_run_pass, 1),
        "stable_selector_ratio_pct": round(stable_ratio, 1),
        "avg_heal_rounds_per_run": round(avg_heal_rounds, 2),
        "profiles_seen": overall.get("profiles", {}),
        "readiness_events": overall.get("readiness_events", 0),
        "num_runs": overall.get("num_runs", 0),
    }

def main():
    per_app, overall = collect()
    metrics = compute_metrics(overall)
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overall": metrics,
        "per_app": per_app,
    }
    md_lines = []
    md_lines.append("# Phase A Validation Summary\n")
    md_lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z\n")
    md_lines.append("## Overall Metrics (EDR)\n")
    md_lines.append(f"- Cold-run pass rate: {metrics['cold_run_pass_rate_pct']} %")
    md_lines.append(f"- Stable selector ratio: {metrics['stable_selector_ratio_pct']} %")
    md_lines.append(f"- Avg heal rounds per run: {metrics['avg_heal_rounds_per_run']}")
    md_lines.append(f"- Profiles seen: {', '.join([f'{k}:{v}' for k,v in metrics['profiles_seen'].items()]) or 'n/a'}")
    md_lines.append(f"- Readiness events: {metrics['readiness_events']}")
    md_lines.append(f"- Runs analyzed: {metrics['num_runs']}\n")
    md_lines.append("## Per App Breakdown\n")
    for app, s in per_app.items():
        md_lines.append(f"### {app}")
        md_lines.append(f"- Runs: {s.get('num_runs',0)}")
        md_lines.append(f"- Passes / Fails: {s.get('passes',0)} / {s.get('fails',0)}")
        st = s.get("stable_selectors",0)
        vt = s.get("volatile_selectors",0)
        ratio = round(st / max(st+vt,1)*100.0, 1)
        md_lines.append(f"- Stable selector ratio: {ratio} %")
        md_lines.append(f"- Heal events: {s.get('heal_events',0)}")
        md_lines.append(f"- Cache saved: {s.get('cache_saved',0)} / skipped: {s.get('cache_skipped',0)}")
        prof = s.get("profiles",{})
        md_lines.append(f"- Profiles: {', '.join([f'{k}:{v}' for k,v in prof.items()]) or 'n/a'}\n")

    md_path = os.path.join(ROOT, "phase_a_validation_summary.md")
    json_path = os.path.join(ROOT, "phase_a_validation_summary.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"✅ Generated: {md_path}")
    print(f"✅ Generated: {json_path}")
    print("\n" + "\n".join(md_lines))

if __name__ == "__main__":
    main()
