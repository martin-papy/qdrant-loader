"""Utility functions for color name conversion and query construction."""

import re
from typing import Optional


# Comprehensive hex to color name mapping
HEX_TO_COLOR_NAME: dict[str, str] = {
    # Black and grays
    "#000000": "black",
    "#000": "black",
    "#FFFFFF": "white",
    "#FFF": "white",
    "#808080": "gray",
    "#808080": "grey",
    "#C0C0C0": "silver",
    "#696969": "dark gray",
    "#A9A9A9": "dark grey",
    "#D3D3D3": "light gray",
    "#D3D3D3": "light grey",
    # Primary colors
    "#FF0000": "red",
    "#F00": "red",
    "#00FF00": "green",
    "#0F0": "green",
    "#0000FF": "blue",
    "#00F": "blue",
    # Extended reds
    "#FF6347": "tomato",
    "#DC143C": "crimson",
    "#B22222": "firebrick",
    "#8B0000": "dark red",
    "#CD5C5C": "indian red",
    "#F08080": "light coral",
    "#FFA07A": "light salmon",
    "#E9967A": "dark salmon",
    "#FA8072": "salmon",
    "#FF7F50": "coral",
    "#FF4500": "orange red",
    "#FF1493": "deep pink",
    "#FF69B4": "hot pink",
    "#FFB6C1": "light pink",
    "#FFC0CB": "pink",
    "#DB7093": "pale violet red",
    "#C71585": "medium violet red",
    # Extended oranges
    "#FFA500": "orange",
    "#FF8C00": "dark orange",
    "#FF7F00": "orange",
    "#FF6347": "tomato",
    "#FF4500": "orange red",
    "#FFD700": "gold",
    "#FFA500": "orange",
    # Extended yellows
    "#FFFF00": "yellow",
    "#FF0": "yellow",
    "#FFFFE0": "light yellow",
    "#FFFACD": "lemon chiffon",
    "#FAFAD2": "light goldenrod yellow",
    "#FFEFD5": "papaya whip",
    "#FFE4B5": "moccasin",
    "#FFD700": "gold",
    "#FFA500": "orange",
    "#FF8C00": "dark orange",
    "#FF7F50": "coral",
    # Extended greens
    "#008000": "green",
    "#228B22": "forest green",
    "#006400": "dark green",
    "#32CD32": "lime green",
    "#00FF00": "lime",
    "#0F0": "lime",
    "#90EE90": "light green",
    "#98FB98": "pale green",
    "#00FA9A": "medium spring green",
    "#00FF7F": "spring green",
    "#3CB371": "medium sea green",
    "#2E8B57": "sea green",
    "#66CDAA": "medium aquamarine",
    "#7FFFD4": "aquamarine",
    "#40E0D0": "turquoise",
    "#48D1CC": "medium turquoise",
    "#20B2AA": "light sea green",
    "#008B8B": "dark cyan",
    "#00CED1": "dark turquoise",
    # Extended blues
    "#000080": "navy",
    "#00008B": "dark blue",
    "#0000CD": "medium blue",
    "#0000FF": "blue",
    "#00F": "blue",
    "#4169E1": "royal blue",
    "#1E90FF": "dodger blue",
    "#00BFFF": "deep sky blue",
    "#87CEEB": "sky blue",
    "#87CEFA": "light sky blue",
    "#4682B4": "steel blue",
    "#5F9EA0": "cadet blue",
    "#6495ED": "cornflower blue",
    "#7B68EE": "medium slate blue",
    "#6A5ACD": "slate blue",
    "#483D8B": "dark slate blue",
    "#191970": "midnight blue",
    # Extended purples
    "#800080": "purple",
    "#8B008B": "dark magenta",
    "#9400D3": "violet",
    "#9932CC": "dark orchid",
    "#BA55D3": "medium orchid",
    "#DA70D6": "orchid",
    "#EE82EE": "violet",
    "#DDA0DD": "plum",
    "#D8BFD8": "thistle",
    "#E6E6FA": "lavender",
    "#9370DB": "medium purple",
    "#8A2BE2": "blue violet",
    "#4B0082": "indigo",
    "#6A5ACD": "slate blue",
    "#7B68EE": "medium slate blue",
    # Extended browns
    "#A52A2A": "brown",
    "#8B4513": "saddle brown",
    "#A0522D": "sienna",
    "#CD853F": "peru",
    "#DEB887": "burlywood",
    "#F5DEB3": "wheat",
    "#D2B48C": "tan",
    "#BC8F8F": "rosy brown",
    "#F4A460": "sandy brown",
    "#DAA520": "goldenrod",
    "#B8860B": "dark goldenrod",
    "#CD853F": "peru",
    "#D2691E": "chocolate",
    "#8B4513": "saddle brown",
    "#A0522D": "sienna",
    "#654321": "dark brown",
    # Extended beiges/creams
    "#F5F5DC": "beige",
    "#FFE4C4": "bisque",
    "#FFEBCD": "blanched almond",
    "#F5DEB3": "wheat",
    "#FFF8DC": "cornsilk",
    "#FFFAF0": "floral white",
    "#FFFFF0": "ivory",
    "#FAEBD7": "antique white",
    "#FDF5E6": "old lace",
    "#FFFACD": "lemon chiffon",
    "#FFF8DC": "cornsilk",
    # Extended whites
    "#FFFFFF": "white",
    "#FFF": "white",
    "#F8F8FF": "ghost white",
    "#F0F8FF": "alice blue",
    "#F5F5F5": "white smoke",
    "#FAFAFA": "white",
    "#F0F0F0": "light gray",
    "#E0E0E0": "light gray",
    "#D3D3D3": "light gray",
    "#C0C0C0": "silver",
    "#A9A9A9": "dark gray",
    "#808080": "gray",
    "#696969": "dim gray",
    "#555555": "dark gray",
    "#2F2F2F": "dark gray",
    "#1C1C1C": "dark gray",
    "#000000": "black",
}


