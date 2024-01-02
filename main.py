import json
import os
from typing import List

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import StreamingResponse
from mistralai.models.chat_completion import ChatMessage
from structlog import get_logger

from lovecraft.data_models import CharacterData, Event, Scenario
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

with open("game_files/config.json") as f:
    config = json.loads(f.read())

game_state = Scenario.model_validate(json.loads(open("game_files/game_state.json").read()))

character_data = CharacterData.model_validate(json.loads(open("game_files/character_data.json").read()))

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


@app.get("/adventure_name")
def get_adventure_name() -> str:
    return config["adventure_name"]


@app.get("/character_data")
def get_character_data() -> CharacterData:
    return character_data


# llm client
@app.post("/narrate")
def get_narration(request: NarrationRequest):
    history = ConversationHistory.main()
    ConversationHistory.append(ChatMessage(role="user", content=request.user_input))
    context_input = " ".join([message.content for message in history])[-2000:]
    context = db_client.get_adventure_context(context_input)
    relevant_events = db_client.get_relevant_events(context_input)
    game_state.events = relevant_events
    response = llm_client.invoke(request.user_input, history, context, game_state)
    return StreamingResponse(stream_tokens(response), media_type="text/event-stream")


@app.post("/append_message")
def append_message(request: AppendMessage) -> int:
    ConversationHistory.append(ChatMessage(role=request.role, content=request.content))
    return 200


@app.post("/update_game_state")
async def update_game_state(request: LLMResponse, background_task: BackgroundTasks):
    past_events = db_client.get_relevant_events(request.llm_response)
    new_events = llm_client.update_event_state(past_events, request.llm_response)
    db_client.update_events([Event(**event) for event in json.loads(new_events)])


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


@app.post("/narrate_bout_of_insanity")
def narrate_insanity(request: LLMResponse):
    history = ConversationHistory.main()
    context_input = " ".join([message.content for message in history])[-2000:]
    context = db_client.get_adventure_context(context_input)
    response = llm_client.bout_of_insanity(request.llm_response, context, character_data.sanity)
    return StreamingResponse(stream_tokens(response), media_type="text/event-stream")


@app.post("/determine_if_skill_check")
def determine_if_skill_check(request: NarrationRequest):
    return skill.do_check(request.user_input)


@app.post("/do_skill_check")
def do_skill_check(request: NarrationRequest):
    selected_skill = skill.select_skill(request.user_input)
    return skill.perform_check(character_data.dict()[selected_skill])


@app.post("/determine_if_sanity_check")
def determine_if_sanity_check(request: LLMResponse):
    return sanity.predict(request.llm_response)


@app.get("/do_sanity_check")
def do_sanity_check() -> bool:
    return sanity.check_sanity(character_data.sanity)


@app.post("/assess_sanity_loss")
def assess_sanity_loss(request: LLMResponse):
    new_sanity = sanity.assess_sanity(request.llm_response, character_data.sanity)
    character_data.sanity = new_sanity
    return 200


@app.get("/current_sanity")
def return_current_sanity():
    return {"character_sanity": character_data.sanity}
