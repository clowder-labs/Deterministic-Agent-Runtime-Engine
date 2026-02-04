# Agent Design: SimpleChatAgent

> Scope: `dare_framework/agent/simple_chat.py`

## 1. 设计定位

- 最轻量的单次模型调用，适合无工具、无规划的简单问答。

## 2. 核心流程

- 写入用户输入 → assemble → 单次模型调用 → 写回 STM → 返回结果。

## 3. 限制

- 无工具调用、无计划、无验证闭环。
