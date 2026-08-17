from agent.baseagent import BaseAgent
from agent.llm import llm
import os
import json


class ExperimentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ExperimentAgent"
        )
        self.llm = llm(name=self.name)
        self.chapter_files = {
            "experiment_plan": "result/实验计划.txt",
            "expected_results": "result/预期成果.txt"
        }

    # 接收Coordinator任务
    def handle_task_assign(self, message):
        task = message.payload

        # REVISION类型：按chapter只修改对应章节
        if isinstance(task, dict) and task.get("type") == "REVISION":
            revision_task = task.get("task", "")
            chapter = task.get("chapter")

            result = self.revise(
                revision_task,
                chapter
            )

            self.save_result(result)

            self.send_result(
                self.agents[message.sender],
                result,
                related_message_id=message.message_id
            )
            return

        result = self.experiment(task)

        self.save_result(result)

        self.send_result(
            self.agents[message.sender],
            result,
            related_message_id=message.message_id
        )

    # 处理查询：针对冲突输出意见
    def handle_query(self, message):
        payload = message.payload

        related_content = payload.get(
            "related_content",
            []
        )

        # 只保留属于ExperimentAgent的章节
        my_chapters = [
            chapter
            for chapter in related_content
            if chapter in self.chapter_files
        ]

        suggestion = self.propose_suggestion(
            payload.get("description", ""),
            payload.get("related_excerpt", {}),
            my_chapters
        )

        self.send_query(
            self.agents[message.sender],
            suggestion,
            related_message_id=message.message_id
        )

    # 实验设计总入口
    def experiment(self, task):
        experiment_plan = self.generate_experiment_plan(
            task
        )

        expected_results = self.generate_expected_results(
            task
        )

        result = {
            "experiment_plan":
                experiment_plan,

            "expected_results":
                expected_results
        }

        return result

    # 加载Prompt
    def load_prompt(self, path):
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return f.read()

    # 读取指定章节内容
    def load_own_content(self, chapter):
        path = self.chapter_files.get(chapter)

        if not path or not os.path.exists(path):
            return ""

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return f"【{path}】\n" + f.read() + "\n"

    # 生成实验方案
    def generate_experiment_plan(self, task):
        prompt_template = self.load_prompt(
            "prompt/experiment_plan_prompt.txt"
        )

        prompt = prompt_template.format(
            task=task
        )

        response = self.llm.chat(
            prompt
        )

        return response

    # 生成预期成果
    def generate_expected_results(self, task):
        prompt_template = self.load_prompt(
            "prompt/experiment_expected_results_prompt.txt"
        )

        prompt = prompt_template.format(
            task=task
        )

        response = self.llm.chat(
            prompt
        )

        return response

    # 冲突修订：按chapter只修改对应章节
    def revise(self, revision_task, chapter=None):
        if chapter and chapter in self.chapter_files:
            return {
                chapter: self.revise_file(
                    self.chapter_files[chapter],
                    revision_task
                )
            }

        return {
            name: self.revise_file(
                path,
                revision_task
            )
            for name, path in self.chapter_files.items()
        }

    # 单个章节文件的修订
    def revise_file(self, path, revision_task):
        original = ""

        if os.path.exists(path):
            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:
                original = f.read()

        prompt_template = self.load_prompt(
            "prompt/agent_revision_prompt.txt"
        )

        prompt = prompt_template.format(
            original_content=original,
            revision_task=revision_task
        )

        return self.llm.chat(
            prompt
        )

    # 针对冲突输出意见
    def propose_suggestion(
        self,
        description,
        related_excerpt,
        chapters
    ):
        prompt_template = self.load_prompt(
            "prompt/agent_suggestion_prompt.txt"
        )

        excerpt_text = json.dumps(
            related_excerpt,
            ensure_ascii=False,
            indent=2
        )
        my_content = ""
        for chapter in chapters:
            my_content += self.load_own_content(
                chapter
            )
        prompt = prompt_template.format(
            name=self.name,
            description=description,
            related_excerpt=excerpt_text,
            my_content=my_content
        )

        return self.llm.chat(
            prompt
        )

    # 保存结果
    def save_result(self, result):
        path = "result"

        os.makedirs(
            path,
            exist_ok=True
        )

        for chapter, content in result.items():
            if chapter in self.chapter_files:
                with open(
                    self.chapter_files[chapter],
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(content)