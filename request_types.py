from pydantic import BaseModel


class LLMResponse(BaseModel):
    llm_response: str


class NarrationRequest(BaseModel):
    user_input: str


class ResolveSkillCheckRequest(BaseModel):
    user_input: str
    check_result: str


class AppendMessage(BaseModel):
    role: str
    content: str
