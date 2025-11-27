#!/usr/bin/env python3
"""
Direct QDrant Database Query Script

This script queries the QDrant database directly using the same configuration
files used for ingestion to verify the content that was ingested.
"""

import argparse
import sys
from pathlib import Path

# Add the qdrant-loader package to the path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "qdrant-loader" / "src"))

from qdrant_client import QdrantClient

from qdrant_loader.config import get_settings, initialize_config


def load_config(config_path: str, env_path: str | None = None):
    """Load configuration from the specified files."""
    config_path_obj = Path(config_path)
    env_path_obj = Path(env_path) if env_path else None

    if not config_path_obj.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path_obj}")

    if env_path_obj and not env_path_obj.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path_obj}")

    # Initialize configuration
    initialize_config(config_path_obj, env_path_obj, skip_validation=True)
    return get_settings()


def create_qdrant_client(settings):
    """Create a QDrant client from settings."""
    client = QdrantClient(
        url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30
    )
    return client


def get_collection_info(client: QdrantClient, collection_name: str):
    """Get information about the collection."""
    try:
        info = client.get_collection(collection_name)
        return info
    except Exception as e:
        print(f"Error getting collection info: {e}")
        return None


def count_documents_by_source(client: QdrantClient, collection_name: str):
    """Count documents by source type."""
    try:
        # Get all points to analyze source types
        points = client.scroll(
            collection_name=collection_name,
            limit=1000,  # Adjust based on your data size
            with_payload=True,
            with_vectors=False,
        )[0]

        source_counts = {}
        source_type_counts = {}

        for point in points:
            payload = point.payload or {}
            source = payload.get("source", "unknown")
            source_type = payload.get("source_type", "unknown")

            source_counts[source] = source_counts.get(source, 0) + 1
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

        return source_counts, source_type_counts, len(points)

    except Exception as e:
        print(f"Error counting documents: {e}")
        return {}, {}, 0


def get_sample_documents(client: QdrantClient, collection_name: str, limit: int = 5):
    """Get sample documents from the collection."""
    try:
        points = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )[0]

        return points
    except Exception as e:
        print(f"Error getting sample documents: {e}")
        return []


def search_documents(
    client: QdrantClient, collection_name: str, query: str, limit: int = 5
):
    """Search for documents using a text query."""
    try:
        # For this example, we'll just return some documents
        # In a real scenario, you'd need to embed the query first
        points = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )[0]

        # Simple text matching in payload
        matching_points = []
        for point in points:
            payload = point.payload or {}
            content = payload.get("content", "").lower()
            title = payload.get("title", "").lower()

            if query.lower() in content or query.lower() in title:
                matching_points.append(point)
                if len(matching_points) >= limit:
                    break

        return matching_points
    except Exception as e:
        print(f"Error searching documents: {e}")
        return []


def print_document_summary(point):
    """Print a summary of a document."""
    payload = point.payload or {}
    print(f"  ID: {point.id}")
    print(f"  Title: {payload.get('title', 'N/A')}")
    print(f"  Source: {payload.get('source', 'N/A')}")
    print(f"  Source Type: {payload.get('source_type', 'N/A')}")
    print(f"  URL: {payload.get('url', 'N/A')}")
    print(f"  Content Length: {len(payload.get('content', ''))}")
    print(f"  Created: {payload.get('created_at', 'N/A')}")
    print(f"  Updated: {payload.get('updated_at', 'N/A')}")

    # Show first 200 characters of content
    content = payload.get("content", "")
    if content:
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"  Content Preview: {preview}")
    print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Query QDrant database directly")
    parser.add_argument("--config", required=True, help="Path to config.yaml file")
    parser.add_argument("--env", help="Path to .env file")
    parser.add_argument("--search", help="Search query to test")
    parser.add_argument(
        "--limit", type=int, default=5, help="Number of results to show"
    )

    args = parser.parse_args()

    try:
        # Load configuration
        print("Loading configuration...")
        settings = load_config(args.config, args.env)

        print(f"QDrant URL: {settings.qdrant_url}")
        print(f"Collection: {settings.qdrant_collection_name}")
        print()

        # Create QDrant client
        print("Connecting to QDrant...")
        client = create_qdrant_client(settings)

        # Get collection info
        print("Getting collection information...")
        collection_info = get_collection_info(client, settings.qdrant_collection_name)

        if collection_info:
            print(f"Collection Status: {collection_info.status}")
            print(f"Vector Count: {collection_info.points_count}")
            try:
                vector_size = getattr(
                    collection_info.config.params.vectors, "size", "Unknown"
                )
                print(f"Vector Size: {vector_size}")
            except AttributeError:
                print("Vector Size: Unknown")
            print()
        else:
            print("Could not retrieve collection information.")
            return

        # Count documents by source
        print("Analyzing document sources...")
        source_counts, source_type_counts, total_docs = count_documents_by_source(
            client, settings.qdrant_collection_name
        )

        print(f"Total Documents: {total_docs}")
        print("\nDocuments by Source Type:")
        for source_type, count in source_type_counts.items():
            print(f"  {source_type}: {count}")

        print("\nDocuments by Source:")
        for source, count in source_counts.items():
            print(f"  {source}: {count}")
        print()

        # Get sample documents
        print(f"Sample Documents (showing {args.limit}):")
        sample_docs = get_sample_documents(
            client, settings.qdrant_collection_name, args.limit
        )

        for i, point in enumerate(sample_docs, 1):
            print(f"\n--- Document {i} ---")
            print_document_summary(point)

        # Search if query provided
        if args.search:
            print(f"\nSearch Results for '{args.search}':")
            search_results = search_documents(
                client, settings.qdrant_collection_name, args.search, args.limit
            )

            if search_results:
                for i, point in enumerate(search_results, 1):
                    print(f"\n--- Search Result {i} ---")
                    print_document_summary(point)
            else:
                print("No matching documents found.")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
