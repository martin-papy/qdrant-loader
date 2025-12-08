"""Script to check metadata flow in Qdrant Loader."""

import asyncio
from qdrant_client import QdrantClient

async def check_metadata():
    """Check metadata in Qdrant collection."""

    print("=" * 80)
    print("QDRANT METADATA CHECKER")
    print("=" * 80)

    # Connect to Qdrant
    client = QdrantClient(url='http://localhost:6333')

    try:
        # Get collection info
        collection = client.get_collection('test_docs')
        print(f"\n[Collection: test_docs]")
        print(f"   Points count: {collection.points_count}")
        print(f"   Vectors count: {collection.vectors_count}")

        if collection.points_count == 0:
            print("\n[WARNING] Collection is EMPTY - no data has been ingested yet!")
            print("\n[INFO] Metadata Flow:")
            print("   1. Connector reads documents -> creates Document objects with metadata")
            print("   2. ChunkingWorker chunks documents -> adds metadata to chunks")
            print("   3. EmbeddingWorker creates embeddings")
            print("   4. UpsertWorker uploads to Qdrant with metadata in payload")
            print("\n[INFO] Metadata Structure in Qdrant Payload:")
            print("   - content: chunk text")
            print("   - metadata: {chunk metadata dict}")
            print("   - source: source name")
            print("   - source_type: connector type (git, localfile, etc)")
            print("   - created_at: timestamp")
            print("   - updated_at: timestamp")
            print("   - title: document title")
            print("   - url: document URL")
            print("   - document_id: parent document ID")
            return

        # Get sample points with full payload
        print(f"\n[Sample Points - showing first 3]:")
        points = client.scroll(
            collection_name='test_docs',
            limit=3,
            with_payload=True,
            with_vectors=False
        )

        for i, point in enumerate(points[0], 1):
            print(f"\n{'=' * 80}")
            print(f"Point {i}:")
            print(f"{'=' * 80}")
            print(f"ID: {point.id}")

            if point.payload:
                print(f"\n[Payload Structure]:")
                for key in point.payload.keys():
                    print(f"   - {key}")

                print(f"\n[Content - first 200 chars]:")
                content = point.payload.get('content', '')
                print(f"   {content[:200]}...")

                print(f"\n[Metadata]:")
                metadata = point.payload.get('metadata', {})
                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"   {key}: {value[:100]}...")
                        else:
                            print(f"   {key}: {value}")
                else:
                    print("   (empty)")

                print(f"\n[Standard Fields]:")
                print(f"   source: {point.payload.get('source')}")
                print(f"   source_type: {point.payload.get('source_type')}")
                print(f"   title: {point.payload.get('title')}")
                print(f"   url: {point.payload.get('url')}")
                print(f"   document_id: {point.payload.get('document_id')}")
                print(f"   created_at: {point.payload.get('created_at')}")

        # Show metadata keys summary
        print(f"\n{'=' * 80}")
        print(f"[Metadata Keys Summary Across All Points]:")
        print(f"{'=' * 80}")

        all_metadata_keys = set()
        sample_size = min(100, collection.points_count)
        points = client.scroll(
            collection_name='test_docs',
            limit=sample_size,
            with_payload=True,
            with_vectors=False
        )

        for point in points[0]:
            if point.payload and 'metadata' in point.payload:
                metadata = point.payload['metadata']
                if isinstance(metadata, dict):
                    all_metadata_keys.update(metadata.keys())

        if all_metadata_keys:
            print(f"\nFound {len(all_metadata_keys)} unique metadata keys:")
            for key in sorted(all_metadata_keys):
                print(f"   - {key}")
        else:
            print("\n[WARNING] No metadata keys found in chunks!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print(f"\n[INFO] Make sure:")
        print("   1. Qdrant is running on http://localhost:6333")
        print("   2. Collection 'test_docs' exists")
        print("   3. You have run ingestion: qdrant-loader ingest --workspace .")

if __name__ == "__main__":
    asyncio.run(check_metadata())
