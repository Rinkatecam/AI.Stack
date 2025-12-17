"""
title: Files & Documents Tool
version: 2.0.0
description: Search, read, and semantically query files with RAG support. Includes PDF reading with OCR and Qdrant vector search integration.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack
requirements: pydantic, pymupdf, pytesseract, pdf2image, pillow, qdrant-client

# SYSTEM PROMPT FOR AI - READ THIS CAREFULLY
# ==========================================
# You have access to the user's file system AND semantic search through this tool.
#
# TWO TYPES OF SEARCH:
#   1. BASIC SEARCH - Find files by name, read content, grep-like search
#   2. SEMANTIC SEARCH (RAG) - Search by meaning using Qdrant vector database
#
# WHEN TO USE WHAT:
#   - "Find file named config.yaml" → find_files("config.yaml")
#   - "Search for files about authentication" → semantic_search("authentication")
#   - "What do my documents say about quality control?" → ask_documents("quality control")
#
# IMPORTANT PATHS (inside Docker container):
#   /data/user-files     - User's workspace (READ + WRITE)
#   /data/projects       - Projects folder (READ + WRITE)
#   /data/home           - User's home directory (READ-ONLY)
#
# RAG FUNCTIONS:
#   index_folder(path)        - Index a folder into Qdrant for semantic search
#   semantic_search(query)    - Search indexed documents by meaning
#   ask_documents(question)   - Ask questions about indexed documents
#   list_indexed()            - Show what collections are indexed
"""

import os
import re
import fnmatch
import pathlib
import datetime
import hashlib
import platform
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field

# PDF support
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# OCR support for scanned PDFs
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# Qdrant for RAG
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

SYSTEM = platform.system()

# Configuration
MAX_BYTES = int(os.getenv("FILE_MAX_BYTES", "200000"))
MAX_RESULTS = int(os.getenv("FILE_MAX_RESULTS", "200"))
QDRANT_HOST = os.getenv("QDRANT_HOST", "aistack-vector")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://aistack-llm:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


def _get_home_dir() -> str:
    """Get user's home directory."""
    return os.path.expanduser("~")


def _get_common_locations() -> List[str]:
    """Get list of common searchable locations."""
    locations = []

    # Docker container paths
    if os.path.exists("/data/user-files") or os.path.exists("/data/home"):
        locations = [
            "/data/projects",
            "/data/user-files",
            "/data/home",
        ]
        for subdir in ["Documents", "Desktop", "Downloads"]:
            path = f"/data/home/{subdir}"
            if os.path.exists(path):
                locations.append(path)
    else:
        # Local paths
        home = _get_home_dir()
        locations = [
            os.path.join(home, "Documents"),
            os.path.join(home, "Desktop"),
            os.path.join(home, "Downloads"),
            home,
        ]

    return [loc for loc in locations if loc and os.path.exists(loc)]


def _get_default_root() -> str:
    """Get default root directory."""
    locations = _get_common_locations()
    return locations[0] if locations else _get_home_dir()


FILE_ROOT = os.getenv("FILE_ROOT", _get_default_root())


# Text file extensions
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst",
    ".cfg", ".conf", ".ini", ".env", ".yaml", ".yml", ".toml", ".json",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash",
    ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb", ".php",
    ".html", ".htm", ".xml", ".css", ".scss", ".sql",
    ".log", ".csv", ".tsv",
}

TEXT_FILENAMES = {
    "Dockerfile", "Makefile", "README", "LICENSE", "CHANGELOG",
    ".env", ".gitignore", ".dockerignore",
}


def _is_text_like(p: pathlib.Path) -> bool:
    """Check if file is likely a text file."""
    if p.name in TEXT_FILENAMES:
        return True
    return p.suffix.lower() in TEXT_EXTENSIONS


