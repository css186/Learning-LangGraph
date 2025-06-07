from pydantic import BaseModel, Field
from typing import Literal, Union, TypedDict, Annotated, Optional, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class StartMessage(BaseModel):
    title: Literal["start interview"]
    description: str = Field(description="Description of the interview question")
    language: str = Field(description="programming langauage")

    class Config:
        extra = "forbid"

class QuestionMessage(BaseModel):
    title: Literal["question"]
    speech: str = Field(description="user's input")
    code: str = Field(description="user's code")
    thread_id: str = Field(description="thread id")

    class Config:
        extra = "forbid"

class SubmissionMessage(BaseModel):
    title: Literal["submission result"]
    status: str = Field(description="status of the submission")
    thread_id: str = Field(description="thread id")

    class Config:
        extra = "forbid"

class EndMessage(BaseModel):
    title: Literal["end interview"]
    thread_id: str = Field(description="thread id")

    class Config:
        extra = "forbid"


class AgentState(BaseModel):
    thread_id: Optional[str] = None
    title: Optional[str] = None
    user_input: Optional[str] = None
    status: Optional[str] = None
    model_response: Optional[str] = None
    current_stage: Optional[str] = None
    current_code: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    response_history: List[Union[str, BaseMessage]] = []

    class Config:
        extra = "ignore"
