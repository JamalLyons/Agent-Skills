#!/usr/bin/env python3
"""Show the queue state of an epic's sub-issues.

  epic_status.py --repo owner/name --epic 42           table
  epic_status.py --repo owner/name --epic 42 --json    machine-readable
  epic_status.py --repo owner/name --epic 42 --ready   ready issue numbers, dependency order

Statuses for open tasks: ready, blocked, check (a blocker was closed without a
merged PR or commit), in-review (an open PR will close it), human (needs a person).
Closed tasks: done, done-unverified (closed as completed with no merged PR or
commit), dropped (closed as not planned or duplicate).

A blocker counts as satisfied only when it is closed as completed AND it was
closed by a merged PR or a commit, or is a human task closed as completed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from epiclib import REPO_RE, Gh, GhError, parse_marker  # noqa: E402

CLOSER = '''timelineItems(itemTypes: [CLOSED_EVENT], last: 1) {
  nodes { ... on ClosedEvent { closer { __typename ... on PullRequest { number merged } } } } }'''

QUERY = '''query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      number title state url
      subIssues(first: 50, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          number title state stateReason url body
          assignees(first: 5) { nodes { login } }
          closedByPullRequestsReferences(first: 10, includeClosedPrs: true) { nodes { number state merged url } }
          %(closer)s
          blockedBy(first: 50) {
            pageInfo { hasNextPage }
            nodes {
              number title state stateReason body repository { nameWithOwner }
              closedByPullRequestsReferences(first: 10, includeClosedPrs: true) { nodes { number merged } }
              %(closer)s
            }
          }
        }
      }
    }
  }
}''' % {'closer': CLOSER}

ORDER = ['ready', 'check', 'in-review', 'blocked', 'human', 'done', 'done-unverified', 'dropped']


def _closer(node: dict) -> dict | None:
    items = (node.get('timelineItems') or {}).get('nodes') or []
    c = items[-1].get('closer') if items else None
    if not c:
        return None
    return {'type': c.get('__typename'), 'number': c.get('number'), 'merged': c.get('merged')}


def _evidence(node: dict) -> bool:
    """True when a merged PR or a commit closed (or will be recorded as closing) this issue."""
    c = _closer(node)
    if c and (c['type'] == 'Commit' or (c['type'] == 'PullRequest' and c['merged'])):
        return True
    prs = (node.get('closedByPullRequestsReferences') or {}).get('nodes') or []
    return any(p.get('merged') for p in prs)


def normalize_issue(node: dict, repo: str) -> dict:
    meta = parse_marker(node.get('body'))
    return {
        'number': node['number'],
        'repo': (node.get('repository') or {}).get('nameWithOwner', repo),
        'title': node.get('title', ''),
        'state': node['state'].lower(),
        'state_reason': (node.get('stateReason') or '').lower() or None,
        'url': node.get('url'),
        'key': meta.get('key') if meta else None,
        'kind': (meta or {}).get('kind', 'agent'),
        'tier': (meta or {}).get('tier'),
        'managed': meta is not None,
        'evidence': _evidence(node),
        'open_prs': [p['number'] for p in ((node.get('closedByPullRequestsReferences') or {}).get('nodes') or [])
                     if p.get('state') == 'OPEN'],
        'assignees': [a['login'] for a in ((node.get('assignees') or {}).get('nodes') or [])],
    }


def closed_status(i: dict) -> str:
    if i['state_reason'] in ('not_planned', 'duplicate'):
        return 'dropped'
    if i['kind'] == 'human' or i['evidence']:
        return 'done'
    return 'done-unverified'


def classify(task: dict, blockers: list[dict]) -> tuple[str, str]:
    """Return (status, reason) for one normalized sub-issue."""
    if task['state'] == 'closed':
        s = closed_status(task)
        return s, {'done': '', 'dropped': f'closed as {task["state_reason"]}',
                   'done-unverified': 'closed as completed without a merged PR or commit'}[s]
    if task['kind'] == 'human':
        return 'human', 'needs a person'
    if task['open_prs']:
        return 'in-review', 'open PR ' + ', '.join(f'#{n}' for n in task['open_prs'])
    pending, dropped, unverified = [], [], []
    for b in blockers:
        ref = f'#{b["number"]}' if b['repo'] == task['repo'] else f'{b["repo"]}#{b["number"]}'
        if b['state'] == 'open':
            pending.append(ref)
            continue
        s = closed_status(b)
        if s == 'dropped':
            dropped.append(ref)
        elif s == 'done-unverified':
            unverified.append(ref)
    if dropped:
        return 'blocked', 'blocker dropped: ' + ', '.join(dropped) + ' (re-plan needed)'
    if pending:
        return 'blocked', 'waiting on ' + ', '.join(pending)
    if unverified:
        return 'check', 'blocker closed without merged PR: ' + ', '.join(unverified)
    return 'ready', ''


def build_status(epic: dict, nodes: list[dict], repo: str) -> dict:
    tasks, warnings, unmanaged = [], [], []
    for n in nodes:
        t = normalize_issue(n, repo)
        bb = n.get('blockedBy') or {}
        if (bb.get('pageInfo') or {}).get('hasNextPage'):
            warnings.append(f'#{t["number"]} has more than 50 blockers; status may be incomplete')
        blockers = [normalize_issue(b, repo) for b in (bb.get('nodes') or [])]
        t['blocked_by'] = [b['number'] for b in blockers if b['repo'] == repo]
        t['status'], t['reason'] = classify(t, blockers)
        if not t['managed']:
            unmanaged.append(t['number'])
        tasks.append(t)

    # dependency order among sibling tasks, stable by issue number
    nums = sorted(t['number'] for t in tasks)
    deps = {t['number']: [b for b in t['blocked_by'] if b in nums] for t in tasks}
    order, placed = [], set()
    while len(order) < len(nums):
        progress = False
        for n in nums:
            if n not in placed and all(d in placed for d in deps[n]):
                order.append(n)
                placed.add(n)
                progress = True
        if not progress:
            cyc = [n for n in nums if n not in placed]
            warnings.append('dependency cycle among ' + ', '.join(f'#{n}' for n in cyc))
            order += cyc
            break
    if unmanaged:
        warnings.append('not created by create-workforce-epic (treated as agent tasks, tier unknown): '
                        + ', '.join(f'#{n}' for n in sorted(unmanaged)))
    rank = {n: i for i, n in enumerate(order)}
    tasks.sort(key=lambda t: rank[t['number']])
    counts = {s: sum(t['status'] == s for t in tasks) for s in ORDER}
    return {'repo': repo, 'epic': epic['number'], 'title': epic['title'], 'state': epic['state'].lower(),
            'counts': counts, 'tasks': tasks, 'ready': [t['number'] for t in tasks if t['status'] == 'ready'],
            'warnings': warnings}


def fetch(gh: Gh, repo: str, epic: int) -> dict:
    owner, name = repo.split('/', 1)
    nodes, after, issue = [], None, None
    while True:
        data = gh.graphql(QUERY, {'owner': owner, 'name': name, 'number': epic, 'after': after})
        issue = (data.get('repository') or {}).get('issue')
        if issue is None:
            raise GhError(404, f'issue {repo}#{epic} not found')
        page = issue['subIssues']
        nodes += page['nodes']
        if not page['pageInfo']['hasNextPage']:
            break
        after = page['pageInfo']['endCursor']
    return build_status(issue, nodes, repo)


def main(argv: list[str] | None = None, gh: Gh | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--epic', type=int, required=True)
    out = ap.add_mutually_exclusive_group()
    out.add_argument('--json', action='store_true')
    out.add_argument('--ready', action='store_true', help='print ready issue numbers only')
    args = ap.parse_args(argv)
    if not REPO_RE.match(args.repo) or args.epic < 1:
        print('--repo must be owner/name and --epic a positive number', file=sys.stderr)
        return 2
    try:
        st = fetch(gh or Gh(), args.repo, args.epic)
    except GhError as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(st, indent=2))
    elif args.ready:
        for n in st['ready']:
            print(f'#{n}')
    else:
        print(f'{st["repo"]}#{st["epic"]} {st["title"]} [{st["state"]}]')
        print('  ' + '  '.join(f'{s}={c}' for s, c in st['counts'].items() if c))
        for t in st['tasks']:
            tag = t['key'] or '-'
            kind = 'human' if t['kind'] == 'human' else (t['tier'] or '?')
            reason = f'  ({t["reason"]})' if t['reason'] else ''
            print(f'  #{t["number"]:<6} {t["status"]:<16} {tag:<8} {kind:<6} {t["title"]}{reason}')
        for w in st['warnings']:
            print(f'warning: {w}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
