#!/usr/bin/env python3
"""Read live subscription usage per provider and suggest a model for each planned step.

Usage:
  python3 route.py                          # usage snapshot only
  python3 route.py --steps hard,easy,easy,hard,easy
  python3 route.py --steps ... --set antigravity=30 --set cursor=60   # % LEFT this week
  python3 route.py --steps ... --avoid claude                          # spare a provider (fallback only)
  python3 route.py --json ...               # machine-readable

Sources (all read-only, local):
  claudeAgent  ~/.claude.json -> cachedUsageUtilization (five_hour / seven_day utilization %)
  codex        newest ~/.codex/sessions/**/*.jsonl event with rate_limits.primary/secondary
  cursor, antigravity: no local limit data; use --set or config.json usage_overrides, else assumed.

The allocation is a greedy heuristic: each step goes to the tier model whose provider has the
highest score (weekly % left x bonuses), then that provider's headroom is reduced by the step's
estimated cost, so the work spreads out. Treat it as a suggestion; the lead can override.
"""
import argparse, glob, json, os, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = time.time()


def load_config():
    with open(os.path.join(HERE, "..", "config.json")) as f:
        return json.load(f)


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="minutes") if ts else None


def _window(used_pct, resets_at):
    """Return % left, treating an already-passed reset as a fresh window."""
    if used_pct is None:
        return None
    if resets_at and resets_at < NOW:
        return 100.0
    return max(0.0, 100.0 - float(used_pct))


def claude_usage():
    p = os.path.expanduser("~/.claude.json")
    try:
        d = json.load(open(p)).get("cachedUsageUtilization") or {}
        u = d.get("utilization") or {}
        def parse(key):
            w = u.get(key) or {}
            ts = None
            if w.get("resets_at"):
                ts = datetime.fromisoformat(w["resets_at"]).timestamp()
            return _window(w.get("utilization"), ts), ts
        s_left, s_reset = parse("five_hour")
        w_left, w_reset = parse("seven_day")
        if w_left is None and s_left is None:
            return None
        return {"weekly_left": w_left, "weekly_resets": w_reset, "session_left": s_left,
                "session_resets": s_reset, "source": "~/.claude.json",
                "age_min": round((NOW - d.get("fetchedAtMs", NOW * 1000) / 1000) / 60)}
    except Exception:
        return None


def codex_usage():
    files = sorted(glob.glob(os.path.expanduser("~/.codex/sessions/**/*.jsonl"), recursive=True),
                   key=os.path.getmtime, reverse=True)[:25]
    for f in files:
        best = None
        try:
            with open(f, errors="ignore") as fh:
                for line in fh:
                    if '"rate_limits"' not in line or '"used_percent"' not in line:
                        continue
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    stack = [o]
                    while stack:
                        x = stack.pop()
                        if isinstance(x, dict):
                            rl = x.get("rate_limits")
                            if isinstance(rl, dict) and (rl.get("primary") or rl.get("secondary")):
                                best = rl
                            stack.extend(x.values())
                        elif isinstance(x, list):
                            stack.extend(x)
        except OSError:
            continue
        if best:
            pr, se = best.get("primary") or {}, best.get("secondary") or {}
            return {"weekly_left": _window(se.get("used_percent"), se.get("resets_at")),
                    "weekly_resets": se.get("resets_at"),
                    "session_left": _window(pr.get("used_percent"), pr.get("resets_at")),
                    "session_resets": pr.get("resets_at"), "source": "codex session log",
                    "age_min": round((NOW - os.path.getmtime(f)) / 60)}
    return None


def snapshot(cfg, sets):
    providers = sorted({m["provider"] for t in cfg["tiers"].values() for m in t})
    live = {"claudeAgent": claude_usage(), "codex": codex_usage()}
    overrides = dict(cfg.get("usage_overrides") or {})
    overrides.update(sets)
    out = {}
    for p in providers:
        if p in overrides:
            v = overrides[p]
            left = v.get("weekly_left_pct") if isinstance(v, dict) else v
            out[p] = {"weekly_left": float(left), "session_left": None, "source": "user-provided"}
        elif live.get(p):
            out[p] = live[p]
        else:
            out[p] = {"weekly_left": None, "session_left": None, "source": "unknown"}
    return out


