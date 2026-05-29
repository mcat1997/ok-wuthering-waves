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
