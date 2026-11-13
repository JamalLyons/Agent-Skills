---
name: caffeine-time
description: Start a coding session and keep the computer awake for a specified duration so work is not interrupted. Use when the user asks to begin coding without the computer sleeping; defaults to 2 hours 56 minutes.
---

# Caffeine Time

When starting a coding session, prevent the Mac from sleeping for the requested duration. If the user does not give a duration, use **2 hours 56 minutes** (10,560 seconds).

## Procedure

1. Determine the duration from the user's request. Accept natural language durations such as `90 minutes`, `2 hours`, or `1 hour 15 minutes`. If omitted, use 2 hours 56 minutes. If the requested time is ambiguous, use the clearest reasonable interpretation and state it.
2. Confirm the platform. This skill's command is for macOS. On another platform, use that platform's native awake/inhibit mechanism if known; otherwise explain the limitation.
3. Start a detached macOS `caffeinate` process for the computed integer number of seconds. Substitute the duration for `SECONDS`:

   ```sh
   ( nohup /usr/bin/caffeinate -dimsu -t SECONDS >/dev/null 2>&1 </dev/null & )
   ```

   This asks macOS to stay awake for the duration without blocking the coding session. Do not use `pmset sleepnow` or any command that puts the computer to sleep.
4. Tell the user the duration and approximate local time the awake request will end. Explain that closing the lid or manually sleeping/shutting down the Mac can still interrupt work; the timer only prevents automatic sleep while active.

## Examples

- “Start a coding session” → keep the Mac awake for 2 hours 56 minutes.
- “Start a coding session and keep it awake for 45 minutes” → keep it awake for 45 minutes.
- “Give me three hours to code” → keep it awake for 3 hours.
