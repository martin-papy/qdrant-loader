from typing import Dict, Any
import re

class GitMetadata:
    def _extract_structure_metadata(self, content: str) -> Dict[str, Any]:
        """Extract structural metadata from content."""
        metadata = {
            "section_headers": [],
            "code_blocks": [],
            "links": [],
            "images": [],
            "tables": [],
            "lists": [],
            "blockquotes": [],
            "footnotes": [],
            "toc": [],
            "metadata": {},
        }

        # Extract section headers
        header_pattern = r'^(#{1,6})\s+(.+)$'
        for line in content.split('\n'):
            header_match = re.match(header_pattern, line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()
                metadata["section_headers"].append({
                    "level": level,
                    "text": text,
                    "line_number": content.split('\n').index(line) + 1
                })

        # Extract code blocks
        code_block_pattern = r'```[\s\S]*?```'
        for match in re.finditer(code_block_pattern, content):
            code_block = match.group(0)
            metadata["code_blocks"].append({
                "content": code_block,
                "start_line": content[:match.start()].count('\n') + 1,
                "end_line": content[:match.end()].count('\n') + 1
            })

        # Extract links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            metadata["links"].append({
                "text": match.group(1),
                "url": match.group(2)
            })

        # Extract images
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, content):
            metadata["images"].append({
                "alt_text": match.group(1),
                "url": match.group(2)
            })

        # Extract tables
        table_pattern = r'\|.*\|\n\|[\s-:]+\|\n(\|.*\|\n)*'
        for match in re.finditer(table_pattern, content):
            table = match.group(0)
            metadata["tables"].append({
                "content": table,
                "start_line": content[:match.start()].count('\n') + 1,
                "end_line": content[:match.end()].count('\n') + 1
            })

        # Extract lists
        list_pattern = r'^[\s-*+]\s+.+$'
        for line in content.split('\n'):
            if re.match(list_pattern, line):
                metadata["lists"].append({
                    "content": line,
                    "line_number": content.split('\n').index(line) + 1
                })

        # Extract blockquotes
        blockquote_pattern = r'^>\s+.+$'
        for line in content.split('\n'):
            if re.match(blockquote_pattern, line):
                metadata["blockquotes"].append({
                    "content": line,
                    "line_number": content.split('\n').index(line) + 1
                })

        # Extract footnotes
        footnote_pattern = r'\[\^([^\]]+)\]:\s+(.+)$'
        for match in re.finditer(footnote_pattern, content):
            metadata["footnotes"].append({
                "id": match.group(1),
                "content": match.group(2)
            })

        # Extract table of contents
        toc_pattern = r'^#{1,6}\s+.+$'
        for line in content.split('\n'):
            if re.match(toc_pattern, line):
                metadata["toc"].append({
                    "content": line,
                    "line_number": content.split('\n').index(line) + 1
                })

        # Extract front matter metadata if present
        front_matter_pattern = r'^---\n([\s\S]*?)\n---'
        front_matter_match = re.match(front_matter_pattern, content)
        if front_matter_match:
            front_matter = front_matter_match.group(1)
            for line in front_matter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata["metadata"][key.strip()] = value.strip()

        return metadata 