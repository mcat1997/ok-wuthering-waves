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

## 三次修复内容

- `enhanced_resonance` 新增 `require_available` 元参数：角色提供强化 E 检测时，等待不到强化 E 图标就返回失败，不再把普通 E 点击记录成强化 E 成功。
- liberation 新增 `require_lib2` 元参数：爱弥斯 R2 会先等待 `lib2_available()`，没有 R2 图标时不释放解放。
- action 新增 `stop_on_fail` 元参数：爱弥斯 R2 失败时跳过后续依赖 R2 的 `E-2A-E` 尾段，直接走该 step 的切人出口。
- 爱弥斯“快速重击”从普通 `heavy` 改成 `execute`，优先复用 `Aemeath.handle_heavy()` 的高亮重击和 pending lib2 状态记录。
- 爱弥斯两段强化 E 增加更长等待和 `require_available=True`，1 链重击 / 处决后补短后摇，减少动画锁期间误判。

### 三次修复验证

- `python -m py_compile src/team/__init__.py src/team/TeamRotation.py src/team/aemeath_denia_chisa.py src/task/AutoCombatTask.py src/task/BaseCombatTask.py tests/TestChar.py` 通过。
- `git diff --check` 通过。
- `python .codestable/tools/validate-yaml.py --dir .codestable/issues/2026-05-29-team-axis-video-gap` 通过。
- 定向 `unittest` 仍被当前环境缺少 `ok` 依赖挡在导入阶段：`ModuleNotFoundError: No module named 'ok'`。

## 四次修复内容

- `TeamRotationStep` 增加 `intro_actions` / `intro_retry_limit`，让队伍轴能在 step 出口声明“这里要求真实变奏”，并在协奏未满时保持当前 step。
- `TeamRotation.perform()` 在 `next_free_intro=True` 出口前先读取真实协奏并输出 `intro readiness` 日志；协奏未满时执行补协奏动作，仍未满则不切人、不推进，避免假变奏污染爱弥斯状态。
- 队伍轴切人不再把 `next_free_intro` 透传为底层 `free_intro=True`；确认协奏满后用 `switch_to_char(..., free_intro=False)` 让底层重新读取真实协奏并设置 `has_intro`。
- `TeamActionRunner` 新增 `build_con` 动作，并支持 `normal_chain` / `tap_normal_chain` 的 `until_con_full` 参数。
- 爱达千轴加长达妮娅 / 千咲关键普攻段和 2A 间隔，并在千咲、达妮娅、爱弥斯所有变奏出口追加 `build_con`，优先保证协奏满再进入下一名角色。
- 新增单测覆盖：队伍轴不会在协奏未满时强制 fake intro；真实满协奏时不会传 `free_intro=True` 但仍能得到入场；`build_con` 会以 `until_con_full=True` 执行普攻链。

### 四次修复验证

- `python -m py_compile src/team/__init__.py src/team/TeamRotation.py src/team/aemeath_denia_chisa.py src/task/AutoCombatTask.py src/task/BaseCombatTask.py tests/TestChar.py` 通过。
- `git diff --check` 通过。
- `python .codestable/tools/validate-yaml.py --dir .codestable/issues/2026-05-29-team-axis-video-gap` 通过。
- 通过本地 stub `ok` 的隔离脚本验证队伍轴核心分支：满协奏时切人不传 `free_intro=True` 但目标获得入场；未满协奏时不切人并保持当前 step；`build_con` 以 `until_con_full=True` 执行。
- 定向 `unittest` 仍被当前环境缺少 `ok` 依赖挡在导入阶段：`ModuleNotFoundError: No module named 'ok'`。

## 已知限制

- 本次修复无法在本地直接复现实机战斗，只能基于用户提供的实战日志、实战视频和教学视频定位并修正明显偏差。
- 当前本地 Python 环境缺少 `ok` 依赖，`unittest` 仍无法导入项目测试入口。
