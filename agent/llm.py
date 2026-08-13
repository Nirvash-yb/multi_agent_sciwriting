import requests
import datetime
from config import CONFIG

class llm:
    def __init__(self, name="unknown"):
        self.api_key = CONFIG.get("api_key", "")
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.model = "deepseek-chat"
        self.name = name
        self.logger = None

    def chat(self, prompt):
        headers = {
            "Authorization":
            f"Bearer {self.api_key}",

            "Content-Type":
            "application/json"
        }

        data = {
            "model": self.model,
            "messages":[
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=data
        )

        result = response.json()

        answer = (
            result["choices"][0]
            ["message"]
            ["content"]
        )

        # 记录本次调用消耗的token
        if self.logger:
            usage = result.get("usage", {})
            prompt_tokens = usage.get(
                "prompt_tokens", 0
            )
            completion_tokens = usage.get(
                "completion_tokens", 0
            )
            total_tokens = usage.get(
                "total_tokens", 0
            )
            self.logger.record_llm_usage(
                agent=self.name,
                prompt=prompt,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )

        return answer

# llm1 = llm()
# result = llm1.chat(
# """
# 你现在是多智能体科研协作系统中的 CoordinatorAgent。
#
# 你的任务是：
# 针对科研任务《基于多智能体强化学习的分布式计算资源调度方法研究》基金申请书，
# 将完整申请书撰写任务进行分解，并分配给5个子智能体协同完成。
#
# 申请书需要包含以下核心章节：
#
# 1. 立项依据
#    - 研究背景
#    - 国内外研究现状
#    - 当前研究问题与研究意义
#
# 2. 研究内容
#    - 主要研究目标
#    - 关键科学问题
#    - 具体研究内容
#
# 3. 技术路线
#    - 整体研究框架
#    - 多智能体强化学习模型设计
#    - 算法流程与关键技术
#
# 4. 实验方案
#    - 实验环境
#    - 数据集或仿真平台
#    - 对比方法
#    - 评价指标
#    - 预期实验结果
#
# 5. 预期成果
#    - 理论贡献
#    - 技术成果
#    - 论文、专利等产出
#
# 请将任务分配给以下5个智能体：
#
# 1. LiteratureAgent（文献调研智能体）
# 负责：
# - 完成立项依据部分
# - 调研国内外研究现状
# - 分析已有资源调度方法
# - 总结研究不足和创新需求
#
# 2. MethodAgent（方法设计智能体）
# 负责：
# - 完成研究内容和技术路线设计
# - 设计多智能体强化学习框架
# - 描述状态空间、动作空间、奖励函数
# - 提出算法流程
#
# 3. ExperimentAgent（实验规划智能体）
# 负责：
# - 完成实验方案设计
# - 规划实验环境和数据来源
# - 设计评价指标
# - 给出预期实验结果
#
# 4. CheckerAgent（数据/逻辑核查智能体）
# 负责：
# - 检查各章节之间逻辑一致性
# - 检查算法描述合理性
# - 检查实验方案与研究方法匹配性
# - 提出修改意见
#
# 5. WriterAgent（统稿润色智能体）
# 负责：
# - 汇总所有智能体结果
# - 组织基金申请书结构
# - 统一语言风格
# - 生成最终申请书文本
#
# 请输出JSON格式：
#
# {
#     "LiteratureAgent":{
#         "chapter":"",
#         "task":""
#     },
#     "MethodAgent":{
#         "chapter":"",
#         "task":""
#     },
#     "ExperimentAgent":{
#         "chapter":"",
#         "task":""
#     },
#     "CheckerAgent":{
#         "chapter":"",
#         "task":""
#     },
#     "WriterAgent":{
#         "chapter":"",
#         "task":""
#     }
# }
#
# 要求：
# 1. 只输出JSON
# 2. 每个task需要具体描述该智能体需要完成的工作
# 3. 不输出任何解释文字
# """
# )