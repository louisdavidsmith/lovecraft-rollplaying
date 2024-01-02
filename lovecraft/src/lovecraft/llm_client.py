from typing import Dict, List

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from .data_models import Event
from .prompts import (
    EVENT_STATE_PROMPT,
    SANITY_PROMPT,
    SANITY_SYSTEM_PROMPT,
    SKILL_CHECK_PROMPT,
    SKILL_CHECK_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    UPDATE_STATE_PROMPT,
    USER_PROMPT,
)


class LLMClient:
    def __init__(self, api_key):
        self.client = MistralClient(api_key=api_key)
        self.model = "mistral-medium"

    def _format_system_prompt(self, game_state: Dict) -> ChatMessage:
        return ChatMessage(role="system", content=SYSTEM_PROMPT.format(game_state=game_state))

    def _format(self, context: str, user_input: str) -> ChatMessage:
        return ChatMessage(role="user", content=USER_PROMPT.format(context=context, user_input=user_input))

    def generate(self, user_input="What is 2+2"):
        return self.client.chat_stream(model=self.model, messages=[ChatMessage(role="user", content=user_input)], max_tokens=128)

    def invoke(self, user_input: str, history: List[ChatMessage], context: str, game_state: Dict):
        prompt = self._format(context, user_input)
        system_prompt = self._format_system_prompt(game_state)
        model_input = [system_prompt] + history + [prompt]
        return self.client.chat_stream(
            model=self.model,
            messages=model_input,
            temperature=0.5,
            max_tokens=2048,
        )

    def resolve_skill_check(self, user_input: str, history: List[ChatMessage], check_result: str):
        prompt = SKILL_CHECK_PROMPT.format(player_action=user_input, check_result=check_result)
        prompt = ChatMessage(role="user", content=prompt)
        system_prompt = ChatMessage(role="system", content=SKILL_CHECK_SYSTEM_PROMPT)
        model_input = [system_prompt] + history + [prompt]
        return self.client.chat_stream(
            model=self.model,
            messages=model_input,
            temperature=0.5,
            max_tokens=2048,
        )

    def bout_of_insanity(self, llm_response: str, context: str, current_sanity: int):
        content = SANITY_PROMPT.format(context=context, llm_response=llm_response, current_sanity=current_sanity)
        system_prompt = ChatMessage(role="system", content=SANITY_SYSTEM_PROMPT)
        prompt = ChatMessage(role="user", content=content)
        model_input = [system_prompt, prompt]
        return self.client.chat_stream(
            model=self.model,
            messages=model_input,
            temperature=0.5,
            max_tokens=2048,
        )

    def update_event_state(self, event_history: List[Event], llm_response: str) -> str:
        state_system_prompt = ChatMessage(role="system", content=EVENT_STATE_PROMPT)
        inputs = [
            state_system_prompt,
            ChatMessage(role="user", content=UPDATE_STATE_PROMPT.format(game_state=event_history, llm_response=llm_response)),
        ]
        response = self.client.chat_stream(model=self.model, messages=inputs)
        full_response = ""
        for token in response:
            full_response += token.choices[0].delta.content or ""
        return full_response
