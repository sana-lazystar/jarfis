"""JARFIS Wiki Semantic Search — sentence-transformers bge-m3 based.

Subcommands:
    index <org_root>                   Build/rebuild embedding index for wiki
    search <org_root> <query> [--top-k N]  Semantic search over wiki (default top-k=5)
    status <org_root>                  Show index status (file count, staleness)
"""

import json
import os
import re
import sys
import time

from .utils import json_error, json_output

# --- Constants ---
WIKI_REL = os.path.join(".jarfis", "wiki")
VECTORS_FILE = ".vectors.npz"
META_FILE = ".vectors-meta.json"
DEFAULT_TOP_K = 5
CHUNK_TOKEN_THRESHOLD = 500  # approx chars * 0.25; we use char count / 4 as proxy
SCORE_THRESHOLD = 0.5
MODEL_NAME = "BAAI/bge-m3"


VENV_DIR = os.path.join(os.path.expanduser("~"), ".claude", ".jarfis-venv")


def _ensure_dependencies():
    """Check that sentence-transformers and numpy are available."""
    try:
        import numpy  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        json_error(
            "sentence-transformers is not installed. "
            "Run /jarfis:wiki-search-setup to install.",
            hint="/jarfis:wiki-search-setup",
        )


def _get_wiki_dir(org_root):
    """Return wiki directory path, exit if not found."""
    wiki_dir = os.path.join(org_root, WIKI_REL)
    if not os.path.isdir(wiki_dir):
        json_error(
            f"Wiki directory not found: {wiki_dir}",
            hint="Run /jarfis:org-init first",
        )
    return wiki_dir


def _estimate_tokens(text):
    """Rough token estimate: len / 4 for mixed Korean/English."""
    return len(text) // 4


