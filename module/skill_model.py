import random

from attributes import attributes
from sentence_transformers.cross_encoder import CrossEncoder
from setfit import SetFitModel


class SkillModel:
    def __init__(self):
        self.model = SetFitModel().from_pretrained("models/model-skill-check")
        self.attributes = attributes
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-2-v2")
        self.check_outcomes = {
            6: "The player is sucessful at the task, and there is an unexpected positive outcome",
            5: "The player is sucessful at the task",
            4: "The player is sucessful at the task, but there is an unexpected negative outcome or complication" "",
            3: "The player fails at the task but there is an unexpected boon that comes the players way.",
            2: "The player fails at the task without additional complications",
            1: "The player fails at the task and there are negative complications",
        }

    def do_check(self, player_action: str) -> bool:
        response = self.model.predict(player_action)
        if response == 1:
            return True
        else:
            return False

    def select_skill(self, player_action: str) -> str:
        pairs = [[player_action, i] for i in list(attributes.values())]
        scores = list(self.cross_encoder.predict(pairs))
        return list(self.attributes.keys())[scores.index(max(scores))]

    def perform_check(self, relevant_skill: int) -> str:
        roll = random.randrange(1, 7)
        result = roll + relevant_skill
        if result > 6:
            result = 6
        elif result < 0:
            result = 1
        return self.check_outcomes[result]
