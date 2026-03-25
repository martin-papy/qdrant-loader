"""Helper functions for integrating color picker with search queries."""

from typing import Any

from .color_utils import (
    build_color_query_generic,
    get_color_name_for_rationale,
    is_valid_hex_color,
)


def prepare_color_search_request(
    hex_color: str, item_type: str = "items"
) -> dict[str, Any]:
    """Prepare a search request from a hex color code.
    
    This function converts a hex color to a searchable query and provides
    metadata for rationale generation. Use this in your Color Fact application
    when the user selects a color from the color picker.
    
    Args:
        hex_color: Hex color code (e.g., "#FF0000", "#000000")
        item_type: Type of items to search for (default: "items")
    
    Returns:
        Dictionary with:
            - "query": Search query string (e.g., "red items")
            - "color_name": Color name (e.g., "red")
            - "is_valid": Whether the hex color is valid
            - "original_hex": Original hex color code
    
    Examples:
        >>> prepare_color_search_request("#FF0000")
        {
            "query": "red items",
            "color_name": "red",
            "is_valid": True,
            "original_hex": "#FF0000"
        }
        
        >>> prepare_color_search_request("#000000", "clothing")
        {
            "query": "black clothing",
            "color_name": "black",
            "is_valid": True,
            "original_hex": "#000000"
        }
        
        >>> prepare_color_search_request("invalid")
        {
            "query": None,
            "color_name": "colorful",
            "is_valid": False,
            "original_hex": "invalid"
        }
    """
    # Validate hex color
    is_valid = is_valid_hex_color(hex_color)
    
    if not is_valid:
        return {
            "query": None,
            "color_name": "colorful",
            "is_valid": False,
            "original_hex": hex_color,
        }
    
    # Build search query
    if item_type == "items":
        query = build_color_query_generic(hex_color)
    else:
        from .color_utils import build_color_query
        query = build_color_query(hex_color, item_type)
    
    # Get color name for rationale
    color_name = get_color_name_for_rationale(hex_color)
    
    return {
        "query": query,
        "color_name": color_name,
        "is_valid": True,
        "original_hex": hex_color,
    }


def generate_color_rationale(
    color_name: str,
    result_count: int = 0,
    item_type: str = "products",
) -> str:
    """Generate recommendation rationale for color-based search.
    
    Args:
        color_name: Color name (e.g., "red", "black")
        result_count: Number of search results found
        item_type: Type of items (default: "products")
    
    Returns:
        Formatted rationale string
    
    Examples:
        >>> generate_color_rationale("red", 5)
        "You're looking for red products! Red is a fantastic choice..."
        
        >>> generate_color_rationale("black", 0)
        "You're looking for black products! Black is a fantastic choice...
        Unfortunately, I found 0 products matching your black color preference..."
    """
    # Color-specific descriptions
    color_descriptions = {
        "black": "incredibly versatile - they're a wardrobe staple that can be dressed up for a night out, worn casually for everyday errands, or even layered for a bit of extra warmth and style. They're perfect for adding a sleek finish to almost any outfit, no matter the occasion or season.",
        "red": "bold and vibrant, perfect for making a statement. Red items bring energy and passion to any look, whether it's a striking accessory or a standout piece that commands attention.",
        "white": "clean and timeless, offering a fresh, crisp look that works in any season. White items are versatile and can be easily paired with other colors or worn alone for a minimalist aesthetic.",
        "blue": "classic and reliable, offering a sense of calm and professionalism. Blue items are versatile enough for both casual and formal settings, making them a smart choice for any wardrobe.",
        "green": "fresh and natural, bringing a sense of tranquility and connection to nature. Green items can range from vibrant emerald to calming sage, offering versatility for different styles.",
        "yellow": "bright and cheerful, perfect for adding a pop of sunshine to any outfit. Yellow items bring energy and optimism, making them ideal for spring and summer looks.",
        "orange": "warm and energetic, combining the vibrancy of red with the cheerfulness of yellow. Orange items are perfect for making a bold, confident statement.",
        "purple": "rich and sophisticated, offering a sense of luxury and creativity. Purple items can range from deep violet to soft lavender, providing options for various styles.",
        "pink": "playful and feminine, offering a range from soft pastels to vibrant fuchsia. Pink items bring a touch of romance and fun to any look.",
        "gray": "neutral and sophisticated, offering a modern, minimalist aesthetic. Gray items are incredibly versatile and can serve as a perfect base for any outfit.",
        "brown": "warm and earthy, bringing a sense of natural elegance. Brown items offer a classic, timeless look that works well in both casual and formal settings.",
    }
    
    # Get color description or use generic
    color_desc = color_descriptions.get(
        color_name.lower(), 
        f"a fantastic choice that brings style and personality to any look. {color_name.capitalize()} items are versatile and can be easily incorporated into various outfits and settings."
    )
    
    # Build rationale
    if color_name and color_name != "colorful":
        rationale = f"You're looking for {color_name} {item_type}! "
        rationale += f"{color_name.capitalize()} is {color_desc} "
    else:
        rationale = f"You're looking for colorful {item_type}! "
        rationale += "Colorful hues are fantastic for bringing energy, joy, and a playful vibe into any space or outfit. "
        rationale += "They're often found in fun home decor, kids' toys, festive party supplies, or vibrant fashion accessories, "
        rationale += "perfect for sparking creativity or making a bold statement. "
    
    # Add result count message
    if result_count == 0:
        rationale += f"\n\nUnfortunately, I found {result_count} {item_type} matching your {color_name or 'colorful'} color preference. "
        rationale += "It looks like we couldn't find an exact match right now. "
        rationale += "Try different colors or adjust your filters to explore more options!"
    else:
        rationale += f"\n\nI found {result_count} {item_type} that match your {color_name or 'colorful'} color preference perfectly "
        rationale += f"and could be just what you're looking for..."
    
    return rationale
