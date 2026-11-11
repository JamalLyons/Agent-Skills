# Plan format (version 1)

`scripts/apply_plan.py` reads one JSON file. `validate` reports every problem at once. The excerpt below shows one task. [plan.example.json](plan.example.json) is a complete plan that passes validation (it is checked by the tests).

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
| `epic` | yes | Issue number of an open issue in `repo` |
| `label` | no | Default `workforce`. Created if missing. Applied to every task issue so interrupted runs can find issues that were created but not yet linked |
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

## Rendered issue body

Each created issue starts with a hidden marker:

```
<!-- workforce-epic: {"v":1,"epic":"owner/name#42","key":"T1","kind":"agent","tier":"hard"} -->
```

Then come a header line (`Part of #42 · task T1 · tier hard`, or `needs a human`) and these sections: Summary, Scope, Out of scope, Owned paths, Acceptance criteria (checkboxes), Verification, Epic criteria covered, Dependencies (`Blocked by #n, …`), and Notes. Empty optional sections are omitted. The Dependencies line duplicates the native blocked-by links, so the order is still readable if the dependencies API is unavailable.

The marker is how `apply` recognises its own issues on re-runs and how `epic_status.py` reads kind and tier. Editing the rest of the body is safe. Removing the marker makes the issue unmanaged: it still appears in status, with tier unknown, but `apply` would create a new issue for that key.

Run `apply_plan.py render <plan> [--task KEY]` to print bodies without touching GitHub.
