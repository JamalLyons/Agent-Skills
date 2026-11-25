---
name: caffeine-time
description: Keep a Mac awake for a coding session for a set duration, defaulting to 2 hours 56 minutes, without stacking duplicate timers; also extend, check, or stop that timer. Use when the user asks to start a coding session, keep the computer awake, stop it sleeping, or stop or extend caffeine. macOS-first; other platforms use their native inhibitor if known.
---

# Caffeine Time

Keep the Mac from idle-sleeping for the requested duration; default **2 hours 56 minutes** (10,560 s). Pidfile: `"${TMPDIR:-/tmp}/caffeine-time.pid"`.

1. Parse the duration (`90 minutes`, `1 hour 15 minutes`, etc.) to integer seconds; state any interpretation. macOS only; elsewhere use the native inhibitor if known, else explain.
2. Check for this skill's timer: read the pidfile and confirm with `ps -o pid=,etime=,command= -p <pid>` that it is still `caffeinate`. A stale pidfile (no process, or not caffeinate) is removed. `pgrep -fl caffeinate` may show other timers; never touch those.
3. If a timer is running, do not start another. Report its remaining time and offer to **extend** (replace with a new timer of the new total) or **keep** it. Replace only after the user agrees.
4. Start (or replace: `kill <old pid>` first, only that PID):

   ```sh
   f="${TMPDIR:-/tmp}/caffeine-time.pid"
   nohup /usr/bin/caffeinate -i -t SECONDS >/dev/null 2>&1 </dev/null & echo $! > "$f"
   ```

   Add `-d` only if the user asks to keep the display on. Never use `pmset` or change persistent power settings.
5. Verify the PID from the pidfile is a running `caffeinate`. On failure, say so; never claim success.
6. Report the duration, local end time, PID, and how to stop: `kill <pid>`. Lid close, manual sleep, or shutdown still interrupt it.

Follow-up requests:
- "How long left?": compute from `etime` and the started duration (`ps -o command=` shows `-t`).
- "Stop caffeine": `kill` the pidfile's PID, verify it exited, remove the pidfile.

Never `killall caffeinate` or `pkill caffeinate`; other tools (such as start-issue-workforce) may own their own timers.
