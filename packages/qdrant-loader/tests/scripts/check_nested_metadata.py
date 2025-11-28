#!/usr/bin/env python3
"""
Nested Metadata Analysis Script

This script examines the nested metadata field to see all the Confluence-specific
information that's being captured from Confluence Data Center.
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


def analyze_nested_metadata(client: QdrantClient, collection_name: str, limit: int = 3):
    """Analyze the nested metadata field in detail."""
    try:
        points = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )[0]

        print(f"Analyzing nested metadata from {len(points)} documents...\n")

        # Collect all unique metadata keys from the nested metadata field
        all_nested_keys = set()
        nested_metadata_analysis = {}

        for i, point in enumerate(points):
            payload = point.payload or {}
            nested_metadata = payload.get("metadata", {})

            print(f"=== Document {i+1} ===")
            print(f"Document ID: {point.id}")
            print(f"Confluence Page ID: {nested_metadata.get('id', 'N/A')}")
            print(f"Title: {nested_metadata.get('title', 'N/A')}")
            print(f"Space: {nested_metadata.get('space', 'N/A')}")
            print(f"Type: {nested_metadata.get('type', 'N/A')}")
            print(f"Author: {nested_metadata.get('author', 'N/A')}")
            print(f"Version: {nested_metadata.get('version', 'N/A')}")
            print(f"Created: {nested_metadata.get('created_at', 'N/A')}")
            print(f"Updated: {nested_metadata.get('updated_at', 'N/A')}")
            print(f"Labels: {nested_metadata.get('labels', [])}")
            print(f"Comments: {len(nested_metadata.get('comments', []))} comments")

            # Add keys to our collection
            all_nested_keys.update(nested_metadata.keys())

            # Analyze each nested field
            for key, value in nested_metadata.items():
                if key not in nested_metadata_analysis:
                    nested_metadata_analysis[key] = {
                        "count": 0,
                        "sample_values": [],
                        "types": set(),
                        "null_count": 0,
                    }

                nested_metadata_analysis[key]["count"] += 1
                nested_metadata_analysis[key]["types"].add(type(value).__name__)

                if (
                    value is None
                    or value == "N/A"
                    or value == ""
                    or (isinstance(value, list) and len(value) == 0)
                ):
                    nested_metadata_analysis[key]["null_count"] += 1
                elif len(nested_metadata_analysis[key]["sample_values"]) < 2:
                    # Store sample values (truncate if too long)
                    sample_value = str(value)
                    if len(sample_value) > 100:
                        sample_value = sample_value[:100] + "..."
                    nested_metadata_analysis[key]["sample_values"].append(sample_value)

            print("\nAll nested metadata keys:")
            for key in sorted(nested_metadata.keys()):
                value = nested_metadata[key]
                if isinstance(value, list | dict):
                    print(f"  {key}: {type(value).__name__} (length: {len(value)})")
                else:
                    print(f"  {key}: {value}")

            print("-" * 80)

        # Summary analysis
        print("\n=== NESTED METADATA ANALYSIS SUMMARY ===")
        print(f"Total documents analyzed: {len(points)}")
        print(f"Unique nested metadata fields found: {len(all_nested_keys)}")
        print(f"All nested fields: {sorted(all_nested_keys)}")

        print("\n=== NESTED FIELD ANALYSIS ===")
        for field in sorted(all_nested_keys):
            analysis = nested_metadata_analysis[field]
            print(f"\nField: {field}")
            print(f"  Present in: {analysis['count']}/{len(points)} documents")
            print(f"  Data types: {', '.join(analysis['types'])}")
            print(f"  Null/empty values: {analysis['null_count']}")
            if analysis["sample_values"]:
                print(f"  Sample values: {analysis['sample_values']}")

        # Check for expected Confluence fields
        expected_confluence_fields = [
            "id",
            "title",
            "space",
            "version",
            "type",
            "author",
            "labels",
            "comments",
            "updated_at",
            "created_at",
        ]

        print("\n=== EXPECTED CONFLUENCE FIELDS CHECK ===")
        for field in expected_confluence_fields:
            if field in all_nested_keys:
                analysis = nested_metadata_analysis[field]
                status = (
                    "✅"
                    if analysis["null_count"] == 0
                    else f"⚠️ ({analysis['null_count']} null/empty)"
                )
                print(f"{status} {field}")
            else:
                print(f"❌ {field} - MISSING")

        return points

    except Exception as e:
        print(f"Error analyzing nested metadata: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Analyze nested metadata in QDrant documents"
    )
    parser.add_argument("--config", required=True, help="Path to config.yaml file")
    parser.add_argument("--env", help="Path to .env file")
    parser.add_argument(
        "--limit", type=int, default=3, help="Number of documents to analyze"
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
        client = create_qdrant_client(settings)

        # Analyze nested metadata
        analyze_nested_metadata(client, settings.qdrant_collection_name, args.limit)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
