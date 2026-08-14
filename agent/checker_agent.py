from agent.baseagent import BaseAgent
from agent.llm import llm


class CheckerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CheckerAgent"
        )
        self.llm = llm(name=self.name)

    # 收到检查任务后开始交叉审查
    def handle_task_assign(self, message):
        self.check()

    # 读取文件
    def load_content(self, path):
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return f.read()

    # 加载Prompt
    def load_prompt(self, path):
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return f.read()

    # 交叉审查
    def check(self):
        files = {
            "LiteratureAgent": [
                "result/立项依据.txt"
            ],

            "MethodAgent": [
                "result/研究内容.txt",
                "result/技术路线.txt"
            ],

            "ExperimentAgent": [
                "result/实验计划.txt",
                "result/预期成果.txt"
            ]
        }
        content = {}

        # 读取所有Agent生成的正文
        for agent_name, paths in files.items():
            content[agent_name] = ""
            for path in paths:
                content[agent_name] += (
                    self.load_content(path)
                    + "\n"
                )

        # 构造交叉审查Prompt
        prompt_template = self.load_prompt(
            "prompt/checker_prompt.txt"
        )

        prompt = prompt_template.format(
            content=content
        )

        # 调用LLM
        conflicts = self.llm.chat_json(
            prompt,
            fallback={"conflicts": []}
        )

        # 发送冲突通知
        self.send_conflicts(conflicts)

    # 发送冲突通知
    def send_conflicts(self, conflicts):
        if not conflicts:
            return

        coordinator = self.agents.get("CoordinatorAgent")
        self.send_conflict(
            coordinator,
            conflicts
        )