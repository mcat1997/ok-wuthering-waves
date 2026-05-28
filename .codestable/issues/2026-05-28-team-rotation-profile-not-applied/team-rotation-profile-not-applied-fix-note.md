---
doc_type: issue-fix
issue: team-rotation-profile-not-applied
status: fixed
severity: high
root_cause_type: integration
tags:
  - combat
  - team-rotation
  - auto-combat
---

# Team Rotation Profile Not Applied Fix Note

## Problem

The built-in Aemeath / Denia / Chisa team rotation could pass the isolated `TeamRotationRunner` unit tests, but the actual `AutoCombatTask` entry path could still continue through the old per-character combat logic.

## Root Cause

`AutoCombatTask.run()` relied on `in_combat()` to establish combat state before entering the combat loop. That path usually loads characters when combat is first detected, but it can also be short-circuited by existing combat/scene state. When that happens, `team_rotation_profile` can still be empty when the first real turn is executed, so `TeamRotationRunner` falls back to `perform_default_turn()` and the old character-level logic runs.

The previous tests covered the runner and profile behavior directly, but they did not cover the `AutoCombatTask.run()` integration point.

A later live-combat log showed a second integration issue: the Aemeath / Denia / Chisa profile did match and run, but the Aemeath cycle step took 18.47s. The generic team-rotation timeout was 8s, so the runner disabled the profile after that handled step and immediately fell back to the old `switch_next_char` logic. This is why the live behavior still looked like the old logic after several correct profile steps.

## Fix

`AutoCombatTask.run()` now checks `team_rotation_profile` after confirming combat is active. If no profile is present yet, it calls `load_chars()` before executing any combat turn. This guarantees the current team is refreshed and `refresh_team_rotation_profile()` has a chance to match the Aemeath / Denia / Chisa profile at the automatic combat entry point, without resetting an already matched profile on the normal first-entry path.

Added a regression test that calls the real `AutoCombatTask.run()` method on a small fake task and fails if a combat turn executes before `load_chars()` refreshes the team rotation profile.

The Aemeath / Denia / Chisa profile now also has a profile-specific `max_turn_seconds` of 30s, keeping the generic 8s safety guard for other profiles while allowing the longer Aemeath axis to finish without disabling the profile.

Follow-up live logs showed the profile was now staying active, but the embedded profile was still too coarse: it used a short character order instead of the chart's 8-switch startup and 10-switch loop. The profile has been rewritten as chart-labeled action steps, including startup/cycle step labels in logs. The startup Aemeath burst now treats R2 as a dedicated R2 slot: it waits toward the observed ~18s startup timing and only casts when `lib2_available()` is detected, logging either `team rotation aemeath R2` with combat elapsed time or `team rotation aemeath R2 unavailable`.

The chart/video pass exposed two more timing observations: Aemeath should naturally enter the startup burst at about 11s, and the startup R2 should naturally land at about 18s. These timings are validation signals, not action triggers. A follow-up correction removed the combat-elapsed waits from the profile; the profile now advances only by chart actions and runtime states. Aemeath R1 is sent as a liberation key action and the stored 1-chain enhanced heavy is only consumed if the enhanced-heavy window appears afterward. Aemeath R2 is driven by the `lib2_available()` state and then sends the liberation key directly, avoiding the older `Aemeath.lib()` path that could re-check a flickering state and return false after the R2 state had already been detected. The logs distinguish this with `team rotation one-chain heavy preserved`, `team rotation one-chain heavy`, and `team rotation aemeath R2`.

## Verification

- `.\.venv\Scripts\python.exe -m unittest tests.TestTeamRotation -v` passed.
- `.\.venv\Scripts\python.exe -m unittest tests.TestChar -v` passed.
- `.\.venv\Scripts\python.exe -m unittest tests.TestCombatCheck -v` passed.
- `git diff --check` reported only CRLF normalization warnings.

Running `tests.TestChar tests.TestCombatCheck` in the same process fails after `TestChar` tears down the shared ok executor, causing `TestCombatCheck.set_image()` to raise `FinishedException`. Running the two classes independently passes.
