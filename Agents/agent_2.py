## Chatbot with Memory
# 1. Different message types: HumanMessage, AIMessage
# 2. Maintain a full conversation history
# 3. GPT-4o using LangChain's ChatOpenAI
# 4. Create sophisticated conversation loops

from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]

llm = ChatOpenAI(model="gpt-4o")

def process_message(state: AgentState) -> AgentState:
    """
    This node will solve the request you input
    """
    response = llm.invoke(state["messages"])
    state["messages"].append(AIMessage(content=response.content))
    print(f"AI: {response.content}\n")
    return state


def create_graph():
    graph = StateGraph(AgentState)
    graph.add_node("process", process_message)
    graph.add_edge(START, "process")
    graph.add_edge("process", END)
    return graph

def create_agent():
    graph = create_graph()
    agent = graph.compile()
    return agent


def main():
    
    conversation_history = []
    try:
        with open("conversation_history.txt", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("You: "):
                    conversation_history.append(HumanMessage(content=line[5:].strip()))
                elif line.startswith("AI: "):
                    conversation_history.append(AIMessage(content=line[4:].strip()))
    except FileNotFoundError:
        print("No previous conversation history found. Starting fresh.")

    # Preprocess the conversation history to minimize token usage
    length = len(conversation_history)
    if length > 10:
        conversation_history = conversation_history[-10:]  # Keep only the last 10 messages


    print("Welcome to the Chatbot! Type 'exit' to end the conversation.")

    user_input = input("You: ")
    while user_input.lower() != "exit":
        conversation_history.append(HumanMessage(content=user_input))
        agent = create_agent()

        result = agent.invoke({"messages": conversation_history})
        # print(result["messages"])
        conversation_history = result["messages"]
        user_input = input("You: ")

    with open("conversation_history.txt", "w") as f:
        f.write("=== Start of Conversation ===\n")
        for message in conversation_history:
            if isinstance(message, HumanMessage):
                f.write(f"You: {message.content}\n")
            elif isinstance(message, AIMessage):
                f.write(f"AI: {message.content}\n")
        f.write("=== End of Conversation ===\n")

    print("Conversation history saved to conversation_history.txt")

if __name__ == "__main__":
    main()