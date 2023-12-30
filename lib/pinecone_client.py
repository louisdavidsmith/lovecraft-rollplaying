import pinecone
from dotenv import load_dotenv

load_dotenv()
PINECONE_KEY = os.getenv("PINECONE")

class PineconeClient:

    def __init__(self):
        self.env = "gcp-starter"
        pinecone.init(
            api_key=PINECONE_KEY,
            environment='gcp-starter'
        )
        self.index = pinecone.Index('lovecraft-rag')

    def get_context(self, vector, top_k=3):
        xc = self.index.query(vector, top_k=top_k, include_metadata=True)
        return " ".join([x['metadata']['text'] for x in xc['matches']])
