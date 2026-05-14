import asyncio
from importlib import import_module


def make_settings():
    settings_mod = import_module("qdrant_loader_core.llm.settings")
    return settings_mod.LLMSettings(
        provider="bedrock",
        base_url=None,
        api_key=None,
        api_version=None,
        headers=None,
        models={"embeddings": "amazon.titan-embed-text-v2:0", "chat": ""},
        tokenizer="none",
        request=settings_mod.RequestPolicy(),
        rate_limits=settings_mod.RateLimitPolicy(),
        embeddings=settings_mod.EmbeddingPolicy(vector_size=1024),
        provider_options={
            "aws_region": "us-east-1",
            "model_id": "amazon.titan-embed-text-v2:0",
        },
    )

async def main():
    factory = import_module("qdrant_loader_core.llm.factory")
    settings = make_settings()
    provider = factory.create_provider(settings)

    emb = provider.embeddings()
    vectors = await emb.embed(["hello"])

    print("vector count:", len(vectors))
    print("vector dim:", len(vectors[0]) if vectors else 0)
    print("first vector sample:", vectors[0][:5])

if __name__ == "__main__":
    asyncio.run(main())