def hex_to_color_name(hex_code: str) -> Optional[str]:
    """Convert hex color code to color name.
    
    Args:
        hex_code: Hex color code (e.g., "#000000", "#000", "000000")
    
    Returns:
        Color name string (e.g., "black") or None if not found
    
    Examples:
        >>> hex_to_color_name("#000000")
        'black'
        >>> hex_to_color_name("#FF0000")
        'red'
        >>> hex_to_color_name("#000")
        'black'
        >>> hex_to_color_name("invalid")
        None
    """
    if not hex_code:
        return None
    
    # Normalize hex code
    hex_code = hex_code.strip().upper()
    
    # Add # if missing
    if not hex_code.startswith("#"):
        hex_code = "#" + hex_code
    
    # Handle 3-digit hex codes (e.g., #000 -> #000000)
    if len(hex_code) == 4:
        hex_code = "#" + hex_code[1] * 2 + hex_code[2] * 2 + hex_code[3] * 2
    
    # Look up in mapping
    return HEX_TO_COLOR_NAME.get(hex_code)


def build_color_query(hex_code: str, item_type: str = "clothing") -> Optional[str]:
    """Build a semantic search query from a hex color code.
    
    Args:
        hex_code: Hex color code (e.g., "#000000")
        item_type: Type of items to search for (default: "clothing")
    
    Returns:
        Search query string (e.g., "black clothing") or None if color not found
    
    Examples:
        >>> build_color_query("#000000")
        'black clothing'
        >>> build_color_query("#FF0000", "jacket")
        'red jacket'
        >>> build_color_query("#invalid")
        None
    """
    color_name = hex_to_color_name(hex_code)
    if not color_name:
        return None
    
    return f"{color_name} {item_type}"


def build_color_query_generic(hex_code: str) -> Optional[str]:
    """Build a generic semantic search query from a hex color code.
    
    Uses generic terms like "items" or "products" instead of specific item types.
    
    Args:
        hex_code: Hex color code (e.g., "#000000")
    
    Returns:
        Search query string (e.g., "black items") or None if color not found
    
    Examples:
        >>> build_color_query_generic("#000000")
        'black items'
        >>> build_color_query_generic("#FF0000")
        'red items'
    """
    color_name = hex_to_color_name(hex_code)
    if not color_name:
        return None
    
    return f"{color_name} items"


def get_color_name_for_rationale(hex_code: str) -> str:
    """Get color name for use in rationale generation.
    
    Returns a user-friendly color name, or "colorful" as fallback.
    
    Args:
        hex_code: Hex color code (e.g., "#000000")
    
    Returns:
        Color name string, or "colorful" if not found
    
    Examples:
        >>> get_color_name_for_rationale("#000000")
        'black'
        >>> get_color_name_for_rationale("#invalid")
        'colorful'
    """
    color_name = hex_to_color_name(hex_code)
    return color_name if color_name else "colorful"


def is_valid_hex_color(hex_code: str) -> bool:
    """Check if a string is a valid hex color code.
    
    Args:
        hex_code: String to validate
    
    Returns:
        True if valid hex color, False otherwise
    
    Examples:
        >>> is_valid_hex_color("#000000")
        True
        >>> is_valid_hex_color("#000")
        True
        >>> is_valid_hex_color("000000")
        True
        >>> is_valid_hex_color("invalid")
        False
    """
    if not hex_code:
        return False
    
    # Normalize
    hex_code = hex_code.strip().upper()
    if not hex_code.startswith("#"):
        hex_code = "#" + hex_code
    
    # Check pattern: #RRGGBB or #RGB
    pattern = r"^#[0-9A-F]{3}([0-9A-F]{3})?$"
    return bool(re.match(pattern, hex_code))
