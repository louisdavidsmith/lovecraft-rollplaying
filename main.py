import os

from dotenv import load_dotenv
from fastapi import FastAPI
from structlog import get_logger

from lovecraft.db_client import SqlClient
from lovecraft.llm_client import LLMClient
from lovecraft.sanity_model import SanityModel
from lovecraft.skill_model import SkillModel

logger = get_logger("main")

load_dotenv()
MISTRAL_KEY = os.environ["MISTRAL"]

app = FastAPI()

llm_client = LLMClient(MISTRAL_KEY)
logger.info("LoadedLLMClient")

db_client = SqlClient()
logger.info("LoadedDbClient")

sanity = SanityModel()
logger.info("LoadedSanityModel")

skill = SkillModel()
logger.info("LoadedSkillModel")
