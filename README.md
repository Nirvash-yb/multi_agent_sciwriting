# 多智能体科研基金申请书写作系统

基于多智能体协作与 LLM（DeepSeek）的科研基金申请书自动撰写系统。以 JSON 配置驱动，`python main.py` 一键运行。

## 系统架构

系统包含 6 个智能体，通过消息通信（`TASK_ASSIGN` / `QUERY` / `RESULT` / `CONFLICT` / `ACK`）协同完成任务：

| 智能体 | 职责 |
|---|---|
| CoordinatorAgent | 任务分解、任务分发、冲突协商调度（状态机 + 线程锁） |
| LiteratureAgent | 撰写「立项依据」章节 |
| MethodAgent | 撰写「研究内容」「技术路线」章节 |
| ExperimentAgent | 撰写「实验方案」「预期成果」章节 |
| CheckerAgent | 跨章节交叉审查，检测数据/参数/逻辑冲突 |
| WriterAgent | 最终统稿润色，生成 Markdown 申请书 |

### 消息调度

所有消息进入一个全局**优先级队列**，由固定数量（`config.json` 的 `max_threads`，默认 8）的 worker 线程并发处理：

- 优先级高的消息先出队（`HIGH` → `NORMAL` → `LOW`），同优先级按入队顺序先入先出
- 处理中产生的子消息也会进入队列，`wait_all` 会等待全部消息链处理完成

| 消息 | 默认优先级 |
|---|---|
| CONFLICT（冲突通知） | HIGH |
| QUERY（意见征集） | HIGH |
| REVISION 修订任务 | HIGH（分发时指定） |
| TASK_ASSIGN / RESULT | NORMAL |
| ACK | LOW |

### 工作流程

1. **任务分解**：Coordinator 调用 LLM 将研究主题分解为各正文 Agent 的撰写任务
2. **并行撰写**：Literature / Method / Experiment 三个正文 Agent 各自撰写章节
3. **交叉审查**：Checker 检查跨章节一致性，输出冲突列表（最多 `max_check_round` 个冲突数量）
4. **冲突协商**：对每个冲突，涉及 Agent 先输出修改意见 → Coordinator 用 LLM 裁决生成修订任务 → 分发各 Agent 修订 → 循环直至无冲突或达到最大轮数
5. **最终统稿**：Writer 整合五个章节生成 `最终申请书.md`
6. **分析可视**：生成通信时序图、负载图、消息类型分布、token 消耗图

## 目录结构

```
Agents/
├── main.py                     # 一键运行入口
├── config.json                 # 运行配置（含密钥，已 gitignore）
├── config.example.json         # 配置示例
├── agent/
│   ├── baseagent.py            # 消息通信基类（线程化）
│   ├── coordinator_agent.py    # 协调者（任务分解/冲突协商）
│   ├── literature_agent.py     # 文献调研（立项依据）
│   ├── method_agent.py         # 方法设计（研究内容/技术路线）
│   ├── experiment_agent.py     # 实验规划（实验方案/预期成果）
│   ├── checker_agent.py        # 数据核查（跨章节冲突检查）
│   ├── writer_agent.py         # 统稿润色
│   └── llm.py                  # LLM 调用封装
├── communication/
│   ├── message.py              # 消息类型与实体
│   ├── logger.py               # 通信日志 / token 统计
│   └── communicationanalyzer.py # 可视化分析
├── prompt/                     # 各 Agent 的提示词模板
├── result/                     # 各章节生成结果（运行产物）
├── temp/                       # 中间 JSON（运行产物）
├── logs/                       # 通信日志与 token 统计（运行产物）
└── analysis/                   # 可视化图表（运行产物）
```

## 安装与运行

```bash
pip install -r requirements.txt
```

1. 编辑 `config.json`（可复制 `config.example.json` 后填写）：

```json
{
    "api_key": "sk-你的DeepSeek密钥",
    "research_topic": "研究方向主题",
    "max_check_round": 1,
    "max_threads": 8
}
```

配置项说明：
- `api_key` —— DeepSeek API 密钥
- `research_topic` —— 研究主题（申请书题目）
- `max_check_round` —— 冲突协商最大轮数
- `max_threads` —— 消息并发处理 worker 线程数

2. 一键运行：

```bash
python main.py
```

## 输出

- `最终申请书.md` —— 最终生成的申请书
- `result/` —— 各正文 Agent 的章节初稿与修订稿
- `logs/messages.json` —— 全部通信记录
- `logs/llm_usage_summary.json` —— 各 Agent token 消耗汇总
- `analysis/*.png` —— 通信时序、负载、消息类型、token 消耗可视化