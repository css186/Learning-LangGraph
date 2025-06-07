from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from .schemas import AgentState
from .config import settings
import logging

logger = logging.getLogger(__name__)

def interview_step(state: AgentState) -> AgentState:
    """
    1) Read state.language, state.description and state.user_input
    2) Call the LLM
    3) Append the reply to state.history & state.model_responses
    4) Return {"state": state} so StateGraph merges it back in
    """
    system = SystemMessage(content=f"""
        You are an experienced hiring manager at Google.
        Language: {state.language}
        The interview question:  {state.description}
        Candidate said: {state.user_input or "<no input>"}
        Please conduct the technical interview, guide the candidate 
        and give feedback.
        """.strip())

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.0
    )
    ai_msg = llm.invoke([system])
    reply = ai_msg.content

    # mutate the Pydantic model
    state.model_response = ai_msg.content
    state.response_history.append(reply)

    logger.info(f"[interview_step] LLM replied: {reply!r}")

    # return a mapping of updated fields
    return state


