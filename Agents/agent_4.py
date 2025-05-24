from typing import TypedDict, Sequence, Annotated
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

load_dotenv()


# Globel variables
document_content = ""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

@tool
def update(content: str) -> str:
    """
    Update the document with the provided content.
    """
    global document_content
    document_content = content
    return f"Document updated with content: {content}"

@tool
def save(filename: str) -> str:
    """
    Save the current document to a text file and finish the process.
    Args:
        filename: Name of the text file.
    """
    if not filename.endswith(".txt"):
        filenname = f"{filename}.txt"

    try:
        with open(filename, "w") as file:
            file.write(document_content)
        print(f"\n Document saved to {filename}")
        return f"Document saved to {filename}"
    except Exception as e:
        return f"Error saving document: {str(e)}"


def draft_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(
        content=f"""
        You are a Drafter, a helpful writing assistant.
        You are going to help the user update and modify documents.
        - If the user wants to update or modify the document, use the 'update' tool with the complete content.
        - If the user wants to save the document, use the 'save' tool.
        - Make sure to always show the current document state after modification.

        The current document content is: {document_content}
        
        """
    )

    if not state["messages"]:
        user_input = "I'm ready to help you update a document. What would you like to create?"
        user_message = HumanMessage(content=user_input)

    else:
        user_input = input("What would you like to do with the document?")
        print(f"\nUser: {user_input}")
        user_message = HumanMessage(content=user_input)

    all_messages = [system_prompt] + list(state["messages"]) + [user_message]

    response = model.invoke(all_messages)
    print(f"\nAI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"\nAI is calling tool: {[tc["name"] for tc in response.tool_calls]}")


    return {"messages": list(state["messages"]) + [user_message, response]}



def should_continue(state: AgentState) -> AgentState:
    """
    Determine if the agent should continue or end the conversation
    """
    messages = state["messages"]
    if not messages:
        return "continue"
    
    # look for the moset recent tool message
    for message in reversed(messages):
        if (isinstance(message, ToolMessage) and
            "saved" in message.content.lower() and 
            "document" in message.content.lower()):
            return "end"
    
    return "continue"


def print_messages(messages):
    """
    Print the messages in a readable format
    """
    if not messages:
        return
    
    for message in messages[-3:]:
        if isinstance(message, ToolMessage):
            print(f"\nTool Result: {message.name} - {message.content}")



tools = [update, save]

model = ChatOpenAI(model="gpt-4o").bind_tools(tools)




graph = StateGraph(AgentState)
graph.add_node("agent", draft_agent)
graph.set_entry_point("agent")
graph.add_node("tool", ToolNode(tools=tools))
graph.add_edge("agent", "tool")

graph.add_conditional_edges(
    "tool",
    should_continue,
    {
        "continue": "agent",
        "end": END
    }
)

app = graph.compile()

def run_agent():
    print("\n ===================== Draft Agent ====================")
    init_state = {"messages": []}

    for step in app.stream(init_state, stream_mode="values"):
        if "messages" in step:
            print_messages(step["messages"])
    
    print("\n ===================== Draft Agent Finished ====================")


if __name__ == "__main__":
    run_agent()
