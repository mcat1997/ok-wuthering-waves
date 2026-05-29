---
doc_type: issue-fix
issue: 2026-05-29-team-axis-video-gap
status: fixed
fixed_at: 2026-05-29
tags: [combat, team-axis, rotation]
---

# 爱达千队伍轴偏离教学视频 Fix Note

## 修复内容

- 在 `TeamRotation.perform()` 中新增入场钩子：当前 step 角色带 `has_intro` 时，对支持 `record_intro_liberation()` 的角色执行入场状态补账，并按 `last_switch_in_time` 保证同一次入场只记录一次。
- 在 `TeamActionRunner` 中支持通用 `pre_delay` / `post_delay`，并过滤这些通用参数，避免传入 `click_resonance()` / `click_echo()` 等角色 helper。
- 在爱达千 plan 中为容易空判的节点补短等待：达妮娅 `E -> R`、千咲 `Q -> 强化E`、达妮娅 `2A -> 强化E/R2`、爱弥斯 `Q/a3a4 -> R1` 等。
- 补充单测覆盖队伍轴入场钩子只在同一次入场记录一次。

## 二次修复内容

- `TeamActionRunner` 新增 action 成败语义：`False` 和 `(False, ...)` 会被识别为失败，日志会记录 `attempt`、`success`、`result`、重试和 exhausted。
- 队伍轴 action 支持 `attempts` / `retry_delay` / `required` / `force_on_fail` 等元参数，且不会把这些参数传进角色技能 helper。
- `TeamRotation.perform()` 遇到 required action 失败时不再切人、不再 `advance()`，保留当前 step 并回退给角色轴兜底，避免真实状态和固定轴继续分叉。
- `TeamRotation` 记录 step 内 action 进度；如果爱弥斯长 step 中途因丢目标被打断，恢复后从失败 action 继续，而不是重打一整段 R1/重击/强化E。
- `select_team_rotation()` 支持在短暂 `target enemy failed` / `combat check not in combat` / `sleep check not in combat` 后恢复原 rotation，默认窗口为 `Team Axis Resume Window = 12` 秒，避免同一场战斗重跑启动段。
- 千咲 `强化E` 改为检测失败时按计划强制发一次共鸣键，并补 `force_on_fail` 日志；达妮娅强化 E、千咲电锯终结、爱弥斯 R1/强化 E 等关键节点加 required/retry 标记。
- 爱弥斯队伍轴释放强化 E 成功后同步调用 `record_enhance_e()`，让她自己的强化 E / R2 等状态判断不再缺账。

## 验证

- `python -m py_compile src/team/__init__.py src/team/TeamRotation.py src/team/aemeath_denia_chisa.py src/task/AutoCombatTask.py src/task/BaseCombatTask.py tests/TestChar.py` 通过。
- `git diff --check` 通过。
- `python .codestable/tools/validate-yaml.py --dir .codestable/issues/2026-05-29-team-axis-video-gap` 通过。
- 定向 `unittest` 仍被当前环境缺少 `ok` 依赖挡在导入阶段：`ModuleNotFoundError: No module named 'ok'`。

### 二次修复验证

- `python -m py_compile src/team/__init__.py src/team/TeamRotation.py src/team/aemeath_denia_chisa.py src/task/AutoCombatTask.py src/task/BaseCombatTask.py tests/TestChar.py` 通过。
- `git diff --check` 通过。
- `python .codestable/tools/validate-yaml.py --dir .codestable/issues/2026-05-29-team-axis-video-gap` 通过。
- 定向 `unittest` 仍被当前环境缺少 `ok` 依赖挡在导入阶段：`ModuleNotFoundError: No module named 'ok'`。

## 已知限制

- 本次修复无法在本地直接复现实机战斗，只能基于用户提供的实战日志、实战视频和教学视频定位并修正明显偏差。
- 当前本地 Python 环境缺少 `ok` 依赖，`unittest` 仍无法导入项目测试入口。
