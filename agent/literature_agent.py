from agent.baseagent import BaseAgent
from agent.llm import llm
import os
import json

class LiteratureAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="LiteratureAgent")
        self.llm = llm(name=self.name)

    def handle_task_assign(self, message):
        task = message.payload

        # REVISION类型：带原文重写自己的章节
        if isinstance(task, dict) and task.get("type") == "REVISION":
            revision_task = task.get("task", "")
            result = self.revise(revision_task)
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

    # 处理查询：针对冲突输出意见JSON
    def handle_query(self, message):
        payload = message.payload
        suggestion = self.propose_suggestion(
            payload.get("description", ""),
            payload.get("related_excerpt", {})
        )
        self.send_query(
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

    # 冲突修订：基于原文修改
    def revise(self, revision_task):
        prompt_template = self.load_prompt(
            "prompt/agent_revision_prompt.txt"
        )
        prompt = prompt_template.format(
            original_content=self.load_own_content(),
            revision_task=revision_task
        )
        return self.llm.chat(prompt)

    # 针对冲突输出意见JSON
    def propose_suggestion(self, description, related_excerpt):
        prompt_template = self.load_prompt(
            "prompt/agent_suggestion_prompt.txt"
        )
        excerpt_text = json.dumps(
            related_excerpt,
            ensure_ascii=False,
            indent=2
        )
        prompt = prompt_template.format(
            description=description,
            related_excerpt=excerpt_text,
            my_content=self.load_own_content()
        )
        return self.llm.chat(prompt)

    def save_result(self, content):
        path = "result"
        os.makedirs(
            path,
            exist_ok=True
        )
        filename = path + "/立项依据.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)