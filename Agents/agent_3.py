## ReAct Agent (Reasoning and Acting)
# 1. Learn how to create `Tools` in LangGraph
# 2. How to create a ReAct graph
# 3. Work with another different kind of message: ToolMessages
# 4. Test the robustness of the agent

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages] # This means that the sequence of messages will be appended using the `add_message` function (safer)


# Create a tool
@tool
def add(a: int, b: int):
    """
    This is the additiona function that adds two numbers.
    """
    return a + b


def multiply(a: int, b: int):
    """
    This is the multiplication function that multiplies two numbers.
    """
    return a * b

tools = [add, multiply]

# Bind tools to the model
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)


def model_call(state: AgentState) -> AgentState:
    # Set the system message
    system_prompt = SystemMessage(content=
    """
    You are my AI assistant, please answer my query to the best of your ability.
    """
    )
    response = model.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


graph = StateGraph(AgentState)
graph.add_node("agent", model_call)

tool_node = ToolNode(tools=tools)
graph.add_node("tool", tool_node)

graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tool",
        "end": END
    }
)
# Back to the agent node
graph.add_edge("tool", "agent")

app = graph.compile()


def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()

inputs = {"messages": [("user", "Add 40 + 12 and then multiply the result by 6. Also tell me a joke about math.")]}
print_stream(app.stream(inputs, stream_mode="values"))