def _read_text(p: pathlib.Path, max_bytes: int = MAX_BYTES) -> Optional[str]:
    """Read file with encoding detection."""
    try:
        data = p.read_bytes()[:max_bytes]
        for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def _read_pdf(p: pathlib.Path, max_pages: int = 50) -> Optional[str]:
    """Read text from PDF, with OCR fallback for scanned documents."""
    if not PDF_SUPPORT:
        return None

    try:
        doc = fitz.open(str(p))
        text_parts = []
        total_pages = len(doc)
        pages_to_read = min(total_pages, max_pages)

        for page_num in range(pages_to_read):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()

        # Try OCR if no text found
        if not text_parts and OCR_SUPPORT:
            return _read_pdf_ocr(p, max_pages=min(10, max_pages))

        if not text_parts:
            return "[PDF contains no extractable text - may be scanned]"

        result = "\n\n".join(text_parts)
        if total_pages > max_pages:
            result += f"\n\n[...truncated, showing {max_pages} of {total_pages} pages]"

        return result
    except Exception as e:
        return f"[Error reading PDF: {str(e)}]"


def _read_pdf_ocr(p: pathlib.Path, max_pages: int = 10, language: str = "eng+deu") -> Optional[str]:
    """Read scanned PDF using OCR."""
    if not OCR_SUPPORT:
        return None

    try:
        images = convert_from_path(str(p), first_page=1, last_page=max_pages, dpi=300)
        text_parts = []

        for page_num, image in enumerate(images, 1):
            text = pytesseract.image_to_string(image, lang=language)
            if text.strip():
                text_parts.append(f"--- Page {page_num} (OCR) ---\n{text}")

        return "\n\n".join(text_parts) if text_parts else None
    except Exception:
        return None


