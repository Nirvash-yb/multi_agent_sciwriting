from agent.baseagent import BaseAgent
from agent.llm import llm
from communication.message import *

class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="WriterAgent"
        )
        self.llm = llm(name=self.name)

    # 收到最终统稿任务
    def handle_task_assign(self, message):
        content = self.load_content()
        result = self.write(content)
        self.save_result(
            result,
            "最终申请书.md"
        )
        self.send_result(
            self.agents["CoordinatorAgent"],
            "最终申请书生成完成"
        )

    # 读取5份正文
    def load_content(self):
        files = [
            "result/立项依据.txt",
            "result/研究内容.txt",
            "result/技术路线.txt",
            "result/实验计划.txt",
            "result/预期成果.txt"
        ]
        content = ""
        for path in files:
            with open(
                    path,
                    "r",
                    encoding="utf-8"
            ) as f:
                text = f.read()
            content += (
                f"\n\n========== {path} ==========\n\n"
            )
            content += text
        return content

    # 最终统稿
    def write(self, content):
        prompt_template = self.load_prompt(
            "prompt/writer_prompt.txt"
        )
        prompt = prompt_template.format(
            content=content
        )
        return self.llm.chat(prompt)

    # 加载Prompt
    def load_prompt(self, path):
        with open(
                path,
                "r",
                encoding="utf-8"
        ) as f:
            return f.read()

    # 保存最终申请书
    def save_result(self, result, path):
        with open(
                path,
                "w",
                encoding="utf-8"
        ) as f:
            f.write(result)