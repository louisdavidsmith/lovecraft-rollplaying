from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from pinecone_client import PineconeClient
from prompts import (
    CHARACTER_STATE_PROMPT,
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
        self.system_prompt = ChatMessage(role="system", content=" ".join(SYSTEM_PROMPT.split()))
        self.db = PineconeClient()

    def _format_system_prompt(self):
        game_state = open("game_state.json").read()
        return ChatMessage(role="system", content=SYSTEM_PROMPT.format(game_state=game_state))

    def _format(self, context, user_input):
        return USER_PROMPT.format(context=context, user_input=user_input)

    def invoke(self, messages):
        user_input = messages[-1].content
        context_input = " ".join([message.content for message in messages])[-2000:]
        embedding = self.embed(context_input)
        context = self.db.get_context(embedding)
        prompt = self._format(context, user_input)
        system_prompt = self._format_system_prompt()
        model_input = [x for x in messages[:-1]]
        model_input = [system_prompt] + model_input
        model_input.append(ChatMessage(role="user", content=prompt))
        return self.client.chat_stream(
            model=self.model,
            messages=model_input,
            temperature=0.5,
            max_tokens=2048,
        )

    def resolve_skill_check(self, messages, check_result):
        user_input = messages[-1].content
        prompt = SKILL_CHECK_PROMPT.format(player_action=user_input, check_result=check_result)
        system_prompt = ChatMessage(role="system", content=SKILL_CHECK_SYSTEM_PROMPT)
        model_input = [x for x in messages[:-1]]
        model_input = [system_prompt] + model_input
        model_input.append(ChatMessage(role="user", content=prompt))
        return self.client.chat_stream(
            model=self.model,
            messages=model_input,
            temperature=0.5,
            max_tokens=2048,
        )

    def bout_of_insanity(self, llm_response, current_sanity):
        embedding = self.embed(llm_response)
        context = self.db.get_context(embedding)
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

    def update_event_state(self, game_state, llm_response):
        state_system_prompt = ChatMessage(role="system", content=EVENT_STATE_PROMPT)
        inputs = [
            state_system_prompt,
            ChatMessage(role="user", content=UPDATE_STATE_PROMPT.format(game_state=game_state, llm_response=llm_response)),
        ]
        response = self.client.chat_stream(model=self.model, messages=inputs)
        full_response = ""
        for token in response:
            full_response += token.choices[0].delta.content or ""
        return full_response

    def update_npc_state(self, game_state, llm_response):
        state_system_prompt = ChatMessage(role="system", content=CHARACTER_STATE_PROMPT)
        inputs = [
            state_system_prompt,
            ChatMessage(role="user", content=UPDATE_STATE_PROMPT.format(game_state=game_state, llm_response=llm_response)),
        ]
        response = self.client.chat_stream(model=self.model, messages=inputs)
        full_response = ""
        for token in response:
            full_response += token.choices[0].delta.content or ""
        return full_response

    def embed(self, text):
        response = self.client.embeddings(model="mistral-embed", input=text)
        return response.data[0].embedding