def _format_size(size_bytes: int) -> str:
    """Format file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _iter_files(root: pathlib.Path, max_files: int = 10000, max_depth: int = 10):
    """Iterate files safely."""
    count = 0
    root_depth = len(root.parts)
    skip_dirs = ['node_modules', '.git', '__pycache__', '.venv', 'venv', '.cache']

    try:
        for p in root.rglob("*"):
            if count >= max_files:
                break
            if len(p.parts) - root_depth > max_depth:
                continue
            if any(skip_dir in str(p).lower() for skip_dir in skip_dirs):
                continue
            if p.is_file():
                yield p
                count += 1
    except (OSError, PermissionError):
        pass


class Tools:
    class Valves(BaseModel):
        """Configuration options."""
        search_all_by_default: bool = Field(
            default=True,
            description="Search all locations by default"
        )
        max_results: int = Field(
            default=200,
            description="Maximum search results"
        )
        max_file_size_kb: int = Field(
            default=200,
            description="Maximum file size to read (KB)"
        )
        qdrant_host: str = Field(
            default="aistack-vector",
            description="Qdrant server hostname"
        )
        qdrant_port: int = Field(
            default=6333,
            description="Qdrant server port"
        )
        embedding_model: str = Field(
            default="nomic-embed-text",
            description="Ollama embedding model for RAG"
        )
        default_collection: str = Field(
            default="documents",
            description="Default Qdrant collection name"
        )

    def __init__(self):
        self.citation = True
        self.valves = self.Valves()
        self._qdrant_client = None

    def _get_qdrant(self):
        """Get Qdrant client."""
        if not QDRANT_AVAILABLE:
            return None
        if self._qdrant_client is None:
            try:
                self._qdrant_client = QdrantClient(
                    host=self.valves.qdrant_host,
                    port=self.valves.qdrant_port
                )
            except Exception:
                return None
        return self._qdrant_client

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding vector from Ollama."""
        import urllib.request
        import json

        try:
            url = f"{OLLAMA_HOST}/api/embeddings"
            data = json.dumps({
                "model": self.valves.embedding_model,
                "prompt": text
            }).encode('utf-8')

            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('embedding')
        except Exception:
            return None

    # ==================== BASIC FILE OPERATIONS ====================

    def find_files(self, query: str, fuzzy: bool = False, search_in: str = "", search_all: bool = True) -> str:
        """
        Find files by name pattern.

        Args:
            query: Search pattern (substring, glob like '*.pdf', or regex with 'r:' prefix)
            fuzzy: Enable fuzzy matching for typos
            search_in: Specific path to search in
            search_all: Search all common locations

        Returns:
            List of matching files with metadata

        Example:
            find_files("report")
            find_files("*.pdf", search_all=True)
            find_files("r:test_\\d+\\.py")
        """
        if search_in:
            roots = [pathlib.Path(search_in)] if os.path.exists(search_in) else []
        elif search_all:
            roots = [pathlib.Path(loc) for loc in _get_common_locations()]
        else:
            roots = [pathlib.Path(FILE_ROOT)]

        if not roots:
            return f"Error: Path not found"

        q = query.strip()
        if not q:
            return "Error: Please provide a search query."

        is_regex = q.startswith("r:")
        if is_regex:
            try:
                pattern = re.compile(q[2:], re.IGNORECASE)
            except re.error as e:
                return f"Error: Invalid regex: {e}"

        hits = []
        for root in roots:
            if not root.exists():
                continue
            for f in _iter_files(root):
                name = f.name
                matched = False

                if is_regex:
                    matched = pattern.search(name) is not None
                elif fuzzy:
                    matched = q.lower() in name.lower() or all(c in name.lower() for c in q.lower())
                else:
                    matched = fnmatch.fnmatch(name.lower(), q.lower()) or q.lower() in name.lower()

                if matched:
                    try:
                        stat = f.stat()
                        hits.append({
                            "path": str(f),
                            "name": name,
                            "size": _format_size(stat.st_size),
                            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        })
                    except:
                        pass

                if len(hits) >= self.valves.max_results:
                    break

        if not hits:
            return f"No files found matching '{query}'"

        lines = [f"Found {len(hits)} file(s) matching '{query}':\n"]
        for h in hits:
            lines.append(f"  {h['path']}")
            lines.append(f"    Size: {h['size']} | Modified: {h['modified']}")

        return "\n".join(lines)

    def read_file(self, path: str, lines: Optional[str] = None) -> str:
        """
        Read content of a file.

        Args:
            path: Path to file (absolute, relative, or ~/...)
            lines: Optional line range like "1-50"

        Returns:
            File content

        Example:
            read_file("/data/home/Documents/report.txt")
            read_file("~/config.yaml")
        """
        if path.startswith("~"):
            p = pathlib.Path(os.path.expanduser(path))
        elif os.path.isabs(path):
            p = pathlib.Path(path)
        else:
            p = pathlib.Path(FILE_ROOT) / path

        if not p.exists():
            return f"Error: File not found: {path}"

        if p.is_dir():
            return f"Error: '{path}' is a directory. Use list_directory() instead."

        # PDF
        if p.suffix.lower() == ".pdf":
            if not PDF_SUPPORT:
                return "Error: PDF support not available (install pymupdf)"
            text = _read_pdf(p)
            return f"PDF: {p}\n\n{text}"

        # Text files
        if not _is_text_like(p):
            return f"Error: '{path}' appears to be a binary file"

        text = _read_text(p, self.valves.max_file_size_kb * 1024)
        if text is None:
            return f"Error: Could not read file: {path}"

        if lines:
            try:
                if "-" in lines:
                    start, end = map(int, lines.split("-"))
                else:
                    start = int(lines)
                    end = start + 50
                all_lines = text.splitlines()
                selected = all_lines[start-1:end]
                text = "\n".join(f"{i+start}: {line}" for i, line in enumerate(selected))
            except:
                pass

        return f"File: {p}\nSize: {_format_size(p.stat().st_size)}\n\n{text}"

    def list_directory(self, path: str = "", show_hidden: bool = False) -> str:
        """
        List contents of a directory.

        Args:
            path: Directory path (empty for default)
            show_hidden: Include hidden files

        Returns:
            Directory listing
        """
        if not path:
            target = pathlib.Path(FILE_ROOT)
        elif path.startswith("~"):
            target = pathlib.Path(os.path.expanduser(path))
        elif os.path.isabs(path):
            target = pathlib.Path(path)
        else:
            target = pathlib.Path(FILE_ROOT) / path

        if not target.exists():
            return f"Error: Directory not found: {path or FILE_ROOT}"

        if not target.is_dir():
            return f"Error: Not a directory: {path}"

        try:
            entries = []
            for item in sorted(target.iterdir()):
                if not show_hidden and item.name.startswith("."):
                    continue
                if item.is_dir():
                    entries.append(f"  [DIR]  {item.name}/")
                else:
                    size = _format_size(item.stat().st_size)
                    entries.append(f"  [FILE] {item.name} ({size})")

            if not entries:
                return f"Directory '{target}' is empty."

            return f"Contents of '{target}':\n\n" + "\n".join(entries)
        except Exception as e:
            return f"Error: {e}"

    def search_content(self, pattern: str, file_pattern: str = "*", search_all: bool = True) -> str:
        """
        Search for text within files (like grep).

        Args:
            pattern: Text to search for
            file_pattern: Glob to filter files (e.g., "*.py")
            search_all: Search all locations

        Returns:
            Matching lines with file paths
        """
        if search_all:
            roots = [pathlib.Path(loc) for loc in _get_common_locations()]
        else:
            roots = [pathlib.Path(FILE_ROOT)]

        regex = re.compile(re.escape(pattern), re.IGNORECASE)
        results = []
        files_searched = 0

        for root in roots:
            if not root.exists():
                continue
            for f in _iter_files(root, max_files=5000):
                if file_pattern != "*" and not fnmatch.fnmatch(f.name, file_pattern):
                    continue

                if f.suffix.lower() == ".pdf":
                    if PDF_SUPPORT:
                        text = _read_pdf(f, max_pages=10)
                        files_searched += 1
                    else:
                        continue
                elif _is_text_like(f):
                    text = _read_text(f)
                    files_searched += 1
                else:
                    continue

                if not text:
                    continue

                for line_num, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        results.append({
                            "file": str(f),
                            "line": line_num,
                            "content": line.strip()[:200]
                        })

                if len(results) >= 100:
                    break

        if not results:
            return f"No matches for '{pattern}' ({files_searched} files searched)"

        lines = [f"Found {len(results)} match(es) for '{pattern}':\n"]
        current_file = ""
        for r in results:
            if r["file"] != current_file:
                current_file = r["file"]
                lines.append(f"\n{current_file}:")
            lines.append(f"  {r['line']}: {r['content']}")

        return "\n".join(lines)

    # ==================== RAG / SEMANTIC SEARCH ====================

    def index_folder(self, path: str, collection: str = "") -> str:
        """
        Index a folder into Qdrant for semantic search.

        Args:
            path: Folder path to index
            collection: Collection name (default from settings)

        Returns:
            Indexing status

        Example:
            index_folder("/data/projects/docs")
            index_folder("~/Documents", collection="my_docs")
        """
        if not QDRANT_AVAILABLE:
            return "Error: Qdrant not available (install qdrant-client)"

        client = self._get_qdrant()
        if not client:
            return "Error: Could not connect to Qdrant"

        # Resolve path
        if path.startswith("~"):
            folder = pathlib.Path(os.path.expanduser(path))
        else:
            folder = pathlib.Path(path)

        if not folder.exists():
            return f"Error: Folder not found: {path}"

        collection = collection or self.valves.default_collection

        # Create collection if needed
        try:
            collections = [c.name for c in client.get_collections().collections]
            if collection not in collections:
                # Get embedding dimension from test
                test_embedding = self._get_embedding("test")
                if not test_embedding:
                    return "Error: Could not get embedding from Ollama"

                client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=len(test_embedding), distance=Distance.COSINE)
                )
        except Exception as e:
            return f"Error creating collection: {e}"

        # Index files
        indexed = 0
        errors = 0

        for f in _iter_files(folder, max_files=1000):
            # Read content
            if f.suffix.lower() == ".pdf" and PDF_SUPPORT:
                content = _read_pdf(f, max_pages=20)
            elif _is_text_like(f):
                content = _read_text(f)
            else:
                continue

            if not content or len(content) < 50:
                continue

            # Get embedding
            embedding = self._get_embedding(content[:8000])
            if not embedding:
                errors += 1
                continue

            # Store in Qdrant
            try:
                point_id = int(hashlib.md5(str(f).encode()).hexdigest()[:8], 16)
                client.upsert(
                    collection_name=collection,
                    points=[PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "path": str(f),
                            "name": f.name,
                            "content_preview": content[:500],
                            "indexed_at": datetime.datetime.now().isoformat()
                        }
                    )]
                )
                indexed += 1
            except Exception:
                errors += 1

        return f"Indexed {indexed} files into collection '{collection}' ({errors} errors)"

    def semantic_search(self, query: str, collection: str = "", limit: int = 5) -> str:
        """
        Search indexed documents by meaning (semantic search).

        Args:
            query: What to search for (natural language)
            collection: Collection to search (default from settings)
            limit: Max results

        Returns:
            Relevant documents

        Example:
            semantic_search("authentication implementation")
            semantic_search("quality control procedures")
        """
        if not QDRANT_AVAILABLE:
            return "Error: Qdrant not available"

        client = self._get_qdrant()
        if not client:
            return "Error: Could not connect to Qdrant"

        collection = collection or self.valves.default_collection

        # Get query embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return "Error: Could not generate embedding for query"

        # Search
        try:
            results = client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=limit
            )
        except Exception as e:
            return f"Error searching: {e}"

        if not results:
            return f"No relevant documents found for: {query}"

        lines = [f"Semantic search results for: '{query}'\n"]
        for i, r in enumerate(results, 1):
            payload = r.payload
            lines.append(f"{i}. {payload.get('name', 'Unknown')} (score: {r.score:.3f})")
            lines.append(f"   Path: {payload.get('path', 'N/A')}")
            preview = payload.get('content_preview', '')[:200]
            if preview:
                lines.append(f"   Preview: {preview}...")
            lines.append("")

        return "\n".join(lines)

    def ask_documents(self, question: str, collection: str = "") -> str:
        """
        Ask a question and get answers from indexed documents (RAG).

        Args:
            question: Your question in natural language
            collection: Collection to search

        Returns:
            Relevant context from documents to answer your question

        Example:
            ask_documents("How does the authentication system work?")
            ask_documents("What are the quality requirements?")
        """
        # Use semantic search to find relevant docs
        search_result = self.semantic_search(question, collection, limit=3)

        if "Error" in search_result or "No relevant" in search_result:
            return search_result

        return f"Based on your indexed documents:\n\n{search_result}\n\nUse this context to answer: {question}"

    def list_indexed(self) -> str:
        """
        Show all indexed collections and their statistics.

        Returns:
            List of collections with document counts
        """
        if not QDRANT_AVAILABLE:
            return "Error: Qdrant not available"

        client = self._get_qdrant()
        if not client:
            return "Error: Could not connect to Qdrant"

        try:
            collections = client.get_collections().collections

            if not collections:
                return "No indexed collections found.\n\nUse index_folder(path) to index documents."

            lines = ["Indexed Collections:\n"]
            for coll in collections:
                info = client.get_collection(coll.name)
                lines.append(f"  • {coll.name}: {info.points_count} documents")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def get_environment_info(self) -> str:
        """
        Get information about available paths and RAG status.

        Returns:
            Environment info
        """
        locations = _get_common_locations()

        info = [
            "=" * 50,
            "FILES & DOCUMENTS TOOL - ENVIRONMENT",
            "=" * 50,
            "",
            f"Default search path: {FILE_ROOT}",
            f"PDF Support: {'Yes' if PDF_SUPPORT else 'No'}",
            f"OCR Support: {'Yes' if OCR_SUPPORT else 'No'}",
            f"RAG/Qdrant Support: {'Yes' if QDRANT_AVAILABLE else 'No'}",
            "",
            "Available paths:"
        ]

        for loc in locations:
            try:
                count = sum(1 for _ in pathlib.Path(loc).iterdir())
                info.append(f"  {loc} ({count} items)")
            except:
                info.append(f"  {loc} (access denied)")

        info.extend([
            "",
            "BASIC SEARCH:",
            "  find_files('*.pdf')           - Find by name",
            "  search_content('keyword')     - Search inside files",
            "  read_file('/path/to/file')    - Read content",
            "",
            "SEMANTIC SEARCH (RAG):",
            "  index_folder('/path')         - Index for semantic search",
            "  semantic_search('question')   - Search by meaning",
            "  ask_documents('question')     - Q&A from documents",
        ])

        return "\n".join(info)
