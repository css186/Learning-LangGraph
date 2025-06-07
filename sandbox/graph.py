import logging
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode

from langgraph.checkpoint.redis.aio import AsyncRedisSaver


from .schemas import AgentState
from .nodes import interview_step
from .config import settings
from .tools import count_tokens


logger = logging.getLogger(__name__)


REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
redis_saver: AsyncRedisSaver
interview_agent = None


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("interview", interview_step)
    graph.add_edge(START, interview)


    graph.add_tool(count_tokens)
    count_node = ToolNode(
        tools=[count_tokens],
        name="count_tokens",
        parents=[interview],
    )
    graph.add_node(count_node)
    graph.add_edge(interview, count_node)

    graph.add_edge(count_node, END)
    return graph


async def init_graph():
    global redis_saver, interview_agent
    async with AsyncRedisSaver.from_conn_string(REDIS_URL) as saver:
        redis_saver = saver
        logger.info(f"Redis saver initialized with URL: {REDIS_URL}")

        # Build the graph
        graph = build_graph()
        interview_agent = graph.compile(checkpoint=redis_saver)
        logger.info(f"Graph compiled with Redis checkpointing")


async def shutdown_graph():
    if redis_saver:
        await redis_saver.aclose()
        logger.info(f"Redis saver closed")
