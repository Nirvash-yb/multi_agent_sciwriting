from agent.baseagent import BaseAgent
from agent.llm import llm
import os
import json


class MethodAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MethodAgent"
        )
        self.llm = llm(name=self.name)

    # 接收Coordinator任务
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

        result = self.design(
            task
        )
        self.save_result(
            result
        )
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

    # 方法设计总入口
    def design(self, task, original_content=""):
        research_content = self.generate_research_content(
            task,
            original_content
        )
        technical_route = self.generate_technical_route(
            task,
            original_content
        )
        result = {
            "research_content":
                research_content,

            "technical_route":
                technical_route
        }
        return result

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
        content = ""
        for path in ["result/研究内容.txt", "result/技术路线.txt"]:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content += f"【{path}】\n" + f.read() + "\n"
        return content

    #生成研究内容
    def generate_research_content(self, task, original_content=""):
        prompt_template = self.load_prompt("prompt/method_research_content_prompt.txt")
        prompt = prompt_template.format(task=task)

        if original_content:
            prompt += (
                "\n\n【你的上一版正文】\n"
                + original_content
                + "\n请在上文基础上对相关内容进行修订，"
                  "未被任务涉及的部分保持原文不变。"
            )

        response = self.llm.chat(
            prompt
        )
        return response

    #生成技术路线
    def generate_technical_route(self, task, original_content=""):
        prompt_template = self.load_prompt("prompt/method_technical_route_prompt.txt")
        prompt = prompt_template.format(task=task)

        if original_content:
            prompt += (
                "\n\n【你的上一版正文】\n"
                + original_content
                + "\n请在上文基础上对相关内容进行修订，"
                  "未被任务涉及的部分保持原文不变。"
            )

        response = self.llm.chat(
            prompt
        )
        return response

    # 冲突修订：每个章节文件单独基于原文修改
    def revise(self, revision_task):
        return {
            "research_content":
                self.revise_file(
                    "result/研究内容.txt",
                    revision_task
                ),

            "technical_route":
                self.revise_file(
                    "result/技术路线.txt",
                    revision_task
                )
        }

    # 单个章节文件的修订
    def revise_file(self, path, revision_task):
        original = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                original = f.read()
        prompt_template = self.load_prompt(
            "prompt/agent_revision_prompt.txt"
        )
        prompt = prompt_template.format(
            original_content=original,
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

    #保存结果
    def save_result(self, result):

        path = "result"
        os.makedirs(
            path,
            exist_ok=True
        )
        with open(
            path + "/研究内容.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                result["research_content"]
            )
        with open(
            path + "/技术路线.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                result["technical_route"]
            )