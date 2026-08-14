from communication.message import Message, ACK, RESULT, TASK_ASSIGN, QUERY, CONFLICT, LOW, NORMAL, HIGH
import threading
import queue
import itertools
from config import CONFIG

class BaseAgent:
    # 全局消息优先级队列 + 固定数量worker
    _queue = queue.PriorityQueue()
    _workers = []
    _seq = itertools.count()
    _lazy_lock = threading.Lock()
    _workers_started = False

    def __init__(self, name):
        self.name = name
        self.message=None
        self.logger=None
        # 保存其他Agent对象
        self.agents = {}

    # 懒启动固定数量的worker线程（首次发消息或wait_all时触发）
    @classmethod
    def _ensure_workers(cls):
        base = BaseAgent
        if base._workers_started:
            return
        with base._lazy_lock:
            if base._workers_started:
                return
            max_workers = CONFIG.get("max_threads", 8)
            for _ in range(max(1, max_workers)):
                worker = threading.Thread(
                    target=base._worker_loop,
                    daemon=True
                )
                base._workers.append(worker)
                worker.start()
            base._workers_started = True

    # worker循环：按优先级从队列取消息处理，收到哨兵即退出
    @classmethod
    def _worker_loop(cls):
        base = BaseAgent
        while True:
            _, _, receiver, message = base._queue.get()
            try:
                if message is None:
                    break
                receiver.receive_message(message)
            finally:
                base._queue.task_done()

    # 等待所有消息处理完成（含处理过程中入队的新消息），随后停止worker
    @classmethod
    def wait_all(cls):
        base = BaseAgent
        cls._ensure_workers()
        base._queue.join()
        for _ in base._workers:
            base._queue.put((0, next(base._seq), None, None))
        for worker in base._workers:
            worker.join()

    # 注册Agent
    def register_agent(self, agent):
        self.agents[agent.name] = agent

    #接受消息
    def receive_message(self, message):
        if message.message_type != ACK:
            self.send_ack(
                self.agents[message.sender],
                f"{self.name}确认收到",
                related_message_id=message.message_id
            )
        #按消息类型分发
        if message.message_type == TASK_ASSIGN:
            self.handle_task_assign(message)
        elif message.message_type == RESULT:
            self.handle_result(message)
        elif message.message_type == QUERY:
            self.handle_query(message)
        elif message.message_type == CONFLICT:
            self.handle_conflict(message)
        elif message.message_type == ACK:
            self.handle_ack(message)

    #默认处理器，子类按需覆写
    def handle_task_assign(self, message):
        pass

    def handle_result(self, message):
        pass

    def handle_query(self, message):
        pass

    def handle_conflict(self, message):
        pass

    def handle_ack(self, message):
        pass

    # 各类型专用发送方法
    def send_task_assign(self, receiver, payload, related_message_id=None, priority=NORMAL):
        self.send_message(receiver, TASK_ASSIGN, payload, priority=priority, related_message_id=related_message_id)

    def send_result(self, receiver, payload, related_message_id=None, priority=NORMAL):
        self.send_message(receiver, RESULT, payload, priority=priority, related_message_id=related_message_id)

    def send_query(self, receiver, payload, related_message_id=None, priority=HIGH):
        self.send_message(receiver, QUERY, payload, priority=priority, related_message_id=related_message_id)

    def send_conflict(self, receiver, payload, related_message_id=None, priority=HIGH):
        self.send_message(receiver, CONFLICT, payload, priority=priority, related_message_id=related_message_id)

    def send_ack(self, receiver, payload, related_message_id=None, priority=LOW):
        self.send_message(receiver, ACK, payload, priority=priority, related_message_id=related_message_id)

    # 组装消息并发送（入优先级队列，取负值使HIGH先出队；同优先级按seq先进先出）
    def send_message(self, receiver, msg_type, payload, priority=LOW, related_message_id=None):
        message = Message(self.name, receiver.name, msg_type, payload, priority=priority, related_message_id=related_message_id)

        if self.logger:
            self.logger.record(message)

        self._ensure_workers()
        self._queue.put(
            (-priority, next(self._seq), receiver, message)
        )