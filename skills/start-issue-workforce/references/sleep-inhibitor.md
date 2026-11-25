# Sleep inhibitor

Read when starting long-running recon, checks, or dispatch, on resume, and before the final report.

Before long-running recon, checks, or agent dispatch, the lead must start a temporary idle-sleep inhibitor on the machine running the workforce. Keep it active across child waits, retries, verification, and continuation through the whole approved queue. One inhibitor per lead run is sufficient; children must not start their own. A plan-only run that ends before lengthy work does not need one.

On macOS, run `/usr/bin/caffeinate -i` in a persistent background process or managed terminal session that survives individual shell tool calls. Record its PID/session and start time in the run index, and verify that it remains running after the launching call returns. When a stable process dedicated to this lead run is available, use `/usr/bin/caffeinate -i -w <lead-run-pid>` so the assertion also ends if that process exits. Do not use the PID of a short-lived tool shell or a shared app process as the run lifetime. Leave display sleep enabled; do not change persistent power settings. This prevents idle system sleep, not lid-close or explicit sleep.

On other operating systems, use an available temporary system sleep inhibitor with equivalent run-scoped ownership and cleanup. If the host cannot keep a process alive, the utility is unavailable, or permissions prevent it, report the limitation and continue authorized work without claiming sleep is prevented.

On resume, reconcile the recorded inhibitor with the actual process/session and recreate it if needed. Release only this run's inhibitor when the queue completes, the user stops/cancels the run, or work is blocked/handed back with no active execution remaining. Keep it active during host-directed continuation waits while children or checks still run. Verify cleanup before the final report; never use a broad `killall`/`pkill` that could stop another run's inhibitor.

The user-facing equivalent is the [caffeine-time](../../caffeine-time/SKILL.md) skill, which starts a timed `/usr/bin/caffeinate -i -t SECONDS` and records its PID in `$TMPDIR/caffeine-time.pid`. A workforce run does not reuse or stop that timer; it keeps its own run-scoped inhibitor, tied to the lead run with `-w <lead-run-pid>` when a stable process exists, and releases only its own PID.
