from agent.coordinator_agent import CoordinatorAgent
from agent.literature_agent import LiteratureAgent
from agent.method_agent import MethodAgent
from agent.experiment_agent import ExperimentAgent
from agent.checker_agent import CheckerAgent
from agent.writer_agent import WriterAgent
from agent.baseagent import BaseAgent
from communication.message import *
from communication.logger import CommunicationLogger
import os
from communication.communicationanalyzer import CommunicationAnalyzer
from config import CONFIG

logger = CommunicationLogger()

literature = LiteratureAgent()
method = MethodAgent()
coordinator = CoordinatorAgent()
experiment = ExperimentAgent()
checker = CheckerAgent()
writer = WriterAgent()

#注册日志记录功能
for agent in [coordinator, literature, method, experiment, checker, writer]:
    agent.logger = logger
    agent.llm.logger = logger

# 注册
coordinator.register_agent(literature)
coordinator.register_agent(method)
coordinator.register_agent(experiment)
coordinator.register_agent(checker)
coordinator.register_agent(writer)

literature.register_agent(coordinator)
method.register_agent(coordinator)
experiment.register_agent(coordinator)
checker.register_agent(coordinator)
writer.register_agent(coordinator)

coordinator.start_write(CONFIG.get("research_topic", ""))

BaseAgent.wait_all()

os.makedirs("logs", exist_ok=True)
logger.save("logs/messages.json")
logger.save_llm_messages("logs/llm_messages.json")
logger.save_usage_summary("logs/llm_usage_summary.json")


analyzer = CommunicationAnalyzer(
    log_path="logs/messages.json"
)

analyzer.analyze()