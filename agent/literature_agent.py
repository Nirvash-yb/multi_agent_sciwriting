from agent.baseagent import BaseAgent
from agent.llm import llm
import os

class LiteratureAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="LiteratureAgent")
        self.llm = llm(name=self.name)

    def handle_task_assign(self, message):
        print(f"{self.name}收到任务:{message.payload}")

        task = message.payload

        # REVISION类型：带原文重写自己的章节
        if isinstance(task, dict) and task.get("type") == "REVISION":
            revision_task = task.get("task", "")
            result = self.research(
                revision_task,
                original_content=self.load_own_content()
            )
            self.save_result(result)
            self.send_result(
                self.agents[message.sender],
                result,
                related_message_id=message.message_id
            )
            return

        result = self.research(task)

        self.save_result(result)
        self.send_result(
            self.agents[message.sender],
            result,
            related_message_id=message.message_id
        )

    # 处理查询：针对冲突输出意见JSON并保存
    def handle_query(self, message):
        payload = message.payload
        suggestion = self.propose_suggestion(
            payload.get("description", ""),
            payload.get("related_content", [])
        )
        self.save_suggestion(suggestion)
        print(
            f"{self.name}已输出意见JSON"
        )
        self.send_result(
            self.agents[message.sender],
            suggestion,
            related_message_id=message.message_id
        )

    #加载prompt
    def load_prompt(self, path):
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return f.read()

    # 读取自己的章节内容
    def load_own_content(self):
        path = "result/立项依据.txt"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def research(self, task, original_content=""):
        print(f"{self.name}开始调用LLM生成正文")

        prompt_template = self.load_prompt("prompt/literature_prompt.txt")
        prompt = prompt_template.format(task=task)

        if original_content:
            prompt += (
                "\n\n【你的上一版正文】\n"
                + original_content
                + "\n请在上文基础上对相关内容进行修订，"
                  "未被任务涉及的部分保持原文不变。"
            )

        response = self.llm.chat(prompt)
        return response

    # 针对冲突输出意见JSON
    def propose_suggestion(self, description, related_content):
        print(f"{self.name}开始输出冲突意见JSON")
        prompt_template = self.load_prompt(
            "prompt/agent_suggestion_prompt.txt"
        )
        prompt = prompt_template.format(
            description=description,
            related_content=related_content,
            my_content=self.load_own_content()
        )
        return self.llm.chat(prompt)

    # 保存意见JSON
    def save_suggestion(self, suggestion):
        os.makedirs("temp", exist_ok=True)
        path = f"temp/{self.name}_suggestion.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(suggestion)
        print(f"{self.name}意见JSON已保存:{path}")

    def save_result(self, content):
        path = "result"
        os.makedirs(
            path,
            exist_ok=True
        )
        filename = path + "/立项依据.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"{self.name}结果已保存:{filename}")