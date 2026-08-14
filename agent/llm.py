import requests
import datetime
from config import CONFIG
from agent.json_utils import parse_llm_json

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
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )

        return answer

    def chat_json(self, prompt, fallback=None, validator=None):
        """调用LLM并保证返回合规JSON：提取→校验→失败自动重试一次→兜底fallback。"""
        repair_prompt = (
            prompt
            + "\n\n注意：你上次的输出不是合法JSON，或不符合要求的JSON结构。"
              "请重新输出，只输出JSON，不要包含任何解释、Markdown代码块或额外文字。"
        )
        for attempt in (1, 2):
            current_prompt = (
                prompt if attempt == 1 else repair_prompt
            )
            response = self.chat(current_prompt)
            try:
                return parse_llm_json(
                    response,
                    validator=validator
                )
            except ValueError:
                pass

        return fallback