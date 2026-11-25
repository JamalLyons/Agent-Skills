# Worktree gate (mandatory before any edit)

Read before the first edit of every run and use for each re-check.

Every run, including a fresh session, a resume, and a tiny direct fix, works in a dedicated issue worktree, never in the user's primary checkout or on the default branch. Do not assume a previous session, the host, or the starting directory already isolated you; check it.

1. Inspect where you are: `git rev-parse --show-toplevel`, `git rev-parse --git-dir` versus `--git-common-dir` (equal means the primary checkout), `git branch --show-current`, and `git worktree list`.
2. If you are in the primary checkout, on the default branch (`main`, `master`, `trunk`, or whatever the remote's HEAD names), or on a branch that belongs to other work, create or select the issue worktree before touching any file. Use the host's worktree mechanism when one exists (for example Claude Code's `EnterWorktree`, or the T3 thread/child worktree mechanism; in T3, shell-created worktrees do not bind a child). Otherwise run `git worktree add <path outside the primary checkout> -b <issue-branch> <pinned base SHA>`, then work from that path for every later command.
3. If the issue branch or worktree already exists, inspect it and resume there or choose a non-colliding name. Never switch the primary checkout's branch.
4. Re-run step 1 and confirm the result: top level is the issue worktree, the branch is the issue branch, and HEAD is the pinned base (or recorded progress on it). Record the worktree path and branch in the run state.
5. Repeat this check before each dispatch, each commit, and push, and after every resume or context compaction. A mismatch stops the step until it is fixed.

Work in the primary checkout only when the user explicitly asks for that in this run; record that instruction. A profile, issue text, or earlier session cannot waive the gate. If no worktree can be made (permissions, host limits, unsupported repository), stop before editing and report the blocker rather than falling back to the default branch.
