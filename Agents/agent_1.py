## Simple Bot
# 1. Define `state` structure with a list of `HumanMessage` object
# 2. Initialize a `GPT-4o` model using `LangChain's ChatOpenAI`
# 3. Sending and handling different types of messages
# 4. Building and compiling the graph of the Agent

from typing import TypedDict, List
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: List[HumanMessage]

llm = ChatOpenAI(model="gpt-4o")

def process_node(state: AgentState) -> AgentState:
    """
    Process the state by sending the messages to the LLM and updating the state.
    """
    response = llm.invoke(state["messages"])
    print(f"AI: {response.content}\n")
    return state


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("process", process_node)
    graph.add_edge(START, "process")
    graph.add_edge("process", END)
    return graph


def main():
    graph = build_agent_graph()
    agent = graph.compile()

    while True:
        user_input = input("You (type exit to quit): ")
        if user_input.lower() == "exit":
            print("Exiting the chat.")
            break
        agent.invoke({"messages": [HumanMessage(content=user_input)]})


if __name__ == "__main__":
    main()
