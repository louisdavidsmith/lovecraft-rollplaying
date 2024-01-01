import json
import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from mistralai.models.chat_completion import ChatMessage
from structlog import get_logger

from lovecraft.data_models import CharacterData, Scenario
from lovecraft.db_client import SqlClient
from lovecraft.llm_client import LLMClient
from lovecraft.sanity_model import SanityModel
from lovecraft.skill_model import SkillModel
from request_types import AppendMessage, LLMResponse, NarrationRequest, ResolveSkillCheckRequest


def stream_tokens(response) -> List[str]:
    for token in response:
        yield (token.choices[0].delta.content or "")


logger = get_logger("main")

load_dotenv()
MISTRAL_KEY = os.environ["MISTRAL"]

app = FastAPI()

with open("config.json") as f:
    config = json.loads(f.read())

game_state = Scenario.model_validate(json.loads(open("game_state.json").read()))

character_data = CharacterData.model_validate(json.loads(open("character_data.json").read()))

llm_client = LLMClient(MISTRAL_KEY)
logger.info("LoadedLLMClient")

db_client = SqlClient(config["adventure_name"], config["save_slot"])
logger.info("LoadedDbClient")

sanity = SanityModel()
logger.info("LoadedSanityModel")

skill = SkillModel()
logger.info("LoadedSkillModel")


class ConversationHistory:
    _messages = []

    @classmethod
    def main(self):
        return self._messages

    @classmethod
    def append(self, message: ChatMessage):
        self._messages.append(message)

    @classmethod
    def empty_history(self):
        self._messages = []

    @classmethod
    def get_history(self):
        return [{"role": message.role, "content": message.content} for message in self._messages]


@app.get("/init_adventure")
def init_adventure():
    db_client.update_events(game_state.events)
    return 200


# llm client
@app.post("/narrate")
def get_narration(request: NarrationRequest):
    history = ConversationHistory.main()
    ConversationHistory.append(ChatMessage(role="user", content=request.user_input))
    context_input = " ".join([message.content for message in history])[-2000:]
    context = db_client.get_adventure_context(context_input)
    game_state = db_client.get_relevant_events(context_input)
    response = llm_client.invoke(request.user_input, history, context, game_state)
    return StreamingResponse(stream_tokens(response), media_type="text/event-stream")


@app.post("/append_message")
def append_message(request: AppendMessage) -> int:
    ConversationHistory.append(ChatMessage(role=request.role, content=request.content))
    return 200


@app.get("/get_history")
def get_history():
    return ConversationHistory.get_history()


@app.get("/empty_history")
def empty_history():
    ConversationHistory.empty_history()
    return 200


@app.post("/narrate_resolve_skill_check")
def resolve_skill_check(request: ResolveSkillCheckRequest):
    history = ConversationHistory.main()
    ConversationHistory.append(ChatMessage(role="user", content=request.user_input))
    response = llm_client.resolve_skill_check(request.user_input, history, request.check_result)
    return StreamingResponse(stream_tokens(response), media_type="text/event-stream")


@app.get("/narrate_bout_of_insanity")
def narrate_insanity():
    return "insanity"


# to do: add event update


@app.post("/determine_if_skill_check")
def determine_if_skill_check(request: NarrationRequest):
    return skill.do_check(request.user_input)


@app.post("/do_skill_check")
def do_skill_check(request: NarrationRequest):
    selected_skill = skill.select_skill(request.user_input)
    return skill.perform_check(character_data.dict()[selected_skill])


# sanity model
@app.post("/determine_if_sanity_check")
def determine_if_sanity_check(request: LLMResponse):
    return sanity.predict(request.llm_response)


@app.get("/do_sanity_check")
def do_sanity_check():
    return "True/false"


@app.get("/assess_sanity_loss")
def assess_sanity_loss():
    return "sanity"


# db client
@app.get("/get_mythos_context")
def get_mythos_context():
    return "context"


@app.get("/get_relevant_events")
def get_relevant_events():
    return ""


@app.get("/get_recent_history")
def get_recent_history():
    return ""


# @app.get('/invoke_llm')
# def test():
#    return StreamingResponse(stream_tokens(llm_client.generate()), media_type='text/event-stream')
