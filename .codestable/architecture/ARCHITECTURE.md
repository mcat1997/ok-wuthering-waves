# ok-ww 架构总入口

> 状态：骨架（待填充）
> 创建日期：2026-05-29

## 1. 项目简介

ok-ww 是一个基于图像识别的鸣潮自动化程序，支持后台运行，基于 ok-script 开发。

## 2. 核心概念 / 术语表

- 角色轴：默认自动战斗模式，由当前角色的 `BaseChar.do_perform()` 决定本角色动作，再通过 `BaseCombatTask.switch_next_char()` 按角色定位、buff 和协奏状态选择下一个角色。
- 队伍轴：可选自动战斗模式，由 `src/team/` 中的 `TeamRotation` 按整队成员匹配启动轴和循环轴；匹配失败时回退角色轴。
- 显式切人：队伍轴通过 `BaseCombatTask.switch_to_char()` 切到 plan 指定角色，区别于角色轴的启发式 `switch_next_char()`。

## 3. 子系统 / 模块索引

- `src/task/AutoCombatTask.py`：自动战斗入口。战斗循环优先尝试匹配队伍轴，未匹配时执行角色轴。
- `src/task/BaseCombatTask.py`：战斗通用能力。包含角色加载、协奏读取、默认切人和队伍轴使用的显式切人入口。
- `src/char/`：角色轴实现目录，每个角色类封装自身 `do_perform()`。
- `src/team/`：队伍轴实现目录，包含通用 `TeamRotation` 引擎和具体队伍 plan。

## 4. 关键架构决定

- 自动战斗保持“队伍轴优先、角色轴兜底”：只有当前队伍命中 `TeamRotation.required_char_classes` 且任务配置启用 `Use Team Axis` 时才进入队伍轴。
- 队伍轴只编排跨角色时序，不接管角色识别、战斗识别、技能 UI 识别和冷却读取。
- 固定目标切人复用 `BaseCombatTask` 的切换循环，避免另写一套输入和入场技状态同步逻辑。

## 5. 已知约束 / 硬边界

- 队伍轴动作粒度是可自动化的技能/普攻/重击/等待，不承诺复刻教学视频逐帧时机。
- 新队伍轴应优先新增 `src/team/{team}.py` 的 plan，不要把跨角色流程塞进单个 `src/char/*.py`。
