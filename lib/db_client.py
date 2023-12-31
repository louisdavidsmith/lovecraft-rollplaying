from typing import List

from data_models import Event
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores import SQLiteVSS
from sqlite_utils import Database


class SqlClient:
    def __init__(self, adventure_name: str, save_name: str):
        self.embeddings = SentenceTransformerEmbeddings(model_name="jinaai/jina-embedding-l-en-v1")
        self.mythos_db = SQLiteVSS.create_connection(db_file="/data/lovecraft.db")
        self.state_db = SQLiteVSS.create_connection(db_file=f"/data/{adventure_name}_{save_name}_state.db")
        self.history_db = Database(db_file=f"/data/{adventure_name}_history.db")
        self.context_table = SQLiteVSS(table="mythos", embedding=self.embeddings, connection=self.mythos_db)
        self.events_table = SQLiteVSS(table="events", embedding=self.embeddings, connection=self.mythos_db)

    def get_adventure_context(self, llm_output: str, top_k=4) -> str:
        res = self.context_table.similarity_search(llm_output, k=top_k)
        return " ".join([x.page_content for x in res])

    def get_relevant_events(self, content: str) -> List[Event]:
        res = self.events_table.similarity_search(content, k=10)
        return [Event(description=event.page_content) for event in res]

    def get_recent_history(self, n_results: int) -> List[str]:
        return None

    def update_events(self, events: List[Event]):
        events = [x.description for x in events]
        self.events_table.add_texts([events])

    def update_history(self, content: List[str], role: List[str], timestamp: List[float]):
        self.history_db["history"].insert(
            [
                {"content": content_object, "role": content_role, "time_ingested_dt": ts}
                for content_object, content_role, ts in zip(content, role, timestamp)
            ]
        )
