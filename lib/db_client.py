from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores import SQLiteVSS
from sqlite_utils import Database


class SqlClient:
    def __init__(self, adventure_name: str):
        self.embeddings = SentenceTransformerEmbeddings(model_name="jinaai/jina-embedding-l-en-v1")
        self.mythos_db = SQLiteVSS.create_connection(db_file="/data/lovecraft.db")
        self.state_db = None
        self.history_db = Database(db_file=f"/data/{adventure_name}_history.db")
        self.context_table = SQLiteVSS(table="mythos", embedding=self.embeddings, connection=self.mythos_db)
        self.events_table = "adventure-events"

    def intialize_adventure(self, adventure: str, save_name: str):
        return None

    def get_adventure_context(self, llm_output: str, top_k=4) -> str:
        res = self.context_table.similarity_search(llm_output, k=top_k)
        return " ".join([x.page_content for x in res])

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

    def update_history(self, content: str, timestamp: float):
        self.history_db["history"].insert({"content": content, "time_ingested_dt": timestamp})
