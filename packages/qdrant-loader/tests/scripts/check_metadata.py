#!/usr/bin/env python3
"""
Metadata Analysis Script

This script examines the metadata fields captured in QDrant documents
to verify what information is being extracted from Confluence Data Center.
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


def analyze_metadata(client: QdrantClient, collection_name: str, limit: int = 10):
    """Analyze metadata fields across multiple documents."""
    try:
        points = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )[0]

        print(f"Analyzing metadata from {len(points)} documents...\n")

        # Collect all unique metadata keys
        all_keys = set()
        metadata_analysis = {}

        for i, point in enumerate(points):
            payload = point.payload or {}

            print(f"=== Document {i+1} (ID: {point.id}) ===")
            print(f"Payload keys: {list(payload.keys())}")

            # Add keys to our collection
            all_keys.update(payload.keys())

            # Analyze each field
            for key, value in payload.items():
                if key not in metadata_analysis:
                    metadata_analysis[key] = {
                        "count": 0,
                        "sample_values": [],
                        "types": set(),
                        "null_count": 0,
                    }

                metadata_analysis[key]["count"] += 1
                metadata_analysis[key]["types"].add(type(value).__name__)

                if value is None or value == "N/A" or value == "":
                    metadata_analysis[key]["null_count"] += 1
                elif len(metadata_analysis[key]["sample_values"]) < 3:
                    # Store sample values (truncate if too long)
                    sample_value = str(value)
                    if len(sample_value) > 100:
                        sample_value = sample_value[:100] + "..."
                    metadata_analysis[key]["sample_values"].append(sample_value)

            # Show detailed payload for first few documents
            if i < 3:
                print("Full payload:")
                for key, value in payload.items():
                    if isinstance(value, str) and len(value) > 200:
                        print(f"  {key}: {value[:200]}...")
                    else:
                        print(f"  {key}: {value}")
                print("-" * 80)
            else:
                print("(Payload details truncated for brevity)")
                print("-" * 40)

        # Summary analysis
        print("\n=== METADATA ANALYSIS SUMMARY ===")
        print(f"Total documents analyzed: {len(points)}")
        print(f"Unique metadata fields found: {len(all_keys)}")
        print(f"All fields: {sorted(all_keys)}")

        print("\n=== FIELD ANALYSIS ===")
        for field in sorted(all_keys):
            analysis = metadata_analysis[field]
            print(f"\nField: {field}")
            print(f"  Present in: {analysis['count']}/{len(points)} documents")
            print(f"  Data types: {', '.join(analysis['types'])}")
            print(f"  Null/empty values: {analysis['null_count']}")
            if analysis["sample_values"]:
                print(f"  Sample values: {analysis['sample_values']}")

        # Check for missing expected fields
        expected_fields = [
            "title",
            "content",
            "source",
            "source_type",
            "url",
            "created_at",
            "updated_at",
            "metadata",
        ]

        print("\n=== EXPECTED FIELDS CHECK ===")
        for field in expected_fields:
            if field in all_keys:
                analysis = metadata_analysis[field]
                status = (
                    "✅"
                    if analysis["null_count"] == 0
                    else f"⚠️ ({analysis['null_count']} null)"
                )
                print(f"{status} {field}")
            else:
                print(f"❌ {field} - MISSING")

        return points

    except Exception as e:
        print(f"Error analyzing metadata: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Analyze QDrant document metadata")
    parser.add_argument("--config", required=True, help="Path to config.yaml file")
    parser.add_argument("--env", help="Path to .env file")
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of documents to analyze"
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

        # Analyze metadata
        analyze_metadata(client, settings.qdrant_collection_name, args.limit)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
