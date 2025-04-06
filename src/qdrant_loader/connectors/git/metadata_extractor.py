import chardet
import re
from pathlib import Path
from typing import Dict, Any, List
from git import Repo
import structlog
from qdrant_loader.utils.logger import get_logger

logger = get_logger(__name__)

class GitMetadataExtractor:
    """Extracts metadata from Git repository files."""
    
    def __init__(self, repo: Repo, file_path: str):
        self.repo = repo
        self.file_path = file_path
        self.relative_path = Path(file_path).relative_to(repo.working_dir)
        self.content = None

    def extract_all_metadata(self) -> Dict[str, Any]:
        """Extract all available metadata for the file."""
        try:
            # Load file content once
            self.content = Path(self.file_path).read_text(encoding='utf-8', errors='ignore')
            
            return {
                **self.extract_file_metadata(),
                **self.extract_repo_metadata(),
                **self.extract_git_history(),
                **self.extract_structure_metadata()
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata for {self.file_path}: {e}")
            return {}

    def extract_file_metadata(self) -> Dict[str, Any]:
        """Extract metadata about the file itself."""
        return {
            'file_type': self.relative_path.suffix,
            'file_name': self.relative_path.name,
            'file_directory': str(self.relative_path.parent),
            'file_encoding': self._detect_encoding(),
            'line_count': self._count_lines(),
            'word_count': self._count_words(),
            'has_code_blocks': self._has_code_blocks(),
            'has_images': self._has_images(),
            'has_links': self._has_links()
        }

    def extract_repo_metadata(self) -> Dict[str, Any]:
        """Extract metadata about the repository."""
        try:
            url = self.repo.remotes.origin.url
            # Extract repo name from URL, removing .git suffix if present
            repo_name = url.split('/')[-1].replace('.git', '')
            
            return {
                'repository_name': repo_name,
                'repository_owner': self._get_repo_owner(),
                'repository_description': self._get_repo_description(),
                'repository_language': self._detect_repo_language()
            }
        except Exception as e:
            logger.error(f"Failed to extract repository metadata: {e}")
            return {
                'repository_name': 'unknown',
                'repository_owner': 'unknown',
                'repository_description': '',
                'repository_language': 'unknown'
            }

    def extract_git_history(self) -> Dict[str, Any]:
        """Extract Git history metadata."""
        try:
            commits = list(self.repo.iter_commits(paths=str(self.relative_path)))
            if not commits:
                return {}
                
            return {
                'last_modified_by': commits[0].author.name,
                'commit_message': commits[0].message.strip(),
                'commit_hash': commits[0].hexsha,
                'creation_date': commits[-1].committed_datetime.isoformat(),
                'number_of_commits': len(commits)
            }
        except Exception as e:
            logger.error(f"Failed to extract git history for {self.file_path}: {e}")
            return {}

    def extract_structure_metadata(self) -> Dict[str, Any]:
        """Extract document structure metadata."""
        return {
            'has_toc': self._has_table_of_contents(),
            'heading_levels': self._get_heading_levels(),
            'sections_count': self._count_sections()
        }

    def _detect_encoding(self) -> str:
        """Detect file encoding, defaulting to UTF-8."""
        try:
            with open(self.file_path, 'rb') as f:
                raw = f.read()
                if not raw:
                    return 'utf-8'
                result = chardet.detect(raw)
                # If confidence is high enough and not ASCII, use detected encoding
                if result and result['confidence'] > 0.9 and result['encoding'] != 'ascii':
                    return result['encoding'].lower()
            return 'utf-8'  # Default to UTF-8
        except Exception:
            return 'utf-8'

    def _count_lines(self) -> int:
        """Count lines in file."""
        return len(self.content.splitlines())

    def _count_words(self) -> int:
        """Count words in file."""
        return len(self.content.split())

    def _has_code_blocks(self) -> bool:
        """Check if file contains code blocks."""
        return bool(re.search(r'```[\s\S]*?```', self.content))

    def _has_images(self) -> bool:
        """Check if file contains image references."""
        return bool(re.search(r'!\[.*?\]\(.*?\)', self.content))

    def _has_links(self) -> bool:
        """Check if file contains hyperlinks."""
        return bool(re.search(r'\[.*?\]\(.*?\)', self.content))

    def _get_repo_owner(self) -> str:
        """Extract repository owner from URL."""
        try:
            url = self.repo.remotes.origin.url
            if 'github.com' in url:
                return url.split('/')[-2]
            elif 'gitlab.com' in url:
                return url.split('/')[-2]
            elif 'bitbucket.org' in url:
                return url.split('/')[-2]
        except Exception:
            pass
        return 'unknown'

    def _get_repo_description(self) -> str:
        """Get repository description from config or README."""
        try:
            # First try to get from repo description, but skip if it's the default message
            if (self.repo.description and 
                self.repo.description.strip() and 
                "Unnamed repository;" not in self.repo.description):
                return self.repo.description.strip()
            
            # If not available, try to extract from README
            readme_paths = ['README.md', 'README.txt', 'README', 'README.rst']
            for readme in readme_paths:
                readme_path = Path(self.repo.working_dir) / readme
                if readme_path.exists():
                    content = readme_path.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')
                    
                    # Process the content to find a good description
                    description = ''
                    current_paragraph = []
                    found_title = False
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Skip badges and links at the start
                        if not found_title and (
                            line.startswith('[![') or 
                            line.startswith('![') or
                            line.startswith('[!')
                        ):
                            continue
                            
                        # Identify the title
                        if not found_title:
                            if line and (line.startswith('#') or '===' in line):
                                found_title = True
                            continue
                            
                        # Skip common sections we don't want in the description
                        if line.lower().startswith(('#', '##')) and any(
                            section in line.lower() for section in 
                            ['install', 'usage', 'contributing', 'license', 'test', 'build', 'deploy']
                        ):
                            break
                            
                        # Build paragraphs
                        if line:
                            # Skip lines that are likely not part of the description
                            if not (line.startswith('```') or line.startswith('---') or line.startswith('>')):
                                current_paragraph.append(line)
                        elif current_paragraph:
                            # We found a complete paragraph
                            paragraph = ' '.join(current_paragraph)
                            # Skip short or non-descriptive paragraphs
                            if (len(paragraph) > 50 and 
                                not paragraph.startswith('[![') and
                                not all(char in '[]()!#' for char in paragraph)):
                                description = paragraph
                                break
                            current_paragraph = []
                    
                    # Handle case where description is in the last paragraph
                    if not description and current_paragraph:
                        description = ' '.join(current_paragraph)
                    
                    if description:
                        # Clean up the description
                        description = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', description)  # Convert markdown links to text
                        description = re.sub(r'<[^>]+>', '', description)  # Remove HTML tags
                        description = description.replace('\n', ' ').strip()
                        # Limit length while trying to break at a sentence boundary
                        if len(description) > 200:
                            sentences = re.split(r'(?<=[.!?])\s+', description[:250])
                            description = ' '.join(sentences[:-1]) + '...'
                        return description
            
            return 'No description available'
        except Exception as e:
            logger.error(f"Failed to get repository description: {e}")
            return 'No description available'

    def _detect_repo_language(self) -> str:
        """Detect primary language of repository."""
        # This is a simple implementation. Could be enhanced with more sophisticated detection
        try:
            # Check file extension for common programming languages
            ext = self.relative_path.suffix.lower()
            lang_map = {
                '.py': 'Python',
                '.js': 'JavaScript',
                '.java': 'Java',
                '.md': 'Markdown',
                '.txt': 'Text',
                '.adoc': 'AsciiDoc'
            }
            return lang_map.get(ext, 'Unknown')
        except Exception:
            return 'Unknown'

    def _has_table_of_contents(self) -> bool:
        """Check if file has a table of contents."""
        toc_patterns = [
            r'^#+\s*Table of Contents',
            r'^#+\s*Contents',
            r'^#+\s*TOC',
            r'\[TOC\]'
        ]
        return any(re.search(pattern, self.content, re.MULTILINE) for pattern in toc_patterns)

    def _get_heading_levels(self) -> List[int]:
        """Get list of heading levels used in the document."""
        heading_levels = set()
        for match in re.finditer(r'^(#+)\s', self.content, re.MULTILINE):
            heading_levels.add(len(match.group(1)))
        return sorted(heading_levels)

    def _count_sections(self) -> int:
        """Count number of main sections in the document."""
        return len(re.findall(r'^#\s', self.content, re.MULTILINE)) 