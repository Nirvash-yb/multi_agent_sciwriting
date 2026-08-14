import json
import os
from collections import Counter, defaultdict


def load_token_summary(
        summary_path="logs/llm_usage_summary.json"):

    if not os.path.exists(summary_path):
        return None

    with open(
        summary_path,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


class CommunicationAnalyzer:
    def __init__(self, log_path, output_dir="analysis"):
        self.log_path = log_path
        self.output_dir = output_dir

        self.logs = []

        os.makedirs(self.output_dir, exist_ok=True)

    def load_logs(self):
        """读取通信日志"""
        with open(
            self.log_path,
            "r",
            encoding="utf-8"
        ) as f:
            self.logs = json.load(f)

        return self.logs

    def generate_sequence_diagram(self):
        import matplotlib.pyplot as plt

        if not self.logs:
            return None

        agents = []

        for log in self.logs:
            sender = log.get("sender")
            receiver = log.get("receiver")

            if sender and sender not in agents:
                agents.append(sender)

            if receiver and receiver not in agents:
                agents.append(receiver)

        if not agents:
            return None

        message_count = len(self.logs)

        height = max(
            6,
            message_count * 0.6
        )

        fig, ax = plt.subplots(
            figsize=(12, height)
        )

        x_positions = {
            agent: index
            for index, agent in enumerate(agents)
        }

        for agent, x in x_positions.items():
            ax.plot(
                [x, x],
                [0, message_count + 1],
                linestyle="--",
                linewidth=1
            )

            ax.text(
                x,
                message_count + 1.2,
                agent,
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold"
            )

        for index, log in enumerate(self.logs):

            sender = log.get("sender")
            receiver = log.get("receiver")

            message_type = log.get(
                "message_type",
                "UNKNOWN"
            )

            if (
                    sender not in x_positions
                    or receiver not in x_positions
            ):
                continue

            x1 = x_positions[sender]
            x2 = x_positions[receiver]

            # 从上往下排列
            y = message_count - index

            # 消息箭头
            ax.annotate(
                "",
                xy=(x2, y),
                xytext=(x1, y),
                arrowprops=dict(
                    arrowstyle="->",
                    linewidth=1.2
                )
            )

            # 消息类型
            ax.text(
                (x1 + x2) / 2,
                y + 0.15,
                message_type,
                ha="center",
                va="bottom",
                fontsize=8
            )

            # 时间
            timestamp = log.get(
                "timestamp",
                ""
            )

            ax.text(
                -0.5,
                y,
                timestamp,
                ha="right",
                va="center",
                fontsize=7
            )

        ax.set_xlim(
            -1,
            len(agents)
        )

        ax.set_ylim(
            0,
            message_count + 2
        )

        ax.set_xticks([])

        ax.set_yticks([])

        # 去掉边框
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.set_title(
            "Multi-Agent Communication Sequence",
            fontsize=14,
            fontweight="bold"
        )

        plt.tight_layout()

        # =========================
        # 保存 PNG
        # =========================

        output_path = os.path.join(
            self.output_dir,
            "communication_sequence.png"
        )

        plt.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

        return output_path

    def analyze_load(self):
        send_count = Counter()
        receive_count = Counter()

        for log in self.logs:

            sender = log.get("sender")
            receiver = log.get("receiver")

            if sender:
                send_count[sender] += 1

            if receiver:
                receive_count[receiver] += 1

        agents = sorted(
            set(send_count) | set(receive_count)
        )

        result = {}

        for agent in agents:

            result[agent] = {
                "send": send_count[agent],
                "receive": receive_count[agent],
                "total": (
                    send_count[agent]
                    + receive_count[agent]
                )
            }

        return result

    def generate_load_chart(self):
        import matplotlib.pyplot as plt
        import numpy as np

        load = self.analyze_load()

        if not load:
            return

        agents = list(load.keys())

        send_values = [
            load[agent]["send"]
            for agent in agents
        ]

        receive_values = [
            load[agent]["receive"]
            for agent in agents
        ]

        x = np.arange(len(agents))

        width = 0.35

        plt.figure(figsize=(10, 6))

        plt.bar(
            x - width / 2,
            send_values,
            width,
            label="Send"
        )

        plt.bar(
            x + width / 2,
            receive_values,
            width,
            label="Receive"
        )

        plt.xlabel("Agent")
        plt.ylabel("Message Count")
        plt.title("Agent Communication Load")

        plt.xticks(
            x,
            agents,
            rotation=30
        )

        plt.legend()

        plt.tight_layout()

        output_path = os.path.join(
            self.output_dir,
            "communication_load.png"
        )

        plt.savefig(
            output_path,
            dpi=300
        )

        plt.close()

        return output_path

    def analyze_message_types(self):
        counter = Counter()

        for log in self.logs:

            message_type = log.get(
                "message_type",
                "UNKNOWN"
            )

            counter[message_type] += 1

        return dict(counter)

    def generate_message_type_chart(self):
        import matplotlib.pyplot as plt

        type_count = self.analyze_message_types()

        if not type_count:
            return

        labels = list(type_count.keys())
        values = list(type_count.values())

        plt.figure(figsize=(8, 8))

        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90
        )

        plt.title(
            "Message Type Distribution"
        )

        plt.tight_layout()

        output_path = os.path.join(
            self.output_dir,
            "message_type_distribution.png"
        )

        plt.savefig(
            output_path,
            dpi=300
        )

        plt.close()

        return output_path

    # 将token汇总JSON转换为每个Agent消耗token的柱状图
    def generate_token_chart(
            self,
            summary_path="logs/llm_usage_summary.json"):

        import matplotlib.pyplot as plt

        data = load_token_summary(summary_path)

        if not data or not data.get("by_agent"):
            return None

        by_agent = data["by_agent"]

        agents = list(by_agent.keys())

        totals = [
            by_agent[agent]["total_tokens"]
            for agent in agents
        ]

        prompt_values = [
            by_agent[agent]["prompt_tokens"]
            for agent in agents
        ]

        completion_values = [
            by_agent[agent]["completion_tokens"]
            for agent in agents
        ]

        plt.figure(figsize=(10, 6))

        bars = plt.bar(
            agents,
            totals,
            color="#4C72B0",
            label="Total"
        )

        for bar, total, prompt, completion in zip(
                bars,
                totals,
                prompt_values,
                completion_values):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{total}\n(p:{prompt}/c:{completion})",
                ha="center",
                va="bottom",
                fontsize=8
            )

        plt.xlabel("Agent")
        plt.ylabel("Tokens")
        plt.title("LLM Token Consumption per Agent")
        plt.xticks(rotation=30)
        plt.legend()
        plt.tight_layout()

        output_path = os.path.join(
            self.output_dir,
            "token_usage.png"
        )

        plt.savefig(
            output_path,
            dpi=300
        )

        plt.close()

        return output_path

    def analyze(self):
        self.load_logs()

        sequence_path = (
            self.generate_sequence_diagram()
        )

        load_path = (
            self.generate_load_chart()
        )

        message_type_path = (
            self.generate_message_type_chart()
        )

        token_chart_path = (
            self.generate_token_chart()
        )

        return {
            "sequence_diagram": sequence_path,
            "communication_load": load_path,
            "message_type_distribution": message_type_path,
            "token_usage": token_chart_path
        }

    @staticmethod
    def _alias(name):

        return (
            name
            .replace(" ", "_")
            .replace("-", "_")
            .replace(".", "_")
        )