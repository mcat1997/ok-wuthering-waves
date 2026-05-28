---
doc_type: feature-brainstorm
feature: 2026-05-28-team-rotation-profiles
status: confirmed
summary: 为少数特定队伍提供开发者配置的队伍级战斗轴/策略覆盖，并保留现有自动战斗作为回退。
tags: [combat, team, rotation, developer-config]
---

# 队伍级战斗轴 Profile Brainstorm

> Stage 0 | 2026-05-28 | 下一步：design

## 想做什么、为什么

项目现有自动战斗以角色识别后的 `BaseChar.perform()` 和 `BaseCombatTask._choose_switch_target()` 为核心：每个角色负责自己的动作，换人由通用规则按入场技、角色定位、buff 时间和角色自定义优先级决定。

想解决的问题是：有些固定队伍需要更具体的出手顺序或换人节奏，通用规则不够表达这些“队伍轴”。第一版目标不是做给普通用户自由编辑的宏系统，而是让开发者能为少数特定队伍写代码级 profile，先验证队伍级策略层是否能稳定接入现有战斗循环。

## 考虑过的方向

### 方向 A：精确固定轴

- 描述 / 价值 / 代价：为某个三人队写完整步骤序列，例如 A 入场、放技能、切 B、B 延奏、切 C 爆发。表达力最强，但最容易因识别失败、技能冷却、动作超时或战斗状态变化卡死。
- 结论：暂不选为第一版完整形态。可以吸收“必要动作顺序”的能力，但必须有超时和 fallback。

### 方向 B：队伍级策略覆盖

- 描述 / 价值 / 代价：识别到特定角色组合后启用对应 profile，profile 只接管必要的换人与动作顺序，其余仍走现有角色 `perform()` 和通用换人策略。实现成本和风险都可控，也能自然兼容现有角色类。
- 结论：选定。第一版以代码内 developer profile 形式落地。

### 方向 C：角色级增强

- 描述 / 价值 / 代价：不引入队伍层，只在特定角色遇到某些队友时改 `perform()` 或 `get_switch_priority()`。侵入面小，但队伍轴会散落在多个角色类里，后续很难看出“这套队伍到底怎么跑”。
- 结论：否决作为主方案。可作为 profile 内部调用角色能力的补充。

## 已敲定的设计点

- 已确认：第一版只做开发者配置，不做 YAML/JSON 文件配置，也不做 GUI 配置。
- 已确认：新增“队伍 profile”层；加载队伍角色后，根据识别到的角色组合匹配 profile。
- 已确认：profile 可以覆盖队伍级换人/动作顺序，但必须保留现有角色 `perform()` 与通用换人逻辑作为 fallback。
- 已确认：队伍匹配失败、当前角色识别不稳、动作不可用、动作超时、离开战斗等情况，不继续硬跑轴，回退默认自动战斗。
- 倾向：profile 接口先作为 Python 代码注册表存在，后续如果要开放给用户配置，再从这个接口抽象出 YAML/JSON schema。
- 倾向：第一版只覆盖少数明确队伍，不改变没有 profile 的队伍行为。

## 选定方向与遗留问题

选定方向是“队伍匹配 + 开发者配置 profile + 安全 fallback”。profile 是现有自动战斗循环上的一层可选覆盖：命中特定队伍才启用，执行不了就回到当前 `BaseChar.perform()` / `_choose_switch_target()` 体系。

明显不做：不做普通用户可编辑配置文件，不做 GUI，不做无限自由脚本语言，不要求一次支持所有队伍。

遗留给 design 的问题：

- profile 挂载点放在 `load_chars()` 之后、`get_current_char().perform()` 之前，还是封装成 `BaseCombatTask` 的可选策略对象？
- profile 的匹配 key 用角色类名、模板 label 名、还是标准化后的角色标识？
- profile 动作接口应暴露哪些最小安全动作：切人、执行当前角色默认 `perform()`、按技能、等待条件、fallback？
- fallback 的粒度是单步失败回默认逻辑，还是本轮战斗禁用 profile？
- 第一批用于验证的具体队伍要选哪一套？
