import pinecone


class PineconeClient:
    def __init__(self, api_key):
        self.env = "gcp-starter"
        pinecone.init(api_key=api_key, environment="gcp-starter")
        self.index = pinecone.Index("lovecraft-rag")

    def get_context(self, vector, top_k=3):
        xc = self.index.query(vector, top_k=top_k, include_metadata=True)
        return " ".join([x["metadata"]["text"] for x in xc["matches"]])
