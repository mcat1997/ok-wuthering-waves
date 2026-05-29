---
doc_type: feature-design
feature: 2026-05-29-team-axis
status: approved
summary: Add a generic team-axis rotation layer and implement the 1-chain Aemeath, Denia, Chisa axis from the tutorial video.
tags: [combat, team-axis, rotation]
requirement:
---

# 队伍轴接入方案

> 阶段：阶段 1（方案设计）
> 输入来源：用户请求 + `/Users/a38999/Downloads/爱达千5R教学.mp4`
> 执行假设：用户要求“设计并写”，本轮视为设计确认后继续实现。

## 0. 术语约定

- **角色轴**：现有 `BaseChar.do_perform()`，由当前角色自己决定技能、普攻和切人。
- **队伍轴 / TeamRotation**：战斗任务层的上层编排，按整队成员匹配后执行启动轴和循环轴。
- **Action**：队伍轴的最小动作节点，例如 `E`、`R`、`Q`、`2A`、`a2a3`、`强化E`、`重击`、`变奏`。
- **Step**：一个角色在场时连续执行的一组 Action，结束后显式切到下一名目标角色。
- **启动轴**：每场战斗首次进入匹配队伍时执行一次。
- **循环轴**：启动轴结束后反复执行，直到战斗结束。

## 1. 决策与约束

### 需求摘要

现状只能让“当前角色”自己跑一段动作并交给启发式切人，无法表达“爱弥斯、达妮娅、千咲”这种跨角色固定时序。新增能力需要在不破坏旧角色轴的前提下，让匹配队伍进入通用队伍轴引擎，并落一条教学视频里的 1 链爱达千轴。

### 明确不做

- 不新增图像模板和 `Labels`，只使用已有角色识别与技能可用判断。
- 不改角色识别、协奏识别、战斗进入/退出判断。
- 不把所有角色都迁移成队伍轴；未匹配的队伍仍走现有角色轴。
- 不追求视频逐帧复刻，动作语言按可自动化的技能/普攻/重击/等待粒度执行。

### 复杂度档位

走默认档位。该能力只影响自动战斗编排层，不引入外部服务、持久化、并发任务或新模型。

### 关键决策

- D1：队伍轴挂在 `AutoCombatTask` 循环内，优先级高于 `get_current_char().perform()`。
- D2：队伍轴本身放在新模块 `src/team/`，避免继续膨胀 `BaseCombatTask.py` 和 `AutoCombatTask.py`。
- D3：显式切人使用新增的固定目标切换接口，保留原有 `switch_next_char` 的启发式选择作为默认角色轴路径。
- D4：教学视频轴用 Python 声明式 plan 表达，后续新增队伍只新增 plan / subclass。

## 2. 名词与编排

### 2.1 名词层

**现状**

- `AutoCombatTask.run()` 在战斗中反复调用 `self.get_current_char().perform()`。
- `BaseCombatTask.switch_next_char()` 只接受当前角色，目标由 `_choose_switch_target()` 按角色定位、buff、协奏和 `get_switch_priority()` 决定。
- `BaseChar` 已提供技能动作原语：`click_resonance`、`click_liberation`、`click_echo`、`continues_normal_attack`、`heavy_attack`、`heavy_click_forte`、`f_break` 等。

**变化**

新增名词：

- `TeamRotation`：队伍轴基类，负责匹配队伍、维护启动/循环状态、执行 step。
- `TeamRotationStep`：`char_cls + actions + next_char_cls` 的声明式动作块。
- `TeamActionRunner`：把动作名映射到 `BaseChar` helper。
- `AemeathDeniaChisaRotation`：1 链爱弥斯、达妮娅、千咲的具体队伍轴。

接口示例：

```python
rotation = select_team_rotation(task)
if rotation and rotation.perform():
    continue
current_char.perform()
```

### 2.2 编排层

**现状**

```mermaid
flowchart LR
  "AutoCombatTask.run" --> "get_current_char().perform"
  "角色 do_perform" --> "switch_next_char 启发式选目标"
```

**变化**

```mermaid
flowchart LR
  "AutoCombatTask.run" --> "select_team_rotation"
  "select_team_rotation" -->|"匹配"| "TeamRotation.perform"
  "select_team_rotation" -->|"未匹配"| "get_current_char().perform"
  "TeamRotation.perform" --> "执行当前 Step"
  "执行当前 Step" --> "switch_to_char 固定目标"
  "switch_to_char 固定目标" --> "下一 Step"
```

流程约束：

- 匹配失败必须无副作用回退角色轴。
- 队伍轴每次只执行一个 step，保留现有战斗循环的 `in_combat()` 检查节奏。
- Step 内动作全部有时间上界，避免卡死自动战斗。
- 显式切人后同步 `is_current_char`、入场技标记和冻结时间统计。

### 2.3 挂载点

- `AutoCombatTask.default_config`：新增开关控制是否启用队伍轴。
- `AutoCombatTask.run()`：战斗循环优先尝试队伍轴。
- `BaseCombatTask`：新增固定目标切换接口供队伍轴使用。
- `src/team/`：新增通用队伍轴引擎与具体爱达千轴。

### 2.4 推进策略

1. 编排骨架：新增 `src/team` 基类、匹配入口和 `AutoCombatTask` 挂载点。
2. 固定切人：在 `BaseCombatTask` 增加 `switch_to_char`，并让原 `switch_next_char` 继续保留原行为。
3. 动作节点：实现通用 Action 到 `BaseChar` helper 的映射。
4. 具体队伍轴：按视频落 1 链爱弥斯、达妮娅、千咲启动轴和循环轴。
5. 验证：补队伍轴匹配/动作顺序/固定切人单测或最小语法校验。

### 2.5 结构健康度与微重构

文件级：`BaseCombatTask.py` 已偏大，但本次只新增固定切人入口，直接大拆会越过 feature 边界。选择最小抽取：把原 `switch_next_char` 的切换循环拆成可复用私有方法，再让固定目标接口复用它。

目录级：`src/char/` 已承载角色逻辑，队伍轴不是单个角色职责，新增 `src/team/`。本次不做更大目录重组。

超出范围观察：长期看 `BaseCombatTask` 可拆成 `CombatState`、`SwitchController`、`CooldownReader`，但这需要独立 `cs-refactor`。

## 3. 验收契约

- S1：当队伍包含 `Aemeath`、`Denia`、`Chisa` 且开关启用时，`AutoCombatTask.run()` 使用队伍轴，不调用当前角色默认角色轴。
- S2：队伍不匹配或开关关闭时，现有角色轴路径不变。
- S3：队伍轴启动时先执行启动轴；启动轴结束后执行循环轴并反复循环。
- S4：队伍轴能显式切到 plan 指定角色，而不是使用启发式下一个角色。
- S5：爱达千轴动作包含视频图中的启动轴和循环轴关键节点：`E/R/Q/2A/a2a3/a3a4/a4a5/强化E/重击/处决/变奏`。
- 反向核对：不新增识别模板；不改变非匹配队伍的切人策略。

## 4. 与项目级架构文档的关系

实现完成后需要更新 `.codestable/architecture/ARCHITECTURE.md`：补充自动战斗从“角色轴”扩展为“角色轴 + 可选队伍轴”的结构说明，并登记 `src/team/` 模块。
