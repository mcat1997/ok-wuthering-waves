---
doc_type: issue-report
issue: 2026-05-29-team-axis-video-gap
status: confirmed
severity: P1
summary: 爱达千队伍轴实战表现与教学视频差距明显，关键技能空放后仍继续推进
tags: [combat, team-axis, rotation]
---

# 爱达千队伍轴偏离教学视频 Issue Report

## 1. 问题现象

使用 1 链爱弥斯、达妮娅、千咲队伍轴实战时，自动战斗的动作节奏和教学视频差距明显。日志显示队伍轴按声明顺序推进，但多个关键节点返回失败，例如达妮娅启动段 `R`、千咲 `强化E`、达妮娅 `强化E/R2`、爱弥斯启动段 `R1/R2`。

## 2. 复现步骤

1. 启动当前实现的 Auto Combat，并启用 `Use Team Axis`。
2. 使用爱弥斯、达妮娅、千咲队伍进入战斗。
3. 对照 `/Users/a38999/Downloads/爱达千5R教学.mp4` 观察自动战斗表现。
4. 查看 `/Users/a38999/Downloads/ok-script.log` 中 `TeamRotation` 日志。
5. 观察到：队伍轴继续推进，但部分关键动作返回 `False`，实战视频 `/Users/a38999/Downloads/飞书20260529-104413.mp4` 的表现和教学轴明显不一致。

复现频率：已在用户提供的一次实战日志和视频中复现。

## 3. 期望 vs 实际

**期望行为**：队伍轴应尽量贴近教学视频，至少保证变奏后的爱弥斯能释放启动段 R1，并减少 E/R/强化E 在动画锁期间直接空判失败。

**实际行为**：队伍轴只按计划顺序推进，缺少角色入场状态补账和动作前后摇等待，导致关键技能失败后后续步骤仍按错误状态继续。

## 4. 环境信息

- 涉及模块 / 功能：Auto Combat 队伍轴
- 相关文件 / 函数：`src/team/TeamRotation.py`、`src/team/aemeath_denia_chisa.py`
- 运行环境：Windows 打包运行日志，仓库本地分析
- 其他上下文：实战视频、教学视频、`ok-script.log`

## 5. 严重程度

**P1** — 核心队伍轴能力可运行但关键动作偏离教学轴，影响该队伍轴实用性。

## 备注

日志关键证据：

- 启动段达妮娅 `R` 返回 `False`。
- 启动段千咲 `强化E` 返回 `(False, 0, False)`。
- 启动段达妮娅 `强化E/R2` 返回失败。
- 启动段爱弥斯 `R1/R2` 返回 `False`。
