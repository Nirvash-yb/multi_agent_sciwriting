from agent.baseagent import BaseAgent
from agent.llm import llm
import os

class ExperimentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ExperimentAgent"
        )
        self.llm = llm(name=self.name)

    # 接收Coordinator任务
    def handle_task_assign(self, message):
        task = message.payload

        # REVISION类型：带原文重写自己的章节
        if isinstance(task, dict) and task.get("type") == "REVISION":
            revision_task = task.get("task", "")
            result = self.experiment(
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

        result = self.experiment(
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

    # 处理查询：针对冲突输出意见JSON并保存
    def handle_query(self, message):
        payload = message.payload
        suggestion = self.propose_suggestion(
            payload.get("description", ""),
            payload.get("related_content", [])
        )
        self.save_suggestion(suggestion)
        print(
            "[ExperimentAgent]已输出意见JSON"
        )
        self.send_result(
            self.agents[message.sender],
            suggestion,
            related_message_id=message.message_id
        )

    # 实验设计总入口
    def experiment(self, task, original_content=""):
        print(
            "ExperimentAgent开始设计实验方案"
        )
        experiment_plan = self.generate_experiment_plan(
            task,
            original_content
        )
        expected_results = self.generate_expected_results(
            task,
            original_content
        )
        result = {

            "experiment_plan":
                experiment_plan,

            "expected_results":
                expected_results
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
        for path in ["result/实验计划.txt", "result/预期成果.txt"]:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content += f"【{path}】\n" + f.read() + "\n"
        return content

    # 生成实验方案
    def generate_experiment_plan(self, task, original_content=""):
        prompt_template = self.load_prompt("prompt/experiment_plan_prompt.txt")
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

    # 生成预期成果
    def generate_expected_results(self, task, original_content=""):
        prompt_template = self.load_prompt("prompt/experiment_expected_results_prompt.txt")
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

    # 针对冲突输出意见JSON
    def propose_suggestion(self, description, related_content):
        print(
            "[ExperimentAgent]开始输出冲突意见JSON"
        )
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
        print(f"[ExperimentAgent]意见JSON已保存:{path}")

    # 保存结果
    def save_result(self, result):
        path = "result"
        os.makedirs(
            path,
            exist_ok=True
        )
        with open(
            path + "/实验计划.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                result["experiment_plan"]
            )
        with open(
            path + "/预期成果.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                result["expected_results"]
            )
        print(
            "ExperimentAgent结果保存完成"
        )