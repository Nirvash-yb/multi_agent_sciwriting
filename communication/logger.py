import json
import datetime

class CommunicationLogger:
    def __init__(self, max_summary_len=50):
        self.logs=[]
        self.llm_usage=[]
        self.max_summary_len = max_summary_len

    # 生成消息体摘要
    def _summarize(self, payload, max_len=None):
        if max_len is None:
            max_len = self.max_summary_len
        text = str(payload)
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    # 记录消息（打印控制台 + 存入self.logs）
    def record(self,message):
        summary = self._summarize(
            message.payload
        )
        entry = {
            "timestamp":
            message.timestamp,

            "sender":
            message.sender,

            "receiver":
            message.receiver,

            "message_type":
            message.message_type,

            "priority":
            message.priority,

            "payload_summary":
            summary
        }
        self.logs.append(entry)

    def save(self,path):
        with open(path,"w",
                  encoding="utf-8") as f:
            json.dump(
                self.logs,
                f,
                indent=4,
                ensure_ascii=False
            )

    # 记录一次LLM调用的token消耗
    def record_llm_usage(
            self,
            agent,
            prompt,
            prompt_tokens,
            completion_tokens,
            total_tokens):
        summary = self._summarize(
            prompt,
            max_len=80
        )
        entry = {
            "timestamp":
            datetime.datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "agent":
            agent,

            "prompt_summary":
            summary,

            "prompt_tokens":
            prompt_tokens,

            "completion_tokens":
            completion_tokens,

            "total_tokens":
            total_tokens
        }
        self.llm_usage.append(entry)
        print(
            f"[{agent}] LLM调用消耗token: "
            f"prompt={prompt_tokens}, "
            f"completion={completion_tokens}, "
            f"total={total_tokens}"
        )

    # 保存逐条LLM调用token记录
    def save_usage(self, path):
        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                self.llm_usage,
                f,
                indent=4,
                ensure_ascii=False
            )

    # 按Agent汇总token消耗并保存
    def save_usage_summary(self, path):
        summary = {}

        for entry in self.llm_usage:
            agent = entry["agent"]
            if agent not in summary:
                summary[agent] = {
                    "call_count": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            summary[agent]["call_count"] += 1
            summary[agent]["prompt_tokens"] += (
                entry["prompt_tokens"]
            )
            summary[agent]["completion_tokens"] += (
                entry["completion_tokens"]
            )
            summary[agent]["total_tokens"] += (
                entry["total_tokens"]
            )

        grand = {
            "call_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

        for agent, data in summary.items():
            for key in grand:
                grand[key] += data[key]

        output = {
            "by_agent": summary,
            "grand_total": grand
        }

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                output,
                f,
                indent=4,
                ensure_ascii=False
            )