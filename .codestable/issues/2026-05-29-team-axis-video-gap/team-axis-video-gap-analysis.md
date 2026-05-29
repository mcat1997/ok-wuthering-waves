---
doc_type: issue-analysis
issue: 2026-05-29-team-axis-video-gap
status: confirmed
root_cause_type: state-pollution
related: [team-axis-video-gap-report.md]
tags: [combat, team-axis, rotation]
---

# 爱达千队伍轴偏离教学视频 根因分析

## 1. 问题定位

| 关键位置 | 说明 |
|---|---|
| `src/team/TeamRotation.py:perform` | 队伍轴直接执行 action，不经过角色 `do_perform()`，因此也不会执行角色轴里的入场状态补账。 |
| `src/char/Aemeath.py:96` | 爱弥斯角色轴在 `has_intro` 时会调用 `record_intro_liberation()`，让 `lib()` 允许变奏后短时间内释放 R1。 |
| `src/char/Aemeath.py:106` | 爱弥斯 `lib()` 依赖 `can_cast_lib1()`，没有入场补账时启动段 R1 会被判定为不可释放。 |
| `src/team/aemeath_denia_chisa.py` | 原 plan 对 E/R/强化E 缺少前后摇等待，容易在上一个动作动画锁期间直接判定失败。 |

## 2. 失败路径还原

**正常路径**：千咲电锯终结后变奏切爱弥斯 → 爱弥斯记录入场解放窗口 → Q/a3a4 后释放 R1 → 接 1 链重击、强化E、处决等节点。

**失败路径**：队伍轴通过 `switch_to_char(..., free_intro=True)` 给爱弥斯设置 `has_intro=True` → 但没有调用爱弥斯入场记录 → `Aemeath.lib()` 认为 R1 未解锁 → 启动段 `R1` 返回 `False` → 后续重击、强化E 仍然推进，实战节奏偏离教学。

**分叉点**：`src/team/TeamRotation.py:perform` — 队伍轴绕过角色轴入场处理。

## 3. 根因

**根因类型**：state-pollution

**根因描述**：队伍轴新增后只复用了 `BaseChar` 的动作原语，没有复用每个角色 `do_perform()` 中的入场状态维护。爱弥斯是受影响最明显的角色：她的 R1 可用性依赖 `record_intro_liberation()`，而队伍轴没有调用该方法，导致变奏入场后的 R1 被误判不可用。同时，动作节点之间缺少短等待，导致部分技能在上一动作动画锁或 UI 未恢复时被过早尝试。

**是否有多个根因**：是。主因是爱弥斯入场状态缺失；次因是队伍轴 action 缺少通用前后摇等待能力。

## 4. 影响面

- **影响范围**：主要影响爱达千队伍轴；通用队伍轴中所有依赖角色入场状态的 future plan 也可能受影响。
- **潜在受害模块**：`src/team/` 队伍轴实现、`AutoCombatTask` 队伍轴路径。
- **数据完整性风险**：无持久化数据风险。
- **严重程度复核**：维持 P1。功能可运行，但核心输出质量不达预期。

## 5. 修复方案

### 方案 A：在队伍轴 step 开始时补角色入场钩子

- **做什么**：`TeamRotation.perform()` 对当前角色执行 action 前，如果 `char.has_intro` 为真，则调用角色已有的入场记录方法，例如 `record_intro_liberation()`。
- **优点**：根因直接，复用现有角色状态逻辑，改动范围小。
- **缺点 / 风险**：只覆盖已有入场记录方法，不能自动复刻所有角色 `do_perform()` 里的特殊入场动作。
- **影响面**：`src/team/TeamRotation.py`。

### 方案 B：只在爱达千 plan 中手写爱弥斯入场 action

- **做什么**：在爱弥斯 step 前新增专用 action，调用爱弥斯入场记录。
- **优点**：影响范围最小，只动具体队伍轴。
- **缺点 / 风险**：通用队伍轴仍缺少入场状态契约，后续队伍容易重复踩坑。
- **影响面**：`src/team/aemeath_denia_chisa.py`。

### 方案 C：回退到角色轴执行爱弥斯段

- **做什么**：队伍轴切到爱弥斯后调用 `Aemeath.do_perform()`。
- **优点**：最接近已有角色逻辑。
- **缺点 / 风险**：会重新启用启发式切人，不再是固定队伍轴，无法精确表达教学流程。
- **影响面**：`src/team/`、`src/char/Aemeath.py`。

### 推荐方案

**推荐方案 A**，并补充 action 前后摇能力。它直接修复爱弥斯 R1 失败的主因，同时给具体 plan 提供低风险调参手段。

