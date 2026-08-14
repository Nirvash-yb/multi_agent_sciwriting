import threading
from agent.baseagent import BaseAgent
from agent.llm import llm
from communication.message import *
from config import CONFIG

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
        self.max_check_round = CONFIG.get("max_check_round", 2)
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
        self.awaiting_agents_suggestions = []
        self.awaiting_agents_revisions = []
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
        self.tasks = self.llm.chat_json(
            prompt,
            fallback={}
        )

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
            if all(self.task_status.values()):
                self.notify_checker()

    # 冲突修正阶段的结果处理
    def _handle_conflict_result(self, message):
        agent_name = message.sender

        if self.phase == "apply_solution":
            if agent_name in self.awaiting_agents_revisions:
                self.awaiting_agents_revisions.remove(agent_name)
                if not self.awaiting_agents_revisions:
                    # 当前冲突解决，处理下一个
                    self.process_next_conflict()

    # 处理子Agent的QUERY回复
    def handle_query(self, message):
        with self.lock:
            if not self.fixing_conflicts:
                return
            if self.phase != "collect_suggestions":
                return
            agent_name = message.sender
            if agent_name not in self.awaiting_agents_suggestions:
                return

            self.suggestions[agent_name] = message.payload
            if all(
                    name in self.suggestions
                    for name in self.awaiting_agents_suggestions
            ):
                self.dispatch_conflict_tasks()

    # 收到Checker冲突通知
    def handle_conflict(self, message):
        with self.lock:
            conflicts = message.payload
            conflict_list = (
                conflicts.get("conflicts", [])
                if isinstance(conflicts, dict)
                else []
            )
            self.check_round+=1

            # 无冲突：进入Writer，或者最大轮次
            if not conflict_list or self.check_round > self.max_check_round:
                self.notify_writer()
                return

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
            self.awaiting_agents_revisions = []
            self.awaiting_agents_suggestions = []

            if self.check_round < self.max_check_round:
                self.notify_checker()
            else:
                self.notify_writer()
            return

        conflict = self.pending_conflicts.pop(0)
        self.current_conflict = conflict
        self.phase = "collect_suggestions"
        self.suggestions = {}

        agents = conflict.get("agents", [])
        self.awaiting_agents_suggestions = list(agents)

        # 分发意见征集任务（仅包含描述、相关章节和相关冲突段）
        request = {
            "description": conflict.get(
                "description", ""
            ),
            "related_content": conflict.get(
                "related_content", []
            ),
            "related_excerpt": conflict.get(
                "related_excerpt", {}
            )
        }
        for agent_name in self.awaiting_agents_suggestions:
            agent = self.agents[agent_name]
            self.send_query(agent, request)

    # 收集完意见后，调用LLM得到分发任务JSON
    def dispatch_conflict_tasks(self):
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
        conflict_tasks = self.llm.chat_json(
            prompt,
            fallback={}
        )

        self.phase = "apply_solution"
        self.awaiting_agents_revisions = list(conflict_tasks.keys())

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
