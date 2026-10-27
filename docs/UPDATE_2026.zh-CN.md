# Agent Zero to Hero：2026 年 10 月更新说明

核查日期：**2026-10-26**。本次基于仓库 2026-06-02 的提交 `179d6b38f137a46e33328958a014e60cb6038b2a`，保留英文课程正文，并提供这份中文导读。

## 更新方向

原教程最值得保留的是从一个模型调用开始，逐步拆开工具循环、上下文、会话和协议的教学方式。新版把这条主线延伸到三个问题：**怎样证明任务完成、谁有权执行动作、失败以后怎样继续**。

这次已经修改了文档和相关代码，不只是一份选题建议。建议先读 [新版课程入口](../README.md)，再读 [2026 Field Guide](FIELD_GUIDE_2026.md)。后者把模型接口、运行时、上下文、Skills、MCP、A2A、评测和可靠性放在一张工程地图里。

## 新增的学习内容

| 内容 | 交付形式 | 解决的问题 |
|---|---|---|
| [17b：Responses API](../chapters/ch17b_responses.md) | Python 示例及离线测试 | 正确处理调用 ID、续接状态、异常响应和预算 |
| [18：Evaluation](../chapters/ch18_evaluation.md) | 设计章节、可运行的本地示例、验收作业 | 把“回答看起来很好”与“任务真的完成”分开 |
| [19：Permissions](../chapters/ch19_permissions.md) | 设计章节、策略示例、攻击情境 | 将用户授权、文档内容和执行权限分开 |
| [20：Durable execution](../chapters/ch20_durable_execution.md) | 设计章节、SQLite 示例、故障注入作业 | 处理“外部动作已成功，但本地没保存结果”的不确定状态 |

后三章明确标为阅读与设计实验，不假装已经把生产级子系统装进 `agent.py`。原七周课程保留，并增加可选的两周可靠性模块；课程大纲、作业验收标准和答案索引也已更新。

## 检索中最值得注意的变化

**接口已经不能只靠改模型名字来升级。** OpenAI 文档区分 Responses、Agents SDK 和托管 Agents API；Gemini 当前文档也使用 Interactions 和相应的状态处理方式。新版增加一个直接使用 HTTP 的 Responses 实验，同时把旧的 Chat Completions／`generateContent` 适配器标明为有限的教学示例。[OpenAI 官方指南](https://developers.openai.com/api/docs/guides/agents)、[Gemini 官方概览](https://ai.google.dev/gemini-api/docs/interactions-overview)。

**MCP 的版本边界必须明确。** 原例子固定为 `2024-11-05`，而官方已发布 `2026-07-28` 稳定规范，生命周期等语义已有变化。因此保留旧版字节级实验，并新增 [MCP 版本说明](MCP_VERSIONS.md)，没有通过只改版本字符串来假装完成迁移。[官方稳定版发布记录](https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28)。

**SDK 升级也可能改变 API 版本。** Anthropic Python SDK 2.x 默认使用 `2026-10-21`，原始 HTTP 章节仍显式指定 `2023-06-01`；后者仍是文档记录的可用选项。新版说明了这个差异并保存本次离线测试依赖，避免把“测试通过”误说成所有线上配置都已验证。[官方迁移说明](https://platform.claude.com/docs/en/api/migration-2026-10-21)。

**评测方法应该长期保留，某个评测产品不应该成为教材的唯一入口。** OpenAI 已公布 Evals 和 Agent Builder 的产品退役安排，所以新章节采用可迁移的任务、试验、结果检查和本地 grader 方法。[官方退役说明](https://developers.openai.com/api/docs/deprecations)。完整一手资料和核查日期见 [来源索引](SOURCES.md)。

## 修正了哪些原文问题

修正了“相邻 user 消息必然报错”、缓存前缀顺序、缓存阈值，以及把可见说明文本当成内部推理的说法。去掉了缺少可复现记录的固定成本、五倍／十倍省钱承诺；说明 Skill 读取一次后仍可能反复进入后续输入。

同时增加真实能力对照表：原来的 `agent.py` 没有集成所有独立章节的 Skills、MCP、子 Agent 和多模型功能。新版明确列出已经实现与仍属于练习的部分，保留教程的可读性。

## 与文档配套的修复

1. 新的 compaction 记录保存完整快照，重启可以恢复压缩后的会话。旧日志中没保存过的摘要无法凭空补回。
2. 流式工具参数等待最终停止状态后再解析，并在整批校验完成后才执行，避免一部分参数损坏时已经执行前面的动作。
3. 截断、拒绝和不支持的停止状态得到明确处理；新增 Responses 示例还检查 HTTP 状态、调用预算和参数范围。

本次没有把教学 CLI 改造成框架，也没有声称完成权限沙箱、外部动作事务或所有提供商的完整兼容层。剩余问题有单独的 [工程清单](WISHLIST.md)，每项附建议验收条件。

## 已验证与未验证

原基线 **42 项测试通过**；更新版 **78 项离线测试通过**，新增 36 项，Ruff 检查通过。新阅读实验中的完整 Python 示例也在本地执行通过。详细环境和验证范围见 [VALIDATION.md](VALIDATION.md)。

没有执行付费模型请求，没有给当前远程 MCP／A2A 服务做互操作认证，也没有测量新模型的真实任务成功率。原有图片和宣传视频保留，里面的历史计数或价格口号以新版正文为准。