## 6. 二次实战复盘：调度状态漂移

用户 2026-05-29 11:02 录制的实战日志显示，上一轮修复后爱弥斯启动段 R1 已能在正确入场窗口内成功释放，但队伍轴仍会偏离教学视频。新的失败信号集中在调度层：

| 日志信号 | 说明 |
|---|---|
| 11:02:24 `startup 8/8` 的爱弥斯 `E` 因 `combat check not in combat` 异常中断 | 同一场战斗短暂丢目标后，`AutoCombatTask` 结束本轮循环。 |
| 11:02:32 重新 `selected team rotation` 且 `startup 1/8` 从头开始 | 同一战斗恢复目标后，`combat_start` 被 `load_chars()` 刷新，队伍轴被当成新战斗重建，启动轴重复执行。 |
| 多个 action 返回 `False` 后仍然继续推进 | 例如千咲 `强化E`、达妮娅 `R2`、爱弥斯 `R1/R2/E` 等失败后，`TeamRotation.perform()` 仍切人和 `advance()`，导致固定轴和真实技能状态分离。 |
| loop 10 爱弥斯 `R1` 返回 `False` 后继续执行重击、强化E、处决 | 这是关键动作失败后继续推进的直接证据，后续动作已经不再对应教学轴。 |

### 补充根因

1. `TeamRotation.perform()` 没有 action 成败语义，所有返回值都被当成“已执行完”，包括 `False` 和 `(False, 0, False)`。
2. `select_team_rotation()` 只用 `combat_start` 判断是否同一轮轴，无法区分真实战斗结束和短暂 `target enemy failed` / `combat check not in combat`。
3. 爱达千 plan 缺少“关键动作必须成功”的声明，失败节点没有重试、没有中止，也没有足够日志提示实际偏离点。

### 补充修复方案

在方案 A 基础上追加调度修复：

- 队伍轴 action 支持 `attempts` / `retry_delay` / `required` / `force_on_fail` 等通用元参数，并在日志中输出每次尝试、失败、重试和最终结果。
- required action 失败后不再切人和推进 step，交回角色轴兜底，避免用错误状态继续跑固定轴。
- 对短时间内由目标识别丢失造成的 out-of-combat，允许在同一队伍下续用原 `TeamRotation`，保留 startup/loop 进度和 step 内 action 进度，避免在爱弥斯长 step 中断后重打一整段。
- 对千咲这种教学轴明确要按、但 UI 可用性检测容易返回 false 的强化 E，允许按计划强制发一次共鸣键，并记录原始检测结果。

## 7. 三次实战复盘：爱弥斯强化 E / R2 假成功

用户 2026-05-29 11:33 录制的实战日志显示，二次修复后队伍轴没有再从头重跑启动段，但爱弥斯段仍有状态分叉：

| 日志信号 | 说明 |
|---|---|
| 11:33:09、11:33:13、11:33:56、11:33:59 `enhanced resonance wait char=Aemeath timeout=1.2s result=None` 后仍记录 action 成功 | 爱弥斯“强化E”的前置图像未出现，但队伍轴继续点击共鸣并把它当强化 E 成功。实际可能只是普通 E。 |
| 11:33:14、11:34:01 爱弥斯 `R2` 两次尝试均 `result=False` | 依赖前面强化 E / 重击状态的 R2 没有准备好。 |
| 11:33:14 `R2` 失败后继续执行 `E`，随后 `combat check not in combat` | R2 失败后仍继续跑 `R2-E-2A-E` 尾段，导致真实状态继续偏离并触发长时间丢目标重进。 |

### 追加根因

1. `enhanced_resonance` 只“等待”角色专用强化 E 检测，但等待失败后仍调用普通 `click_resonance()` 并将其记录为成功。
2. 爱弥斯 R2 前没有强校验 `lib2_available()`，R2 失败仍会继续执行后续依赖 R2 的尾段动作。
3. “快速重击”用普通重击实现，没有复用 `Aemeath.handle_heavy()` 对高亮重击和 pending lib2 的处理。

### 追加修复方案

- 给 `enhanced_resonance` 增加 `require_available`：角色提供强化 E 检测时，等待失败就返回失败，不再把普通 E 伪装成强化 E。
- 给 liberation 增加 `require_lib2`：R2 节点先等待 `lib2_available()`，没有 R2 图标时不点击解放。
- 给 action 增加 `stop_on_fail`：爱弥斯 R2 失败时跳过后续 `E-2A-E` 尾段，直接按 step 的切人出口走，避免继续污染真实状态。
- 爱弥斯“快速重击”改用 `execute`，优先走 `handle_heavy()`，保留角色已有的高亮重击 / pending lib2 处理。
