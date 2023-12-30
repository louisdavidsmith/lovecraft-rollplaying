import json
import os
import random
import re
import shutil
import time

import streamlit as st
from llm_client import SYSTEM_PROMPT, LLMClient
from mistralai.models.chat_completion import ChatMessage
from sanity_model import SanityModel
from skill_model import SkillModel
from structlog import get_logger

logger = get_logger("app")

st.title("Roleplaying in the Eldritch Horror of H.P. Lovecraft")

llm_client = LLMClient()
sanity_client = SanityModel()
skill_model = SkillModel()

adventures = scenarios = list(os.walk("scenarios"))[0][1]

tokens = None

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if 'sanity' not in st.session_state:
    st.session_state.sanity = 100

if 'character_attributes' not in st.session_state:
    character = json.loads(open("character_data.json").read())
    st.session_state.character_attributes = character

with st.sidebar:
    adventure_name = st.session_state.character_attributes["adventure_name"]
    st.text(f"You are currently playing {adventure_name}")
    character_name = st.session_state.character_attributes["name"]
    st.image("investigator.jpeg", caption=character_name)
    st.text(f'Your current sanity is {st.session_state.sanity}')

message_placeholder = st.empty()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message.role):
        st.markdown(message.content)
full_response=""

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
    if skill_model.do_check(prompt):
        skill = skill_model.select_skill(prompt)
        logger.info("SkillCheck", skill=skill)
        check_result = skill_model.perform_check(
                                st.session_state.character_attributes[skill]
                            )
        logger.info("CheckResult", skill=skill, result=check_result)
        tokens = llm_client.resolve_skill_check(st.session_state.messages,
                                            check_result)
    else:
        tokens = llm_client.invoke(st.session_state.messages)

if tokens:
    for response in tokens:
        full_response += (response.choices[0].delta.content or "")
        message_placeholder.markdown(full_response + "▌")
        if "USER_INPUT" in full_response:
            break
        if "What do you want to do next?" in full_response:
            break
    full_response = full_response.replace("What do you want to do next?", "")
    sanity_check = sanity_client.predict(full_response)
    logger.info("SanityCheck", value=sanity_check)
    if sanity_check == 1:
        check_value = random.randrange(110)
        logger.info("SanityCheckValue", value=check_value)
        if check_value > st.session_state.sanity:
            full_response += "\n "
            for response in llm_client.bout_of_insanity(full_response, st.session_state.sanity):
                full_response += (response.choices[0].delta.content or "")
                message_placeholder.markdown(full_response + "▌")
            pattern = r'CURRENT\\?_SANITY\s?=\s?(\d+)\*?'
            current_sanity = re.search(pattern, full_response)
            if current_sanity:
                result = int(current_sanity.group(1))
                st.session_state.sanity = result
            else:
                st.session_state.sanity -= 10
        else:
            pass
    with open('history.txt', 'a+') as f:
        f.write(f" ".join(full_response.split("\n")) + "\n")
    st.session_state.messages.append(ChatMessage(role="assistant", content=full_response))
