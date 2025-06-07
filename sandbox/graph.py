import logging
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode

from langgraph.checkpoint.redis.aio import AsyncRedisSaver


from .schemas import AgentState
from .nodes import interview_step
from .config import settings
from .tools import count_tokens

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env", override=True)
os.environ.setdefault("REDIS_URL", settings.REDIS_URL)

logger = logging.getLogger(__name__)




def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("interview", interview_step)
    graph.add_edge(START, "interview")

    # count_node = ToolNode(
    #     tools=[count_tokens],
    #     name="count_tokens",
    # )
    # register that ToolNode under the same name
    # graph.add_node("count_tokens", count_node)
    # graph.add_edge("interview", "count_tokens")
    # graph.add_edge("count_tokens", END)
    graph.add_edge("interview", END)

    return graph


async def init_graph():
    global redis_saver, interview_agent
    async with AsyncRedisSaver.from_conn_string(os.environ["REDIS_URL"]) as checkpointer:
        checkpointer.asetup()
        logger.info(f"Redis initialized with URL")

        # Build the graph
        graph = build_graph()
        interview_agent = graph.compile(checkpointer=checkpointer)
        logger.info(f"Graph compiled with Redis checkpointing")


# async def shutdown_graph():
#     if redis_saver:
#         await redis_saver.
#         logger.info(f"Redis saver closed")
