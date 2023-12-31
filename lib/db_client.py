from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores import SQLiteVSS


class SqlClient:
    def __init__(self, game_database: str):
        self.embeddings = SentenceTransformerEmbeddings(model_name="jinaai/jina-embedding-l-en-v1")
        self.mythos_db = SQLiteVSS.create_connection(db_file="/data/lovecraft.db")
        self.context_table = SQLiteVSS(table="mythos", embedding=self.embeddings, connection=self.mythos_db)
        self.events_table = "adventure-events"

    def get_adventure_context(self, llm_output: str, top_k=3) -> str:
        context = self.context_table.similarity_search(llm_output)
        return context

    def get_relevant_events(self):
        return None

    def get_relevant_character(self):
        return None

    def get_history(self):
        return None

    def update_events(self):
        return None

    def update_characters(self):
        return None

    def update_history(self):
        return None
