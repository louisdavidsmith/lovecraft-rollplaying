import random
import re

from setfit import SetFitModel
from structlog import get_logger

logger = get_logger("sanity-model")


class SanityModel:
    def __init__(self):
        self.model = SetFitModel().from_pretrained("models/model-sanity/")
        self.cutoff = 0.60
        self.pattern = r"CURRENT\\?_SANITY\s?=\s?(\d+)\*?"

    def predict(self, llm_response: str) -> int:
        proba = float(self.model.predict_proba([llm_response])[0][1])
        if proba > self.cutoff:
            return 1
        else:
            return 0

    def check_sanity(self, current_sanity: int) -> bool:
        check_value = random.randrange(110)
        if check_value > current_sanity:
            return True
        else:
            return False

    def assess_sanity(self, llm_response: str, current_sanity: int) -> int:
        resulting_sanity = re.search(self.pattern, llm_response)
        if resulting_sanity:
            res = int(resulting_sanity.group(1))
            logger.info("ParsedSanity", sanity=res)
            return res
        else:
            logger.info("FailedSanityParse")
            return round(current_sanity * 0.85)
