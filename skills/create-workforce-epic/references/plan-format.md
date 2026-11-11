# Plan format (version 1)

`scripts/apply_plan.py` reads one JSON file. `validate` reports every problem at once. The excerpt below shows one task for an existing epic. [plan.example.json](plan.example.json) is a complete plan for an existing epic, and [plan.new-epic.example.json](plan.new-epic.example.json) is one that creates its own epic. Both pass validation (the tests check them).

```json
{
  "version": 1,
  "repo": "owner/name",
  "epic": 42,
  "label": "workforce",
  "criteria": [
    { "id": "C1", "text": "Users can export a report as CSV", "covered_by": ["T1", "T2"] },
    { "id": "C2", "text": "Export button in the report view", "covered_by": ["T3"] },
    { "id": "C3", "text": "PDF export (derived)", "deferred": "Needs a rendering library decision; separate epic" }
  ],
  "tasks": [
    {
      "key": "T1",
      "title": "Add ExportJob model and migration",
      "kind": "agent",
      "tier": "hard",
      "summary": "Introduce the ExportJob model that tracks export requests and their status.",
      "scope": ["ExportJob model with status enum", "Migration and rollback"],
      "out_of_scope": ["API endpoints", "UI"],
      "owned_paths": ["src/models/export_job.py", "migrations/"],
      "acceptance": ["Migration applies and rolls back cleanly", "Model tests cover status transitions"],
      "verify": ["make test", "make migrate-check"],
      "blocked_by": [],
      "notes": "Follow the pattern in src/models/report.py."
    }
  ]
}
```

## Fields

| Field | Required | Rules |
|---|---|---|
| `version` | yes | `1` |
| `repo` | yes | `owner/name` |
| `epic` | yes | Either the number of an open issue in `repo` (existing epic), or an object describing a new epic (below) |
| `label` | no | Default `workforce`. Created if missing. Applied to every task issue (and to a new epic) so interrupted runs can find issues that were created but not yet linked |
| `criteria[]` | yes | Every epic acceptance criterion. `id` is unique; set exactly one of `covered_by` (task keys) or `deferred` (reason) |
| `tasks[].key` | yes | Unique, stable across re-plans, letter first, up to 32 of `A-Z a-z 0-9 _ -` |
| `title` | yes | 1–256 characters, written as the PR's intent |
| `kind` | no | `agent` (default) or `human` |
| `tier` | agent only | `easy` or `hard`. Human tasks must omit it |
| `summary` | yes | What and why, in a few sentences |
| `scope`, `out_of_scope` | no | Lists of short strings |
| `owned_paths` | agent: recommended | Files, directories, or globs. Used for overlap warnings |
| `acceptance` | yes | At least one checkable criterion; rendered as a checklist |
| `verify` | agent: yes | Exact commands that exist in the repo |
| `blocked_by` | no | Task keys from this plan, or `"#n"` for an existing issue in the same repo |
| `notes` | no | Pointers to patterns, decisions, or risks |

Text fields must not contain the reserved string `workforce-epic`.

## New epic

When no epic issue exists, `epic` is an object and `apply` creates the epic issue before the tasks:

```json
"epic": {
  "key": "csv-export",
  "title": "Epic: CSV export for reports",
  "summary": "Let report owners export any report as CSV from the report view.",
  "background": "Customers copy tables by hand into spreadsheets.",
  "out_of_scope": ["PDF export"],
  "notes": "Requested in the product sync."
}
```

| Field | Required | Rules |
|---|---|---|
| `key` | yes | Same rules as task keys. Unique among epics in the repository and unchanged between runs: a re-run finds the epic it created by this key |
| `title` | yes | 1–256 characters |
| `summary` | yes | The goal, in a few sentences |
| `background`, `notes` | no | Strings |
| `out_of_scope` | no | List of short strings |

The epic body contains a hidden root marker (`<!-- workforce-epic-root: {"v":1,"key":"csv-export"} -->`), then Summary, Background, Acceptance criteria (every `criteria` entry: covered ones as checkboxes, deferred ones with their reason), Out of scope, Notes, and a Tasks note. The epic gets the plan label too, which is how a re-run finds it. Once it exists you may keep the object (it is reused) or replace it with the epic's number.

## Rendered issue body

Each created issue starts with a hidden marker:

```
<!-- workforce-epic: {"v":1,"epic":"owner/name#42","key":"T1","kind":"agent","tier":"hard"} -->
```

Then come a header line (`Part of #42 · task T1 · tier hard`, or `needs a human`) and these sections: Summary, Scope, Out of scope, Owned paths, Acceptance criteria (checkboxes), Verification, Epic criteria covered, Dependencies (`Blocked by #n, …`), and Notes. Empty optional sections are omitted. The Dependencies line duplicates the native blocked-by links, so the order is still readable if the dependencies API is unavailable.

The marker is how `apply` recognises its own issues on re-runs and how `epic_status.py` reads kind and tier. Editing the rest of the body is safe. Removing the marker makes the issue unmanaged: it still appears in status, with tier unknown, but `apply` would create a new issue for that key.

Run `apply_plan.py render <plan> [--task KEY]` to print bodies without touching GitHub. For a new epic, render prints the epic body first, and task markers show `#new` until the epic exists.
