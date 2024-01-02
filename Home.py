from typing import Dict

import httpx
import streamlit as st
from structlog import get_logger

from request_types import AppendMessage, LLMResponse, NarrationRequest, ResolveSkillCheckRequest

url = "http://127.0.0.1:8000"


class Request:
    def __init__(self, url: str):
        self.url = url
        self.path = "{url}/{path}"

    def post(self, path: str, data: Dict):
        return httpx.post(self.path.format(url=self.url, path=path), json=data).json()

    def get(self, path: str):
        return httpx.get(self.path.format(url=self.url, path=path)).json()

    def stream(self, path: str, data: Dict):
        url = self.path.format(url=self.url, path=path)
        return httpx.stream("POST", url, json=data, timeout=120)


request = Request(url)

logger = get_logger("app")

st.title("Roleplaying in the Eldritch Horror of H.P. Lovecraft")


tokens = None
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "sanity" not in st.session_state:
    st.session_state.sanity = request.get("current_sanity")["character_sanity"]

if "character_attributes" not in st.session_state:
    st.session_state.character_attributes = request.get("character_data")

with st.sidebar:
    adventure_name = st.session_state.character_attributes["adventure_name"]
    st.text(f"You are currently playing {adventure_name}")
    character_name = st.session_state.character_attributes["name"]
    st.text(character_name)
    st.text(f"Your current sanity is {st.session_state.sanity}")

message_placeholder = st.empty()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message.role):
        st.markdown(message.content)
full_response = ""

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
    narration_request = NarrationRequest(user_input=prompt)
    if request.post("determine_if_skill_check", narration_request.model_dump(mode="json")):
        logger.info("DetermineSkillCheck", result=True)
        skill_check_result = request.post("do_skill_check", narration_request.model_dump(mode="json"))
        logger.info("SkillChecked", result=skill_check_result)
        resolve_skill_check_request = ResolveSkillCheckRequest(user_input=prompt, check_result=skill_check_result)
        tokens = request.stream("narrate_resolve_skill_check", resolve_skill_check_request.model_dump(mode="json"))
    else:
        tokens = request.stream("narrate", narration_request.model_dump(mode="json"))
if tokens:
    with tokens as r:
        for payload in r.iter_raw():
            full_response += payload.decode("UTF-8")
            message_placeholder.markdown(full_response + "▌")
            if "USER_INPUT" in full_response:
                break
            if "What do you want to do next?" in full_response:
                break
        full_response = full_response.replace("What do you want to do next?", "")
    llm_response = LLMResponse(llm_response=full_response)
    cause_insanity = request.post("determine_if_sanity_check", llm_response.model_dump(mode="json"))
    if cause_insanity == 1:
        tokens = request.stream("narrate_bout_of_insanity", llm_response.model_dump(mode="json"))
        with tokens as r:
            for payload in r.iter_raw():
                full_response += payload.decode("UTF-8")
                message_placeholder.markdown(full_response + "▌")
        llm_response.llm_response = full_response
        request.post("assess_sanity_loss", llm_response.model_dump(mode="json"))
    message = AppendMessage(role="assistant", content=full_response)
    request.post("append_message", message.model_dump(mode="json"))
    request.post("update_game_state", llm_response.model_dump(mode="json"))
    st.session_state.messages.append({"role": "assistant", "content": full_response})
