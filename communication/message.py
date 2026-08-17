import uuid
import datetime

#优先级
HIGH=3
NORMAL=2
LOW=1
#任务分配
TASK_ASSIGN = "TASK_ASSIGN"
#信息查询
QUERY = "QUERY"
#结果提交
RESULT = "RESULT"
#冲突通知
CONFLICT = "CONFLICT"
#确认回执
ACK = "ACK"

class Message:
    def __init__(
            self,
            sender,
            receiver,
            msg_type,
            payload,
            priority=LOW,
            related_message_id=None):

        #唯一消息ID
        self.message_id = str(
            uuid.uuid4()
        )
        #发送时间
        self.timestamp = (
            datetime.datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
        #发送者
        self.sender = sender
        #接收者
        self.receiver = receiver
        #消息类型
        self.message_type = msg_type
        #消息优先级
        self.priority = priority
        #消息主体
        self.payload = payload
        #关联消息ID
        self.related_message_id = related_message_id

    def to_json(self):
        return {
            "message_id":
            self.message_id,

            "timestamp":
            self.timestamp,

            "sender":
            self.sender,

            "receiver":
            self.receiver,

            "message_type":
            self.message_type,

            "priority":
            self.priority,

            "payload":
            self.payload,

            "related_message_id":
            self.related_message_id

        }

    def __str__(self):
        return str(
            self.to_json()
        )