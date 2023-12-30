import os

from dotenv import load_dotenv
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from pinecone_client import PineconeClient

load_dotenv()

MISTRAL_KEY = os.getenv("MISTRAL")

SYSTEM_PROMPT = """
AI, you are the guide of adventures in a world of dark and foreboding adventure set in the 1920s inspired by HP Lovecraft. Your task is to help players explore scenarios in which they must confront and attempt to overcome cosmic and eldritch horror. Your role is to seamlessly blend information retrieval and creative generation to enhance the storytelling experience. Do not regurgitate information from the context, instead use the context to creatively inform novel elements of your storytelling.
When responding to user inputs, only use the provided mythos information if it makes sense given the context of the story and the user input. For example, if a user asks the time, do not use the provided context to respond.
You will use retrieval augmented generation in order to help you set the scene, drive excitement in the story, and maintain internal consistency. After a user has prompted their intentions, you will set out to resolve the actions, prompting the user for further input as necessary to empower them to tell their own story. Pause often to allow for the player character to drive the story.

When the excitement, tension, and action would benefit, please ask the player to roll for success or failure on an action. For example, if a player asks to pick a locked door or to search a room, ask them to roll for success. When resolving the action, take the relative level of success into account.

When pausing to ask for user input, do not offer any options merely finish your output by asking "What do you want to do next?".

Addtionally, when responding avoid any notes, comments, or asides that might take the player character out of the story.

Below is a structed dictionary that gives information to work into your story and on the current state of the narrative.
{game_state}
"""

USER_PROMPT = """MYTHOS_SETTING: {context} | USER_INPUT {user_input}"""

EVENT_STATE_PROMPT = str("""You are a subsystem for a lovecraftian roleplaying game.
                   Your purpose is to take the output of an LLM and return a
                   list of new Events to track the status of the narrative.
                   Here is the schema for the event. When responsing, only
                   return the new elments without any comment or summary. Your
                   repsonse must be valid json. Your reponse should be in the
                   format [{"description": description}]
                   """)

CHARACTER_STATE_PROMPT = str("""You are a subsystem for a lovecraftian roleplaying game.
                   Your purpose is to take the output of an LLM and return a
                   list of new characters or updated charaters to track the status of the narrative.
                   Your repsonse must be valid json. Your reponse should be in the
                   format [
                             {"name": name,
                             "profession": profession,
                             "description": description,
                             hair_color:"hair_color",
                             "gender": gender
                            }
                            ]
                   """)


UPDATE_STATE_PROMPT = "PAST_STATE: {game_state} | LLM_RESPONSE: {llm_response}"

SANITY_SYSTEM_PROMPT = ("You are a subsystem for a lovecraftian role-playing game. When a player encounters horrifying and eldritch powers beyond human comprehension, they must undergo a sanity check. If a player fails that check, your subsystem will take the current context of the adventure, setting information from the lovecraftian mythos, and write a scene that describes a temporary and transient bout of madness. When completing a request modulate the intensity of your response based on the severity of the situation, and the nature of the threat. When responding do not refer to yourself or have any comentary, merely continue the narrative with a bout of madness. Based on the severity of the bout of madness, finish your response with CURRENT_SANITY=(the new sanity value). Sanity losses should range from 5-25 points depending on the situation. Extreme situations such as meeting a dark god, can cause sanity losses of up to 100 points.")

SANITY_PROMPT = ("""MYTHOS_SETTING {context} | LLM_RESPONSE {llm_response} |
                 CURRENT_SANITY = {current_sanity}""")

SKILL_CHECK_SYSTEM_PROMPT = ("""You are a subsystem for a lovecraftian
                   role-playing game. When the player is exploring the world,
                   they will at times take actions that must be resolved via a
                   skill check. Your purpose is to take the player action and
                   the result of the skill check and provide a short narration
                   to resolve the action according to the skill check. The
                   format for the input is PLAYER_ACTION {player_action} |
                   CHECK_RESULT {check_result}.""")

SKILL_CHECK_PROMPT = ("""PLAYER_ACTION {player_action} | CHECK_RESULT
                   {check_result}""")

class LLMClient:

    def __init__(self):
        self.client = MistralClient(api_key=MISTRAL_KEY)
        self.model = "mistral-medium"
        self.system_prompt = ChatMessage(role="system", content=" ".join(SYSTEM_PROMPT.split()))
        self.db = PineconeClient()

    def _format_system_prompt(self):
        game_state = open("game_state.json").read()
        return ChatMessage(
                role="system",
                content=SYSTEM_PROMPT.format(
                    game_state=game_state
                    )
                )

    def _format(self, context, user_input):
        return USER_PROMPT.format(context=context, user_input=user_input)

    def invoke(self, messages):
        user_input = messages[-1].content
        context_input = " ".join(
                [message.content for message in messages]
                )[-2000:]
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
                            temperature=.5,
                            max_tokens=2048,
                            )

    def resolve_skill_check(self, messages, check_result):
        user_input = messages[-1].content
        prompt = SKILL_CHECK_PROMPT.format(player_action=user_input,
                                           check_result=check_result)
        system_prompt = ChatMessage(role="system",
                                    content=SKILL_CHECK_SYSTEM_PROMPT)
        model_input = [x for x in messages[:-1]]
        model_input = [system_prompt] + model_input
        model_input.append(ChatMessage(role="user", content=prompt))
        return self.client.chat_stream(
                            model=self.model,
                            messages=model_input,
                            temperature=.5,
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
                            temperature=.5,
                            max_tokens=2048,
                            )

    def update_event_state(self, game_state, llm_response):
        state_system_prompt = ChatMessage(role="system", content=EVENT_STATE_PROMPT)
        inputs = [
                    state_system_prompt,
                    ChatMessage(
                        role="user",
                        content=UPDATE_STATE_PROMPT.format(game_state=game_state, llm_response=llm_response)
                        )
                    ]
        response = self.client.chat_stream(
                    model=self.model,
                    messages=inputs
                )
        full_response = ""
        for token in response:
            full_response += (token.choices[0].delta.content or "")
        return full_response

    def update_npc_state(self, game_state, llm_response):
        state_system_prompt = ChatMessage(role="system", content=CHARACTER_STATE_PROMPT)
        inputs = [
                    state_system_prompt,
                    ChatMessage(
                        role="user",
                        content=UPDATE_STATE_PROMPT.format(game_state=game_state, llm_response=llm_response)
                        )
                    ]
        response = self.client.chat_stream(
                    model=self.model,
                    messages=inputs
                )
        full_response = ""
        for token in response:
            full_response += (token.choices[0].delta.content or "")
        return full_response

    def embed(self, text):
        response = self.client.embeddings(
          model="mistral-embed",
          input=text)
        return response.data[0].embedding
