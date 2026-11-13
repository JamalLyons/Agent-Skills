#!/usr/bin/env python3
"""Validate and persist a workforce ledger. Records observations; never controls agents."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile

VERSION = 1
SHA = re.compile(r'^[0-9a-f]{40}(?:[0-9a-f]{24})?$')
TRANSITIONS = {
    'pending': {'running', 'blocked', 'cancelled'},
    'running': {'waiting', 'verifying', 'blocked', 'cancelled', 'rework'},
    'waiting': {'running', 'verifying', 'blocked', 'cancelled', 'rework'},
    'verifying': {'accepted', 'rework', 'blocked', 'cancelled'},
    'rework': {'running', 'blocked', 'cancelled'},
    'accepted': {'integrated', 'rework', 'blocked'},
    'blocked': {'pending', 'cancelled'},
    'integrated': set(), 'cancelled': set(),
}
ACTIVE = {'running', 'waiting'}
TERMINAL = {'completed', 'failed', 'cancelled', 'interrupted'}
OUTCOMES = {'fixed', 'tracked', 'added', 'opened', 'dropped'}


class StateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise StateError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def stamp():
    return datetime.now(timezone.utc).isoformat()


def new_state(run_id, repository, issues=(), context=None):
    state = {'version': VERSION, 'revision': 0, 'run_id': run_id,
             'repository': repository, 'issues': list(issues), 'owner': None,
             'context': context or {}, 'steps': {}, 'followups': {}, 'updated_at': stamp()}
    validate(state)
    return state


def validate(state):
    require(isinstance(state, dict) and type(state.get('version')) is int and state.get('version') == VERSION,
            'unsupported or missing state version')
    try:
        json.dumps(state, allow_nan=False)
    except (TypeError, ValueError):
        raise StateError('state must contain finite JSON values') from None
    require(type(state.get('revision')) is int and state['revision'] >= 0, 'invalid revision')
    require(text(state.get('run_id')) and text(state.get('repository')), 'run/repository identity required')
    require(isinstance(state.get('issues'), list) and all(text(x) for x in state['issues']),
            'issues must be a list of qualified references')
    require(state.get('owner') is None or text(state.get('owner')), 'invalid owner')
    require(isinstance(state.get('context'), dict), 'context must be an object')
    require(isinstance(state.get('steps'), dict), 'steps must be an object')
    require(isinstance(state.get('followups'), dict), 'followups must be an object')
    integrations, integrated_heads, active_checkouts, active_tasks = set(), set(), set(), set()
    for key, step in state['steps'].items():
        require(text(key) and isinstance(step, dict), 'invalid step')
        require(step.get('status') in TRANSITIONS, f'{key}: invalid status')
        require(sha(step.get('base')) and text(step.get('checkout')), f'{key}: base/checkout required')
        deps = step.get('dependencies')
        require(isinstance(deps, list) and all(text(d) for d in deps) and len(deps) == len(set(deps))
                and all(d in state['steps'] and d != key for d in deps), f'{key}: invalid dependencies')
        attempts = step.get('attempts')
        require(isinstance(attempts, list), f'{key}: attempts must be a list')
        ids = []
        for index, attempt in enumerate(attempts):
            require(isinstance(attempt, dict) and text(attempt.get('id')), f'{key}: invalid attempt')
            ids.append(attempt['id'])
            require(attempt.get('task_id') is None or text(attempt.get('task_id')), f'{key}: invalid task identity')
            observation = attempt.get('terminal_observation')
            if observation is not None:
                require(isinstance(observation, dict) and observation.get('status') in TERMINAL
                        and text(observation.get('evidence')), f'{key}: invalid terminal observation')
            if index < len(attempts) - 1 and attempt.get('task_id'):
                require(observation is not None, f'{key}: previous runtime attempt lacks terminal evidence')
        require(len(ids) == len(set(ids)), f'{key}: duplicate attempt identity')
        if step['status'] in ACTIVE | {'verifying', 'accepted', 'integrated'}:
            require(bool(attempts), f'{key}: attempt identity required')
        if step['status'] in ACTIVE:
            require(bool(attempts) and attempts[-1].get('terminal_observation') is None,
                    f'{key}: active step must have an unfinished attempt')
            require(step['checkout'] not in active_checkouts, f'{key}: checkout has another active writer')
            active_checkouts.add(step['checkout'])
            task_id = attempts[-1].get('task_id')
            if task_id:
                require(task_id not in active_tasks, f'{key}: runtime task already assigned to an active step')
                active_tasks.add(task_id)
        if attempts and step['status'] not in ACTIVE and attempts[-1].get('task_id'):
            require(attempts[-1].get('terminal_observation') is not None,
                    f'{key}: runtime task needs a recorded terminal observation')
        if step['status'] in {'accepted', 'integrated'}:
            accepted = step.get('accepted') or {}
            require(sha(accepted.get('head')) and isinstance(accepted.get('evidence'), list)
                    and accepted['evidence'] and all(text(x) for x in accepted['evidence']),
                    f'{key}: acceptance needs head-bound verification evidence')
        if step['status'] == 'integrated':
            integration = step.get('integration') or {}
            require(sha(integration.get('head')), f'{key}: integration head required')
            source = step['accepted']['head']
            require(source not in integrations, f'{key}: source head already integrated')
            require(integration['head'] not in integrated_heads, f'{key}: integration head already recorded')
            integrations.add(source)
            integrated_heads.add(integration['head'])
    visiting, done = set(), set()
    def visit(key):
        require(key not in visiting, 'dependency cycle')
        if key in done:
            return
        visiting.add(key)
        for dep in state['steps'][key]['dependencies']:
            visit(dep)
        visiting.remove(key)
        done.add(key)
    for key in state['steps']:
        visit(key)
    for key, item in state['followups'].items():
        require(text(key) and isinstance(item, dict) and text(item.get('problem')),
                'followup needs stable ID and problem')
        require(item.get('outcome') == 'awaiting-answer' or item.get('outcome') in OUTCOMES,
                f'{key}: invalid followup outcome')
        require(text(item.get('evidence')), f'{key}: discovery evidence required')
        require(text(item.get('pending_question')) or item.get('outcome') != 'awaiting-answer',
                f'{key}: pending question required')
        if item.get('outcome') == 'dropped':
            require(text(item.get('authorization')), f'{key}: dropping requires recorded user decision')
        if item.get('outcome') in {'added', 'opened'}:
            require(text(item.get('authorization')) and text(item.get('tracking')),
                    f'{key}: issue mutation needs authorization and verified destination')
        if item.get('outcome') == 'tracked':
            require(text(item.get('tracking')), f'{key}: tracking evidence required')
    return state


def apply_event(state, event, owner):
    """Pure validated transition. Owner IDs coordinate writers; they are not credentials."""
    validate(state)
    require(isinstance(event, dict), 'event must be an object')
    require(text(owner), 'owner identity required')
    out = deepcopy(state)
    kind = event.get('type')
    if kind == 'claim':
        require(out['owner'] in (None, owner), f'run owned by {out["owner"]}; reconcile before claiming')
        out['owner'] = owner
    else:
        require(out['owner'] == owner, f'run owned by {out["owner"]}; claim with the current owner first')
        if kind == 'release':
            out['owner'] = None
        elif kind == 'context':
            require(isinstance(event.get('values'), dict), 'context values must be an object')
            out['context'].update(event['values'])
        elif kind == 'add-step':
            key = event.get('step')
            require(text(key) and key not in out['steps'], 'new unique step ID required')
            out['steps'][key] = {'status': 'pending', 'base': event.get('base'),
                'checkout': event.get('checkout'), 'dependencies': event.get('dependencies', []),
                'attempts': []}
        elif kind == 'transition':
            key, target = event.get('step'), event.get('to')
            require(key in out['steps'], 'unknown step')
            step = out['steps'][key]
            previous = step['status']
            require(target in TRANSITIONS[previous], f'invalid transition {previous} -> {target}')
            if target == 'running' and previous != 'waiting':
                require(all(out['steps'][d]['status'] in {'accepted', 'integrated'}
                            for d in step['dependencies']), 'prerequisites are not accepted')
                attempt_id = event.get('attempt_id')
                require(text(attempt_id) and all(a['id'] != attempt_id for a in step['attempts']),
                        'new attempt identity required')
                step['attempts'].append({'id': attempt_id, 'task_id': event.get('task_id'),
                                         'terminal_observation': None})
            if previous in ACTIVE and target not in ACTIVE:
                attempt = step['attempts'][-1]
                if attempt.get('task_id'):
                    require(event.get('terminal_status') in TERMINAL and text(event.get('terminal_evidence')),
                            'record host terminal status and evidence before releasing task ownership')
                    attempt['terminal_observation'] = {'status': event['terminal_status'],
                                                        'evidence': event['terminal_evidence']}
            if target == 'accepted':
                step['accepted'] = {'head': event.get('head'), 'evidence': event.get('evidence')}
            elif target == 'integrated':
                require(event.get('source_head') == step['accepted']['head'], 'accepted source head mismatch')
                step['integration'] = {'head': event.get('head')}
            elif target in {'rework', 'pending'}:
                step.pop('accepted', None)
            if target in {'blocked', 'cancelled', 'rework'}:
                require(text(event.get('reason')), f'{target} needs a reason')
                step['reason'] = event['reason']
            step['status'] = target
        elif kind == 'followup':
            key, values = event.get('id'), event.get('values')
            require(text(key) and isinstance(values, dict), 'followup ID and values required')
            item = out['followups'].setdefault(key, {'outcome': 'awaiting-answer'})
            item.update(values)
        else:
            raise StateError('unknown event type')
    out['revision'] += 1
    out['updated_at'] = stamp()
    return validate(out)


@contextmanager
def writer_lock(path):
    """An exclusive local lock, with no expiry or automatic stale-lock takeover."""
    lock = path.with_name(path.name + '.lock')
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise StateError(f'writer lock exists: {lock}; inspect its owner/process before recovery') from None
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'created_at': stamp()}))
        yield
    finally:
        lock.unlink()


def atomic_write(path, state):
    validate(state)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(state, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load(path):
    return validate(json.loads(path.read_text()))


def mutate(path, event, owner, expected_revision=None):
    with writer_lock(path):
        state = load(path)
        require(expected_revision is None or state['revision'] == expected_revision,
                'revision changed; reload and reconcile before retrying')
        result = apply_event(state, event, owner)
        atomic_write(path, result)
        return result


def status(state):
    validate(state)
    active = {k: {'status': s['status'], 'attempt': s['attempts'][-1]}
              for k, s in state['steps'].items() if s['status'] in ACTIVE}
    actionable = [k for k, s in state['steps'].items() if s['status'] in {'pending', 'rework'}
                  and all(state['steps'][d]['status'] in {'accepted', 'integrated'} for d in s['dependencies'])]
    return {'run_id': state['run_id'], 'revision': state['revision'], 'owner': state['owner'],
            'active_observations_to_reconcile': active, 'actionable_after_reconciliation': actionable,
            'blocked': {k: s.get('reason') for k, s in state['steps'].items() if s['status'] == 'blocked'},
            'awaiting_verification_or_integration': {k: s['status'] for k, s in state['steps'].items()
                                                   if s['status'] in {'verifying', 'accepted'}},
            'unanswered_followups': {k: v for k, v in state['followups'].items()
                                    if v['outcome'] == 'awaiting-answer'},
            'context': state['context']}


def markdown_summary(summary):
    """A disposable view of canonical JSON; never a second writable ledger."""
    lines = [f'# Workforce run {summary["run_id"]}',
             f'Owner: {summary["owner"] or "unclaimed"}; revision: {summary["revision"]}.',
             '', 'Reconcile these recorded observations with current Git, host tasks, and publication before acting.']
    for key, label in [('active_observations_to_reconcile', 'Active task observations'),
                       ('actionable_after_reconciliation', 'Actionable after reconciliation'),
                       ('awaiting_verification_or_integration', 'Awaiting verification/integration'),
                       ('blocked', 'Blocked'), ('unanswered_followups', 'Unanswered follow-ups')]:
        values = summary[key]
        if values:
            lines += ['', f'## {label}']
            if isinstance(values, list):
                lines += [f'- {value}' for value in values]
            else:
                lines += [f'- {name}: {json.dumps(value, ensure_ascii=False)}' for name, value in values.items()]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'apply', 'validate', 'status', 'resume'))
    parser.add_argument('file', type=Path)
    parser.add_argument('--owner')
    parser.add_argument('--run-id')
    parser.add_argument('--repository')
    parser.add_argument('--issue', action='append', default=[])
    parser.add_argument('--event', help='JSON event path, or - for stdin')
    parser.add_argument('--expected-revision', type=int)
    parser.add_argument('--markdown', action='store_true', help='render a disposable status/resume summary')
    args = parser.parse_args(argv)
    try:
        require(not args.markdown or args.command in {'status', 'resume'}, '--markdown requires status or resume')
        if args.command == 'init':
            state = new_state(args.run_id, args.repository, args.issue)
            args.file.parent.mkdir(parents=True, exist_ok=True)
            with writer_lock(args.file):
                require(not args.file.exists(), 'state already exists; inspect/resume it instead')
                atomic_write(args.file, state)
        elif args.command == 'apply':
            require(args.event is not None, '--event is required')
            if args.event == '-':
                import sys
                event = json.load(sys.stdin)
            else:
                event = json.loads(Path(args.event).read_text())
            state = mutate(args.file, event, args.owner, args.expected_revision)
        else:
            state = load(args.file)
        if args.command in {'status', 'resume'}:
            summary = status(state)
            print(markdown_summary(summary) if args.markdown else json.dumps(summary, indent=2, allow_nan=False))
        else:
            print(json.dumps(state, indent=2, allow_nan=False))
        return 0
    except (StateError, OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
