#!/usr/bin/env python3
"""Advisory routing from bounded local cache reads; never dispatches or contacts providers."""
import argparse
import glob
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_AGE = 3600
MAX_BYTES = 1024 * 1024
ALIASES = {'gemini': 'antigravity', 'gpt': 'codex', 'openai': 'codex',
           'claude': 'claudeAgent', 'anthropic': 'claudeAgent',
           'grok': 'cursor', 'composer': 'cursor'}


def percent(v):
    if isinstance(v, bool):
        raise ValueError('percent must be numeric')
    v = float(v)
    if not math.isfinite(v) or not 0 <= v <= 100:
        raise ValueError('percent must be finite and between 0 and 100')
    return v


def timestamp(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = float(v)
    else:
        n = datetime.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()
    if not math.isfinite(n):
        raise ValueError('invalid timestamp')
    return n


def load_config():
    cfg = json.loads((HERE.parent / 'config.json').read_text())
    if set(cfg['tiers']) != {'easy', 'hard'}:
        raise ValueError('tiers must be easy and hard')
    for models in cfg['tiers'].values():
        for m in models:
            if not isinstance(m['provider'], str) or not isinstance(m['model'], str):
                raise ValueError('invalid model identity')
            if not isinstance(m['options'], dict):
                raise ValueError('model options must be an object')
    r = cfg['routing']
    for k in ('min_weekly_left_pct', 'min_session_left_pct', 'assumed_left_pct_when_unknown'):
        percent(r[k])
    for tier in ('easy', 'hard'):
        if percent(r['step_cost_pct'][tier]) <= 0:
            raise ValueError('step cost must be positive')
    for k in ('preferred_bonus', 'reset_soon_hours', 'reset_soon_bonus'):
        if not math.isfinite(float(r[k])) or float(r[k]) <= 0:
            raise ValueError('routing bonuses/hours must be finite and positive')
    return cfg


def observation(used, reset, observed, now):
    # Past resets cannot establish usage in the new window.
    if observed is None or not 0 <= now - observed <= MAX_AGE:
        return None
    if reset is not None and timestamp(reset) <= now:
        return None
    return 100 - percent(used) if used is not None else None


def claude_usage(now):
    try:
        p = Path.home() / '.claude.json'
        if p.stat().st_size > MAX_BYTES:
            return None
        d = json.loads(p.read_text()).get('cachedUsageUtilization') or {}
        observed = timestamp(d['fetchedAtMs'] / 1000)
        out = {'source': 'local Claude cache', 'age_min': round((now-observed)/60)}
        for key, window in [('session', 'five_hour'), ('weekly', 'seven_day')]:
            w = (d.get('utilization') or {}).get(window) or {}
            out[key+'_left'] = observation(w.get('utilization'), w.get('resets_at'), observed, now)
            if out[key+'_left'] is not None and w.get('resets_at'):
                out[key+'_resets'] = timestamp(w['resets_at'])
        return out
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None


def codex_usage(now):
    candidates = []
    # Bounded tail read per file; glob still enumerates matching paths.
    files = glob.glob(str(Path.home() / '.codex/sessions/**/*.jsonl'), recursive=True)
    def mtime(p):
        try:
            return os.path.getmtime(p)
        except OSError:
            return 0
    for p in sorted(files, key=mtime, reverse=True)[:25]:
        try:
            with open(p, 'rb') as f:
                f.seek(0, 2)
                start = max(0, f.tell()-MAX_BYTES)
                f.seek(start)
                if start:
                    f.readline()  # discard partial first line
                lines = f.read(MAX_BYTES).decode('utf-8', errors='replace').splitlines()
            for line in lines:
                try:
                    event = json.loads(line)
                    payload = event.get('payload') or {}
                    if event.get('type') != 'event_msg' or payload.get('type') != 'token_count':
                        continue
                    rl = payload.get('rate_limits')
                    if not isinstance(rl, dict):
                        continue
                    observed = timestamp(event['timestamp'])
                    out = {'source': 'local Codex event', 'age_min': round((now-observed)/60),
                           'weekly_left': None, 'session_left': None}
                    for w in (rl.get('primary'), rl.get('secondary')):
                        if not isinstance(w, dict):
                            continue
                        key = {300: 'session', 10080: 'weekly'}.get(w.get('window_minutes'))
                        if key:
                            out[key+'_left'] = observation(w.get('used_percent'), w.get('resets_at'), observed, now)
                            if out[key+'_left'] is not None and w.get('resets_at'):
                                out[key+'_resets'] = timestamp(w['resets_at'])
                    if observed <= now:
                        candidates.append((observed, out))
                except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
                    continue
        except OSError:
            continue
    return max(candidates, key=lambda x: x[0])[1] if candidates else None


def snapshot(cfg, sets, now=None):
    now = time.time() if now is None else now
    providers = {m['provider'] for models in cfg['tiers'].values() for m in models}
    overrides = dict(cfg.get('usage_overrides') or {})
    overrides.update(sets)
    unknown = set(overrides) - providers
    if unknown:
        raise ValueError('unknown override provider: '+', '.join(sorted(unknown)))
    live = {'claudeAgent': claude_usage(now), 'codex': codex_usage(now)}
    out = {}
    for p in sorted(providers):
        s = dict(live.get(p) or {'weekly_left': None, 'session_left': None, 'source': 'unknown'})
        if p in overrides:
            v = overrides[p]
            s['weekly_left'] = percent(v['weekly_left_pct'] if isinstance(v, dict) else v)
            s['weekly_source'] = 'user-provided weekly override (no freshness guarantee)'
        out[p] = s
    return out


def allocate(cfg, snap, steps, avoid=(), exclude=(), allowed=None):
    if any(t not in ('easy', 'hard') for t in steps):
        raise ValueError('steps must contain only easy or hard')
    r = cfg['routing']
    remaining, notes = {}, {}
    for p, s in snap.items():
        remaining[p] = {w: percent(s[w+'_left']) if s.get(w+'_left') is not None
                        else percent(r['assumed_left_pct_when_unknown']) for w in ('weekly', 'session')}
        notes[p] = []
        if any(s.get(w+'_left') is None for w in ('weekly', 'session')):
            notes[p].append('unknown window(s): configured assumption used; not observed quota')
        if p in exclude:
            notes[p].append('excluded')
        elif p in avoid:
            notes[p].append('spared unless no eligible alternative')
    plan = []
    for i, tier in enumerate(steps, 1):
        cost = percent(r['step_cost_pct'][tier])
        candidates = []
        for m in cfg['tiers'][tier]:
            p = m['provider']
            if p in exclude or (allowed is not None and p+'/'+m['model'] not in allowed):
                continue
            headroom = remaining[p]
            if any(headroom[w]-cost < r['min_'+w+'_left_pct'] for w in ('weekly', 'session')):
                continue
            score = min(headroom.values()) * (r['preferred_bonus'] if m.get('preferred') else 1)
            # Reset bonuses only apply to trustworthy future reset metadata if supplied.
            reset = snap[p].get('weekly_resets')
            now = time.time()
            if reset and 0 < timestamp(reset)-now < r['reset_soon_hours']*3600:
                score *= r['reset_soon_bonus']
            candidates.append((p not in avoid, score, m))
        if not candidates:
            plan.append({'step': i, 'tier': tier, 'model': None,
                         'reason': 'no eligible model in tier with estimated reserve'})
            continue
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        m = candidates[0][2]
        for w in ('weekly', 'session'):
            remaining[m['provider']][w] -= cost
        plan.append({'step': i, 'tier': tier, 'model': m['model'], 'provider': m['provider'],
                     'options': m['options']})
    return plan, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--steps', default='')
    ap.add_argument('--set', action='append', default=[], metavar='PROVIDER=WEEKLY_PERCENT_LEFT')
    ap.add_argument('--avoid', action='append', default=[])
    ap.add_argument('--exclude', action='append', default=[])
    ap.add_argument('--allow-model', action='append', help='repeat capability-approved provider/model')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    alias = lambda s: ALIASES.get(s.lower(), s)
    try:
        cfg = load_config()
        providers = {m['provider'] for models in cfg['tiers'].values() for m in models}
        sets = {}
        for arg in a.set:
            k, v = arg.split('=', 1)
            sets[alias(k)] = percent(v.rstrip('%'))
        avoid, exclude = {alias(p) for p in a.avoid}, {alias(p) for p in a.exclude}
        if (avoid | exclude) - providers:
            raise ValueError('unknown provider in avoid/exclude')
        steps = a.steps.split(',') if a.steps else []
        steps = [s.strip().lower() for s in steps]
        if len(steps) > 1000:
            raise ValueError('at most 1000 advisory steps per invocation')
        roster = {m['provider']+'/'+m['model'] for models in cfg['tiers'].values() for m in models}
        if a.allow_model and set(a.allow_model)-roster:
            raise ValueError('allow-model is not in configured roster')
        snap = snapshot(cfg, sets)
        plan, notes = allocate(cfg, snap, steps, avoid, exclude,
                               set(a.allow_model) if a.allow_model is not None else None)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        ap.error(str(e))
    result = {'usage': snap, 'notes': notes, 'assignments': plan,
              'advisory': 'Quota estimates, not cost, availability, or authorization guarantees'}
    if a.json:
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        print(result['advisory'])
        for p, s in snap.items():
            print(p, json.dumps(s, allow_nan=False))
        for p, n in notes.items():
            print(p, '; '.join(n))
        for step in plan:
            print(json.dumps(step, allow_nan=False))


if __name__ == '__main__':
    main()
