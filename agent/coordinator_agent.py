import json
import threading
from agent.baseagent import BaseAgent
from agent.llm import llm
from communication.message import *
from config import CONFIG
import os

class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CoordinatorAgent"
        )
        self.llm = llm(name=self.name)
        # 任务要求
        self.tasks = {}
        self.task_status = {}
        # 检查轮次
        self.check_round = 0
        self.max_check_round = CONFIG.get("max_check_round", 1)
        # 待处理冲突队列
        self.pending_conflicts = []
        # 是否正处于冲突修正阶段
        self.fixing_conflicts = False
        # 当前处理的冲突
        self.current_conflict = None
        # 当前阶段: collect_suggestions / apply_solution
        self.phase = None
        # 各Agent返回的意见
        self.suggestions = {}
        # 等待响应的Agent列表
        self.awaiting_agents = []
        # 线程锁，保证状态机串行
        self.lock = threading.Lock()

    # 加载prompt
    def load_prompt(self, path):
        with open(
                path,
                "r",
                encoding="utf-8"
        ) as f:
            return f.read()

    # 开始写初稿
    def start_write(self, task):
        self.decompose_task(task, "prompt/coordinator_prompt.txt")
        self.assign_task()

    # 任务分解
    def decompose_task(self, task, path):
        prompt_template = self.load_prompt(path)
        prompt = prompt_template.format(
            research_topic=task
        )
        response = self.llm.chat(prompt)
        self.tasks = json.loads(response)
        self.save_result(self.tasks, "temp/ctecbiyresult.json")

    # 分发初始任务
    def assign_task(self):
        self.task_status = {
            agent_name: False
            for agent_name in self.tasks
        }
        for agent_name, task in self.tasks.items():
            agent = self.agents[agent_name]
            self.send_task_assign(agent, task)

    # 处理RESULT
    def handle_result(self, message):
        with self.lock:
            if self.fixing_conflicts:
                self._handle_conflict_result(message)
            else:
                self._handle_initial_result(message)

    # 初始撰写阶段的结果处理
    def _handle_initial_result(self, message):
        agent_name = message.sender
        if agent_name in self.task_status:
            self.task_status[agent_name] = True
            print(
                f"{agent_name} 已完成初稿"
            )
            if all(self.task_status.values()):
                print(
                    "[CoordinatorAgent] "
                    "所有正文Agent已完成初稿，首次调用Checker"
                )
                self.notify_checker()

    # 冲突修正阶段的结果处理
    def _handle_conflict_result(self, message):
        agent_name = message.sender

        if self.phase == "collect_suggestions":
            self.suggestions[agent_name] = message.payload
            print(
                f"[CoordinatorAgent] 已收集 "
                f"{agent_name} 的意见"
            )
            if all(
                    name in self.suggestions
                    for name in self.awaiting_agents
            ):
                self.dispatch_conflict_tasks()

        elif self.phase == "apply_solution":
            if agent_name in self.awaiting_agents:
                self.awaiting_agents.remove(agent_name)
                print(
                    f"[CoordinatorAgent] "
                    f"{agent_name} 已完成冲突修订写稿"
                )
                if not self.awaiting_agents:
                    # 当前冲突解决，处理下一个
                    self.process_next_conflict()

    # 收到Checker冲突通知
    def handle_conflict(self, message):
        with self.lock:
            conflicts = message.payload
            conflict_list = (
                conflicts.get("conflicts", [])
                if isinstance(conflicts, dict)
                else []
            )

            # 无冲突：进入Writer
            if not conflict_list:
                print(
                    "[CoordinatorAgent] 未发现冲突"
                )
                self.notify_writer()
                return

            # 达到最大轮次：停止自动修改，进入Writer
            if self.check_round >= self.max_check_round:
                print(
                    "[CoordinatorAgent] "
                    f"达到最大冲突修改轮次({self.check_round})，停止自动修改"
                )
                self.notify_writer()
                return

            print(
                f"[CoordinatorAgent] "
                f"发现 {len(conflict_list)} 个冲突，开始逐条协商解决"
            )
            self.pending_conflicts = list(conflict_list)
            self.fixing_conflicts = True
            self.process_next_conflict()

    # 处理下一个冲突
    def process_next_conflict(self):
        # 全部冲突已解决：未达上限则重新调用Checker，已达上限直接进入Writer
        if not self.pending_conflicts:
            self.fixing_conflicts = False
            self.current_conflict = None
            self.phase = None
            self.suggestions = {}
            self.check_round += 1
            if self.check_round < self.max_check_round:
                print(
                    "[CoordinatorAgent] "
                    "本轮所有冲突已解决，重新调用Checker检查"
                )
                self.notify_checker()
            else:
                print(
                    "[CoordinatorAgent] "
                    f"达到最大冲突修改轮次({self.check_round})，进入Writer"
                )
                self.notify_writer()
            return

        conflict = self.pending_conflicts.pop(0)
        self.current_conflict = conflict
        self.phase = "collect_suggestions"
        self.suggestions = {}

        agents = conflict.get("agents", [])
        self.awaiting_agents = list(agents)

        print(
            "[CoordinatorAgent] "
            f"处理冲突（剩余{len(self.pending_conflicts)}个）："
        )
        print(f"涉及Agent: {agents}")
        print(f"描述: {conflict.get('description', '')}")
        print(f"相关章节: {conflict.get('related_content', [])}")

        # 分发意见征集任务（仅包含描述和相关章节）
        request = {
            "type": "SUGGESTION_REQUEST",
            "description": conflict.get(
                "description", ""
            ),
            "related_content": conflict.get(
                "related_content", []
            )
        }
        for agent_name in self.awaiting_agents:
            agent = self.agents[agent_name]
            self.send_query(agent, request)
            print(
                f"[CoordinatorAgent] "
                f"已请 {agent_name} 对该冲突给出意见"
            )

    # 收集完意见后，调用LLM得到分发任务JSON
    def dispatch_conflict_tasks(self):
        print(
            "[CoordinatorAgent] "
            "已收集全部意见，调用LLM生成分发任务"
        )
        agents = self.current_conflict.get("agents", [])
        prompt_template = self.load_prompt(
            "prompt/coordinator_solution_prompt.txt"
        )
        prompt = prompt_template.format(
            description=self.current_conflict.get(
                "description", ""
            ),
            related_content=self.current_conflict.get(
                "related_content", []
            ),
            suggestions=self.suggestions,
            agents=agents
        )
        response = self.llm.chat(prompt)
        conflict_tasks = json.loads(response)

        # 保存分发任务JSON
        self.save_result(
            conflict_tasks,
            "temp/conflict_tasks.json"
        )
        print(
            f"[CoordinatorAgent] "
            f"分发任务已保存并下发"
        )

        self.phase = "apply_solution"
        self.awaiting_agents = list(conflict_tasks.keys())

        # 像初稿一样分发下去写，只告诉子Agent修改目标
        for agent_name, task in conflict_tasks.items():
            agent = self.agents[agent_name]
            self.send_task_assign(
                agent,
                {
                    "type": "REVISION",
                    "task": task
                },
                priority=HIGH
            )
            print(
                f"[CoordinatorAgent] "
                f"已将修订任务分发给 {agent_name}"
            )

    # 检查正文
    def notify_checker(self):
        checker = self.agents["CheckerAgent"]
        self.send_task_assign(
            checker,
            "检查所有正文Agent生成的内容"
        )

    # 整合正文
    def notify_writer(self):
        writer = self.agents.get(
            "WriterAgent"
        )
        self.send_task_assign(
            writer,
            "所有正文已经完成协商和交叉审查，请进行最终整合。"
        )
        print(
            "[CoordinatorAgent] "
            "已通知WriterAgent进行最终整合"
        )

    def save_result(self, result, path):
        os.makedirs(
            os.path.dirname(path),
            exist_ok=True
        )
        with open(
                path,
                "w",
                encoding="utf-8"
        ) as f:
            json.dump(
                result,
                f,
                ensure_ascii=False,
                indent=4
            )