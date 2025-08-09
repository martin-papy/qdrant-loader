#!/usr/bin/env python3
"""
Generate favicon files from SVG icon.
Requires: pip install cairosvg pillow
"""

import os
from pathlib import Path

try:
    import cairosvg
    from PIL import Image
except ImportError:
    print("Missing dependencies. Install with: pip install cairosvg pillow")
    exit(1)


def svg_to_png(svg_path: str, output_path: str, size: int):
    """Convert SVG to PNG at specified size."""
    png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)

    if png_data is None:
        raise ValueError(f"Failed to convert SVG to PNG for size {size}x{size}")

    with open(output_path, "wb") as f:
        f.write(png_data)

    print(f"Generated {output_path} ({size}x{size})")


def generate_ico(png_files: list, ico_path: str):
    """Generate ICO file from PNG files - use 32x32 for better visibility."""
    images = []
    for png_file in png_files:
        if os.path.exists(png_file):
            img = Image.open(png_file)
            # Convert to RGBA if not already
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            print(f"  Found {img.width}x{img.height} PNG")
            images.append(img)
        else:
            print(f"  Warning: {png_file} not found")

    if not images:
        raise ValueError("No valid PNG files found for ICO generation")

    # Use 32x32 as the primary favicon size for better visibility
    # Find the 32x32 image
    favicon_img = None
    for img in images:
        if img.width == 32 and img.height == 32:
            favicon_img = img
            break

    if not favicon_img:
        # Fallback to first available image
        favicon_img = images[0]
        print(f"  No 32x32 found, using {favicon_img.width}x{favicon_img.height}")
    else:
        print("  Using 32x32 for favicon.ico")

    # Save as ICO with single size for maximum compatibility
    favicon_img.save(ico_path, format="ICO")
    print(f"Generated {ico_path} ({favicon_img.width}x{favicon_img.height})")


def main():
    # Paths
    script_dir = Path(__file__).parent
    svg_path = script_dir / "icons" / "qdrant-loader-icon-static.svg"
    favicon_dir = script_dir / "favicons"

    # Create favicon directory
    favicon_dir.mkdir(exist_ok=True)

    # Favicon sizes
    sizes = [16, 32, 48, 64, 96, 128, 180, 192, 512]

    png_files = []

    # Generate PNG favicons
    for size in sizes:
        output_path = favicon_dir / f"favicon-{size}x{size}.png"
        svg_to_png(str(svg_path), str(output_path), size)
        png_files.append(str(output_path))

    # Generate ICO file (for legacy browsers) - include larger sizes for better visibility
    ico_files = [
        favicon_dir / "favicon-16x16.png",
        favicon_dir / "favicon-32x32.png",
        favicon_dir / "favicon-48x48.png",
        favicon_dir / "favicon-64x64.png",
        favicon_dir / "favicon-96x96.png",
        favicon_dir / "favicon-128x128.png",
    ]
    generate_ico([str(f) for f in ico_files], str(favicon_dir / "favicon.ico"))

    # Generate Apple Touch Icon (180x180 is standard)
    apple_icon_path = favicon_dir / "apple-touch-icon.png"
    os.rename(str(favicon_dir / "favicon-180x180.png"), str(apple_icon_path))
    print(f"Generated {apple_icon_path}")

    # Generate Android Chrome icons
    android_192_path = favicon_dir / "android-chrome-192x192.png"
    android_512_path = favicon_dir / "android-chrome-512x512.png"
    os.rename(str(favicon_dir / "favicon-192x192.png"), str(android_192_path))
    os.rename(str(favicon_dir / "favicon-512x512.png"), str(android_512_path))
    print(f"Generated {android_192_path}")
    print(f"Generated {android_512_path}")

    print("\n✅ All favicons generated successfully!")
    print("\nGenerated files:")
    for file in sorted(favicon_dir.glob("*")):
        print(f"  - {file.name}")


if __name__ == "__main__":
    main()