def allocate(cfg, snap, steps, avoid=()):
    r = cfg["routing"]
    score, notes = {}, {}
    for p, s in snap.items():
        left = s.get("weekly_left")
        if s.get("age_min") is not None and s["age_min"] > 60:
            notes[p] = f"reading is {s['age_min']} min old; may be stale (ask the user if it matters)"
        if left is None:
            left = r["assumed_left_pct_when_unknown"]
            notes[p] = f"usage unknown, assumed {left:.0f}% left"
        if s.get("session_left") is not None and s["session_left"] < r["min_session_left_pct"]:
            notes[p] = f"5h window nearly used ({s['session_left']:.0f}% left), skipped"
            left = 0
        elif left < r["min_weekly_left_pct"]:
            notes[p] = f"only {left:.0f}% left this week, skipped"
            left = 0
        bonus = 1.0
        reset = s.get("weekly_resets")
        if left > 0 and reset and reset - NOW < r["reset_soon_hours"] * 3600:
            bonus = r["reset_soon_bonus"]
            notes.setdefault(p, f"resets in {(reset - NOW) / 3600:.0f}h: use-it-or-lose-it bonus")
        if p in avoid and left > 0:
            bonus *= 0.05  # last resort only
            notes[p] = "avoided at user request (fallback only)"
        score[p] = [left, bonus]
    plan = []
    for i, tier in enumerate(steps, 1):
        cands = []
        for m in cfg["tiers"][tier]:
            left, bonus = score.get(m["provider"], [0, 1])
            if left <= 0:
                continue
            s = left * bonus * (r["preferred_bonus"] if m.get("preferred") else 1.0)
            cands.append((s, m))
        if not cands:
            # tier exhausted: fall back to the other tier rather than stalling
            other = "hard" if tier == "easy" else "easy"
            cands = [(score[m["provider"]][0], m) for m in cfg["tiers"][other] if score[m["provider"]][0] > 0]
        if not cands:
            plan.append({"step": i, "tier": tier, "model": None, "reason": "no provider has headroom"})
            continue
        cands.sort(key=lambda c: c[0], reverse=True)
        m = cands[0][1]
        score[m["provider"]][0] = max(0.0, score[m["provider"]][0] - r["step_cost_pct"][tier])
        plan.append({"step": i, "tier": tier, "model": m["model"], "provider": m["provider"],
                     "options": m["options"]})
    return plan, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="", help="comma list of easy|hard, in plan order")
    ap.add_argument("--set", action="append", default=[], help="provider=PCT_LEFT_THIS_WEEK")
    ap.add_argument("--avoid", action="append", default=[], help="provider to spare (fallback only)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    cfg = load_config()
    alias = {"gemini": "antigravity", "gpt": "codex", "openai": "codex", "claude": "claudeAgent",
             "anthropic": "claudeAgent", "grok": "cursor", "composer": "cursor"}
    sets = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        k = alias.get(k.lower(), k)
        sets[k] = float(v.rstrip("%"))
    snap = snapshot(cfg, sets)
    steps = [s.strip().lower() for s in a.steps.split(",") if s.strip()]
    avoid = {alias.get(x.lower(), x) for x in a.avoid}
    plan, notes = allocate(cfg, snap, steps, avoid) if steps else ([], {})
    if a.json:
        print(json.dumps({"usage": snap, "notes": notes, "assignments": plan}, indent=2, default=str))
        return
    print("Usage (% LEFT)        week    5h      source")
    for p, s in snap.items():
        f = lambda v: f"{v:5.0f}%" if v is not None else "    ? "
        extra = f" ({s['age_min']} min old)" if s.get("age_min") is not None else ""
        rs = f", week resets {_iso(s['weekly_resets'])}" if s.get("weekly_resets") else ""
        print(f"  {p:<18} {f(s.get('weekly_left'))}  {f(s.get('session_left'))}   {s['source']}{extra}{rs}")
    for p, n in notes.items():
        print(f"  note: {p}: {n}")
    if plan:
        print("\nSuggested routing")
        for x in plan:
            if x["model"]:
                print(f"  step {x['step']:>2} [{x['tier']}] -> {x['model']} ({x['provider']}) {json.dumps(x['options'])}")
            else:
                print(f"  step {x['step']:>2} [{x['tier']}] -> NONE: {x['reason']}")


if __name__ == "__main__":
    main()
