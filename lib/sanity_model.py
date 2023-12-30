from setfit import SetFitModel


class SanityModel:

    def __init__(self):
        self.model = SetFitModel().from_pretrained("model-sanity/")
        self.cutoff = 0.60

    def predict(self, llm_response):
        proba = float(self.model.predict_proba([llm_response])[0][1])
        if proba > self.cutoff:
            return 1
        else:
            return 0
