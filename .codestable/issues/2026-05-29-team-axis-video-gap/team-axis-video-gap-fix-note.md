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

## 验证

- `python -m py_compile src/team/__init__.py src/team/TeamRotation.py src/team/aemeath_denia_chisa.py src/task/AutoCombatTask.py src/task/BaseCombatTask.py tests/TestChar.py` 通过。
- `git diff --check` 通过。
- `python .codestable/tools/validate-yaml.py --dir .codestable/issues/2026-05-29-team-axis-video-gap` 通过。
- 定向 `unittest` 仍被当前环境缺少 `ok` 依赖挡在导入阶段：`ModuleNotFoundError: No module named 'ok'`。

## 已知限制

- 本次修复无法在本地直接复现实机战斗，只能基于用户提供的实战日志、实战视频和教学视频定位并修正明显偏差。
- 当前本地 Python 环境缺少 `ok` 依赖，`unittest` 仍无法导入项目测试入口。
