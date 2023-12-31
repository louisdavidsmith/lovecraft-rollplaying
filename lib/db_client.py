from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores import SQLiteVSS


class SqlClient:
    def __init__(self):
        self.embeddings = SentenceTransformerEmbeddings(model_name="jinaai/jina-embedding-l-en-v1")
        self.connection = SQLiteVSS.create_connection(db_file="/data/lovecraft.db")
        self.context_table = SQLiteVSS(table="mythos", embedding=self.embeddings, connection=self.connection)
        self.events_table = "adventure-events"

    def get_adventure_context(self, llm_output: str, top_k=3) -> str:
        context = self.context_table.similarity_search(llm_output)
        return context
