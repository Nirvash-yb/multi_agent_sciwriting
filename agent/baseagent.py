from communication.message import Message, ACK, RESULT, TASK_ASSIGN, QUERY, CONFLICT
import threading

class BaseAgent:
    _threads = []

    def __init__(self, name):
        self.name = name
        self.message=None
        self.logger=None
        # 保存其他Agent对象
        self.agents = {}

    # 等待所有异步线程完成
    @classmethod
    def wait_all(cls):
        while cls._threads:
            thread = cls._threads.pop(0)
            thread.join()

    # 注册Agent
    def register_agent(self, agent):
        self.agents[agent.name] = agent
        print(f"{self.name}注册Agent: {agent.name}")

#接受消息
    def receive_message(self, message):
        print(f"[{self.name}] 收到消息")
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
    def send_task_assign(self, receiver, payload, related_message_id=None):
        self.send_message(receiver, TASK_ASSIGN, payload, related_message_id)

    def send_result(self, receiver, payload, related_message_id=None):
        self.send_message(receiver, RESULT, payload, related_message_id)

    def send_query(self, receiver, payload, related_message_id=None):
        self.send_message(receiver, QUERY, payload, related_message_id)

    def send_conflict(self, receiver, payload, related_message_id=None):
        self.send_message(receiver, CONFLICT, payload, related_message_id)

    def send_ack(self, receiver, payload, related_message_id=None):
        self.send_message(receiver, ACK, payload, related_message_id)

    # 组装消息并发送
    def send_message(self, receiver, msg_type, payload, related_message_id=None):
        message = Message(self.name, receiver.name, msg_type, payload, related_message_id=related_message_id)
        print(
            f"[{self.name}] 发送消息给 [{message.receiver}]"
        )

        if self.logger:
            self.logger.record(message)

        # 干完活释放线程，避免_threads无界累积
        def run_message():
            try:
                receiver.receive_message(message)
            finally:
                try:
                    BaseAgent._threads.remove(thread)
                except ValueError:
                    pass

        thread = threading.Thread(
            target=run_message
        )

        self._threads.append(thread)
        thread.start()