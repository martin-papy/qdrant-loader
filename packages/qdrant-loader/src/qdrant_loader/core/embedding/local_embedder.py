from sentence_transformers import SentenceTransformer
import asyncio

class LocalEmbedder:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    async def embed(self, texts):
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None, lambda: self.model.encode(texts, convert_to_numpy=True)
        )
        return [v.tolist() for v in vectors]