def _strip_frontmatter(content):
    """Remove YAML frontmatter from markdown content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content


def _chunk_file(file_path, content):
    """Split a markdown file into chunks for embedding.

    Strategy:
    - If file <= CHUNK_TOKEN_THRESHOLD tokens: single chunk (whole file)
    - If file > threshold: split by H2 (##) sections, prefix each with file path + heading
    """
    clean = _strip_frontmatter(content)
    if not clean:
        return []

    rel_path = file_path  # already relative when passed in

    if _estimate_tokens(clean) <= CHUNK_TOKEN_THRESHOLD:
        return [{"file": rel_path, "section": None, "text": clean}]

    # Split by H2
    chunks = []
    sections = re.split(r"(?=^## )", clean, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract heading
        heading_match = re.match(r"^## (.+)$", section, re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else None

        # Prefix with file context for better embedding
        prefixed = f"[{rel_path}] {f'[{heading}] ' if heading else ''}{section}"
        chunks.append({"file": rel_path, "section": heading, "text": prefixed})

    return chunks if chunks else [{"file": rel_path, "section": None, "text": clean}]


def _collect_wiki_files(wiki_dir):
    """Walk wiki directory and collect all .md files with content."""
    files = []
    for root, _dirs, filenames in os.walk(wiki_dir):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, wiki_dir)
            try:
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    files.append(
                        {"rel_path": rel_path, "full_path": full_path, "content": content}
                    )
            except (OSError, UnicodeDecodeError):
                continue
    return files


def _load_model():
    """Lazy-load the sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def _check_staleness(wiki_dir, meta):
    """Check for stale files (modified after last indexing)."""
    indexed_at = meta.get("indexed_at", 0)
    stale = []
    for root, _dirs, filenames in os.walk(wiki_dir):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            full_path = os.path.join(root, fname)
            try:
                mtime = os.path.getmtime(full_path)
                if mtime > indexed_at:
                    stale.append(os.path.relpath(full_path, wiki_dir))
            except OSError:
                continue
    return stale


# --- Subcommands ---


def cmd_index(org_root):
    """Build embedding index for all wiki .md files."""
    _ensure_dependencies()
    import numpy as np

    wiki_dir = _get_wiki_dir(org_root)
    wiki_files = _collect_wiki_files(wiki_dir)

    if not wiki_files:
        json_error("No .md files found in wiki directory")

    # Chunk all files
    all_chunks = []
    for wf in wiki_files:
        chunks = _chunk_file(wf["rel_path"], wf["content"])
        all_chunks.extend(chunks)

    if not all_chunks:
        json_error("No content to index after chunking")

    # Embed
    model = _load_model()
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    # Save vectors
    vectors_path = os.path.join(wiki_dir, VECTORS_FILE)
    np.savez_compressed(vectors_path, embeddings=embeddings)

    # Save metadata
    meta = {
        "indexed_at": time.time(),
        "model": MODEL_NAME,
        "total_files": len(wiki_files),
        "total_chunks": len(all_chunks),
        "chunks": [
            {"file": c["file"], "section": c["section"], "preview": c["text"][:100]}
            for c in all_chunks
        ],
    }
    meta_path = os.path.join(wiki_dir, META_FILE)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    json_output(
        {
            "status": "indexed",
            "files": len(wiki_files),
            "chunks": len(all_chunks),
            "vectors_path": vectors_path,
        }
    )


def cmd_search(org_root, query, top_k=DEFAULT_TOP_K):
    """Search wiki using semantic similarity."""
    _ensure_dependencies()
    import numpy as np

    wiki_dir = _get_wiki_dir(org_root)

    # Load index
    vectors_path = os.path.join(wiki_dir, VECTORS_FILE)
    meta_path = os.path.join(wiki_dir, META_FILE)

    if not os.path.isfile(vectors_path) or not os.path.isfile(meta_path):
        json_error(
            "Wiki index not found. Run: jarfis_cli.py wiki index <org_root>",
            hint="jarfis_cli.py wiki index",
        )

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    # Staleness warning
    stale = _check_staleness(wiki_dir, meta)
    stale_warning = None
    if stale:
        stale_warning = f"{len(stale)} file(s) modified since last indexing: {', '.join(stale[:5])}"

    # Load vectors
    data = np.load(vectors_path)
    embeddings = data["embeddings"]

    # Embed query
    model = _load_model()
    query_vec = model.encode([query], normalize_embeddings=True)

    # Cosine similarity (vectors are already normalized)
    scores = np.dot(embeddings, query_vec.T).flatten()

    # Top-k
    top_indices = np.argsort(scores)[::-1][:top_k]

    chunks_meta = meta.get("chunks", [])
    results = []
    seen_files = set()

    for idx in top_indices:
        if idx >= len(chunks_meta):
            continue
        score = float(scores[idx])
        if score < SCORE_THRESHOLD:
            continue
        chunk = chunks_meta[idx]
        file_path = chunk["file"]

        # Deduplicate by file (keep highest score per file)
        if file_path in seen_files:
            continue
        seen_files.add(file_path)

        # Read full file for preview
        full_path = os.path.join(wiki_dir, file_path)
        preview = chunk.get("preview", "")
        if os.path.isfile(full_path):
            try:
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()
                preview = _strip_frontmatter(content)[:200]
            except (OSError, UnicodeDecodeError):
                pass

        results.append(
            {
                "file_path": file_path,
                "section": chunk.get("section"),
                "score": round(score, 4),
                "preview": preview,
            }
        )

    output = {"query": query, "results": results, "total_indexed": meta.get("total_chunks", 0)}
    if stale_warning:
        output["stale_warning"] = stale_warning
    json_output(output)


def cmd_status(org_root):
    """Show index status."""
    wiki_dir = _get_wiki_dir(org_root)
    meta_path = os.path.join(wiki_dir, META_FILE)

    if not os.path.isfile(meta_path):
        json_output({"indexed": False, "hint": "Run: jarfis_cli.py wiki index <org_root>"})
        return

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    stale = _check_staleness(wiki_dir, meta)

    from datetime import datetime

    indexed_at = meta.get("indexed_at", 0)
    json_output(
        {
            "indexed": True,
            "model": meta.get("model", "unknown"),
            "total_files": meta.get("total_files", 0),
            "total_chunks": meta.get("total_chunks", 0),
            "indexed_at": datetime.fromtimestamp(indexed_at).isoformat() if indexed_at else None,
            "stale_files": len(stale),
            "stale_list": stale[:10] if stale else [],
        }
    )


# --- Main ---


def main(args):
    if not args:
        json_error("Usage: jarfis_cli.py wiki <index|search|status> <org_root> [args...]")

    subcmd = args[0]

    if subcmd == "index":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py wiki index <org_root>")
        cmd_index(os.path.abspath(args[1]))

    elif subcmd == "search":
        if len(args) < 3:
            json_error("Usage: jarfis_cli.py wiki search <org_root> <query> [--top-k N]")
        org_root = os.path.abspath(args[1])
        query = args[2]
        top_k = DEFAULT_TOP_K
        if "--top-k" in args:
            try:
                top_k = int(args[args.index("--top-k") + 1])
            except (IndexError, ValueError):
                pass
        cmd_search(org_root, query, top_k)

    elif subcmd == "status":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py wiki status <org_root>")
        cmd_status(os.path.abspath(args[1]))

    else:
        json_error(f"Unknown wiki subcommand: {subcmd}. Available: index, search, status")
