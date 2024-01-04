import sqlite3
from typing import List

from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores import SQLiteVSS
from mistralai.models.chat_completion import ChatMessage
from sqlite_utils import Database

from module.data_models import Event


class SqlClient:
    def __init__(self, save_name: str):
        self.save_name = save_name
        self.embeddings = SentenceTransformerEmbeddings(model_name="jinaai/jina-embedding-s-en-v1")

    def _create_connection(self, file: str) -> sqlite3.Connection:
        return sqlite3.connect(file)

    def _close_connection(self, connection: sqlite3.Connection):
        connection.close()

    def clear_adventure(self):
        save_name = self.save_name
        state_connection = self._create_connection("data/state_db")
        history_connection = self._create_connection("data/history_db")
        history_db = Database(sqlite3.connect(history_connection))
        state_db = Database(sqlite3.connect(state_connection))
        state_db.execute(f"DROP TABLE IF EXISTS {save_name}")
        history_db.execute(f"DROP TABLE IF EXISTS {save_name}")
        self._close_connection(history_connection)
        self._close_connection(state_connection)

    def get_adventure_context(self, llm_output: str, top_k=4) -> str:
        mythos_db = self._create_connection("data/lovecraft.db")
        context_table = SQLiteVSS(table="mythos", embedding=self.embeddings, connection=mythos_db)
        res = context_table.similarity_search(llm_output, k=top_k)
        self._close_connection(mythos_db)
        return " ".join([x.page_content for x in res])

    def get_relevant_events(self, content: str) -> List[Event]:
        state_db = self._create_connection("data/state.db")
        events_table = SQLiteVSS(table=self.save_name, embedding=self.embeddings, connection=state_db)
        res = events_table.similarity_search(content, k=10)
        self._close_connection(state_db)
        return [Event(description=event.page_content) for event in res]

    def get_recent_history(self, n_results: int) -> List[ChatMessage]:
        table_name = self.save_name
        connection = self._create_connection("data/history.db")
        query = f"""SELECT content, role, time_ingested_dt FROM {table_name} order
        by time_ingested_dt desc LIMIT {n_results}"""
        history_db = Database(connection)
        res = history_db.query(query)
        self._close_connection(connection)
        return [ChatMessage(role=content["role"], content=content["content"]) for content in list(res)]

    def update_events(self, events: List[Event]):
        state_db = self._create_connection("data/state.db")
        events_table = SQLiteVSS(table=self.save_name, embedding=self.embeddings, connection=state_db)
        payload = [x.description for x in events]
        events_table.add_texts(payload)
        self._close_connection(state_db)

    def update_history(self, content: str, role: str, timestamp: float) -> int:
        connection = self._create_connection("data/history.db")
        history_db = Database(connection)
        history_db[self.save_name].insert({"content": content, "role": role, "time_ingested_dt": timestamp})
        self._close_connection(connection)
        return 200
