"""JARFIS Semantic Search — sentence-transformers bge-m3 based.

Supports wiki, meetings, and works directories with independent indices.

Legacy subcommands (via jarfis_cli.py wiki):
    index <org_root>                       Build wiki index
    search <org_root> <query> [--top-k N]  Search wiki
    status <org_root>                      Wiki index status

New subcommands (via jarfis_cli.py search):
    search {all|meetings|works|wiki} <query> [--top-k N] [--pretty]
    index {all|meetings|works|wiki} [--org-root PATH]
    status [--org-root PATH]
"""

import json
import os
import re
import sys
import time

from .utils import find_org_root, get_org_dir, json_error, json_output

# --- Constants ---
WIKI_REL = os.path.join(".jarfis", "wiki")
VECTORS_FILE = ".vectors.npz"
META_FILE = ".vectors-meta.json"
DEFAULT_TOP_K = 5
CHUNK_TOKEN_THRESHOLD = 500  # approx chars * 0.25; we use char count / 4 as proxy
SCORE_THRESHOLD = 0.5
MODEL_NAME = "BAAI/bge-m3"

VALID_SCOPES = ("all", "meetings", "works", "wiki")

VENV_DIR = os.path.join(os.path.expanduser("~"), ".claude", ".jarfis-venv")


# --- Utilities ---


def _ensure_dependencies():
    """Check that sentence-transformers and numpy are available."""
    try:
        import numpy  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        json_error(
            "sentence-transformers is not installed. "
            "Run /jarfis:search-setup to install.",
            hint="/jarfis:search-setup",
        )


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


def _collect_md_files(target_dir):
    """Walk directory and collect all .md files with content.

    Skips hidden files (starting with .) and empty files.
    """
    if not os.path.isdir(target_dir):
        return []
    files = []
    for root, _dirs, filenames in os.walk(target_dir):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            if fname.startswith("."):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, target_dir)
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


# Backward compatibility alias
_collect_wiki_files = _collect_md_files


def _load_model():
    """Lazy-load the sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def _check_staleness(target_dir, meta):
    """Check for stale files (modified after last indexing)."""
    indexed_at = meta.get("indexed_at", 0)
    stale = []
    for root, _dirs, filenames in os.walk(target_dir):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            if fname.startswith("."):
                continue
            full_path = os.path.join(root, fname)
            try:
                mtime = os.path.getmtime(full_path)
                if mtime > indexed_at:
                    stale.append(os.path.relpath(full_path, target_dir))
            except OSError:
                continue
    return stale


# --- Path Resolution ---


def resolve_search_dirs(org_root=None, org_dir=None):
    """Resolve search directories for each scope.

    Args:
        org_root: Organization root (project root with .jarfis/). For wiki.
        org_dir: Organization workspace dir (.personal/orgs/{org}/). For meetings/works.

    Returns:
        dict of {scope: target_dir} for existing directories only.
    """
    dirs = {}

    if org_root:
        wiki_dir = os.path.join(org_root, WIKI_REL)
        if os.path.isdir(wiki_dir):
            dirs["wiki"] = wiki_dir

    if org_dir:
        meetings_dir = os.path.join(org_dir, "meetings")
        if os.path.isdir(meetings_dir):
            dirs["meetings"] = meetings_dir

        works_dir = os.path.join(org_dir, "works")
        if os.path.isdir(works_dir):
            dirs["works"] = works_dir

    return dirs


def _resolve_dirs_from_cwd():
    """Resolve org_root and org_dir from current working directory."""
    cwd = os.getcwd()
    org_root = find_org_root(cwd)
    org_dir = get_org_dir(cwd)
    return org_root, org_dir


# --- Core Operations ---


def cmd_index(target_dir):
    """Build embedding index for all .md files in target_dir."""
    _ensure_dependencies()
    import numpy as np

    if not os.path.isdir(target_dir):
        json_error(f"Directory not found: {target_dir}")

    md_files = _collect_md_files(target_dir)

    if not md_files:
        json_error(f"No .md files found in {target_dir}")

    # Chunk all files
    all_chunks = []
    for mf in md_files:
        chunks = _chunk_file(mf["rel_path"], mf["content"])
        all_chunks.extend(chunks)

    if not all_chunks:
        json_error("No content to index after chunking")

    # Embed
    model = _load_model()
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, batch_size=2, show_progress_bar=True, normalize_embeddings=True)

    # Save vectors
    vectors_path = os.path.join(target_dir, VECTORS_FILE)
    np.savez_compressed(vectors_path, embeddings=embeddings)

    # Save metadata
    meta = {
        "indexed_at": time.time(),
        "model": MODEL_NAME,
        "total_files": len(md_files),
        "total_chunks": len(all_chunks),
        "chunks": [
            {"file": c["file"], "section": c["section"], "preview": c["text"][:100]}
            for c in all_chunks
        ],
    }
    meta_path = os.path.join(target_dir, META_FILE)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    json_output(
        {
            "status": "indexed",
            "directory": target_dir,
            "files": len(md_files),
            "chunks": len(all_chunks),
            "vectors_path": vectors_path,
        }
    )


def _search_index(target_dir, query, top_k=DEFAULT_TOP_K, source_label=None):
    """Search a single index directory. Returns (results_list, stale_warning).

    Does NOT print output — callers handle output.
    Requires _ensure_dependencies() and model loading to be done by caller.
    """
    import numpy as np

    vectors_path = os.path.join(target_dir, VECTORS_FILE)
    meta_path = os.path.join(target_dir, META_FILE)

    if not os.path.isfile(vectors_path) or not os.path.isfile(meta_path):
        return [], None

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    # Staleness warning
    stale = _check_staleness(target_dir, meta)
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

    # Top-k per this index
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

        # Deduplicate by file within this index
        if file_path in seen_files:
            continue
        seen_files.add(file_path)

        # Read full file for preview
        full_path = os.path.join(target_dir, file_path)
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
                "source": source_label,
                "file_path": file_path,
                "section": chunk.get("section"),
                "score": round(score, 4),
                "preview": preview,
            }
        )

    return results, stale_warning


def _merge_results(all_results, top_k=DEFAULT_TOP_K):
    """Merge results from multiple indices, deduplicate by (source, file_path), sort by score.

    Deduplication: within same source, keep only highest-scoring entry per file.
    Across sources, same filename is allowed (e.g., summary.md in meetings vs wiki).
    """
    # Deduplicate by (source, file_path) — keep highest score
    best = {}
    for r in all_results:
        key = (r.get("source"), r["file_path"])
        if key not in best or r["score"] > best[key]["score"]:
            best[key] = r

    merged = sorted(best.values(), key=lambda r: r["score"], reverse=True)
    return merged[:top_k]


def cmd_search_single(target_dir, query, top_k=DEFAULT_TOP_K, source_label=None, pretty=False):
    """Search a single directory and output results."""
    _ensure_dependencies()

    results, stale_warning = _search_index(target_dir, query, top_k, source_label)

    output = {
        "query": query,
        "results": results,
        "total_results": len(results),
    }
    if stale_warning:
        output["stale_warning"] = stale_warning

    _output(output, pretty)


def cmd_search_multi(dirs_with_labels, query, top_k=DEFAULT_TOP_K, pretty=False):
    """Search multiple directories, interleave results by score, output combined."""
    _ensure_dependencies()

    all_results = []
    warnings = []

    for target_dir, label in dirs_with_labels:
        if not os.path.isdir(target_dir):
            continue
        results, stale = _search_index(target_dir, query, top_k, label)
        all_results.extend(results)
        if stale:
            warnings.append(f"[{label}] {stale}")

    merged = _merge_results(all_results, top_k)

    output = {
        "query": query,
        "results": merged,
        "total_results": len(merged),
    }
    if warnings:
        output["stale_warning"] = "; ".join(warnings)

    _output(output, pretty)


def cmd_status_dir(target_dir, label=None):
    """Show index status for a directory. Returns status dict (does not print)."""
    meta_path = os.path.join(target_dir, META_FILE)

    if not os.path.isfile(meta_path):
        return {"source": label, "indexed": False, "directory": target_dir}

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    stale = _check_staleness(target_dir, meta)

    from datetime import datetime

    indexed_at = meta.get("indexed_at", 0)
    return {
        "source": label,
        "indexed": True,
        "directory": target_dir,
        "model": meta.get("model", "unknown"),
        "total_files": meta.get("total_files", 0),
        "total_chunks": meta.get("total_chunks", 0),
        "indexed_at": datetime.fromtimestamp(indexed_at).isoformat() if indexed_at else None,
        "stale_files": len(stale),
        "stale_list": stale[:10] if stale else [],
    }


# --- Output Formatting ---


def format_pretty(data):
    """Format search results for human reading."""
    lines = []
    query = data.get("query", "")
    results = data.get("results", [])
    stale = data.get("stale_warning")

    lines.append(f"Search: \"{query}\"")
    lines.append("")

    if stale:
        lines.append(f"  Warning: {stale}")
        lines.append("")

    if not results:
        lines.append("  결과 없음")
    else:
        for i, r in enumerate(results, 1):
            source = r.get("source", "?")
            fpath = r.get("file_path", "")
            section = r.get("section", "")
            score = r.get("score", 0)
            preview = r.get("preview", "")[:80]

            lines.append(f"  {i}. [{source}] {fpath}")
            sec_str = f"  section: {section}" if section else ""
            lines.append(f"     score: {score}{sec_str}")
            if preview:
                lines.append(f"     {preview}")
            lines.append("")

    return "\n".join(lines)


def _output(data, pretty=False):
    """Print output in JSON or pretty format."""
    if pretty:
        print(format_pretty(data))
    else:
        json_output(data)


# --- CLI Entry Points ---


def _parse_flags(args):
    """Parse --top-k N and --pretty from args. Returns (top_k, pretty, remaining_args)."""
    top_k = DEFAULT_TOP_K
    pretty = False
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == "--top-k" and i + 1 < len(args):
            try:
                top_k = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--pretty":
            pretty = True
            i += 1
        elif args[i] == "--org-root" and i + 1 < len(args):
            # handled by caller
            remaining.append(args[i])
            remaining.append(args[i + 1])
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return top_k, pretty, remaining


def search_main(args):
    """Entry point for `jarfis_cli.py search` command.

    Subcommands:
        {all|meetings|works|wiki} <query> [--top-k N] [--pretty]
        index {all|meetings|works|wiki} [--org-root PATH]
        status [--org-root PATH]
    """
    if not args:
        json_error(
            "Usage: jarfis_cli.py search {all|meetings|works|wiki} <query> [--top-k N] [--pretty]\n"
            "       jarfis_cli.py search index {all|meetings|works|wiki} [--org-root PATH]\n"
            "       jarfis_cli.py search status [--org-root PATH]"
        )

    subcmd = args[0]

    # --- search index ---
    if subcmd == "index":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py search index {all|meetings|works|wiki} [--org-root PATH]")
        scope = args[1]
        if scope not in VALID_SCOPES:
            json_error(f"Unknown scope: {scope}. Available: {', '.join(VALID_SCOPES)}")

        # Parse --org-root
        org_root_arg = None
        if "--org-root" in args:
            idx = args.index("--org-root")
            if idx + 1 < len(args):
                org_root_arg = os.path.abspath(args[idx + 1])

        if org_root_arg:
            org_root = org_root_arg
            org_dir = get_org_dir(org_root_arg)
        else:
            org_root, org_dir = _resolve_dirs_from_cwd()

        dirs = resolve_search_dirs(org_root=org_root, org_dir=org_dir)
        scopes = [scope] if scope != "all" else ["wiki", "meetings", "works"]

        results = []
        for s in scopes:
            if s not in dirs:
                results.append({"scope": s, "status": "skipped", "reason": "directory not found"})
                continue
            try:
                cmd_index(dirs[s])
                results.append({"scope": s, "status": "indexed"})
            except SystemExit:
                results.append({"scope": s, "status": "error"})

        json_output({"action": "index", "results": results})
        return

    # --- search status ---
    if subcmd == "status":
        org_root_arg = None
        if "--org-root" in args:
            idx = args.index("--org-root")
            if idx + 1 < len(args):
                org_root_arg = os.path.abspath(args[idx + 1])

        if org_root_arg:
            org_root = org_root_arg
            org_dir = get_org_dir(org_root_arg)
        else:
            org_root, org_dir = _resolve_dirs_from_cwd()

        dirs = resolve_search_dirs(org_root=org_root, org_dir=org_dir)
        statuses = []
        for scope, target_dir in dirs.items():
            statuses.append(cmd_status_dir(target_dir, label=scope))

        pretty = "--pretty" in args
        output = {"statuses": statuses}
        _output(output, pretty)
        return

    # --- search {scope} <query> ---
    if subcmd not in VALID_SCOPES:
        json_error(f"Unknown subcommand: {subcmd}. Available: {', '.join(VALID_SCOPES)}, index, status")

    scope = subcmd
    top_k, pretty, remaining = _parse_flags(args[1:])

    if not remaining:
        json_error(f"Usage: jarfis_cli.py search {scope} <query> [--top-k N] [--pretty]")

    query = remaining[0]

    org_root, org_dir = _resolve_dirs_from_cwd()
    dirs = resolve_search_dirs(org_root=org_root, org_dir=org_dir)

    if scope == "all":
        dirs_with_labels = [(d, label) for label, d in dirs.items()]
        cmd_search_multi(dirs_with_labels, query, top_k, pretty)
    else:
        if scope not in dirs:
            json_error(
                f"{scope} directory not found. "
                f"Available: {', '.join(dirs.keys()) if dirs else 'none (run /jarfis:org-init)'}",
            )
        cmd_search_single(dirs[scope], query, top_k, scope, pretty)


# --- Legacy Entry Point (jarfis_cli.py wiki) ---


def main(args):
    """Legacy entry point for `jarfis_cli.py wiki` command.

    Routes to new generic functions for backward compatibility.
    """
    if not args:
        json_error("Usage: jarfis_cli.py wiki <index|search|status> <org_root> [args...]")

    subcmd = args[0]

    if subcmd == "index":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py wiki index <org_root>")
        org_root = os.path.abspath(args[1])
        wiki_dir = os.path.join(org_root, WIKI_REL)
        if not os.path.isdir(wiki_dir):
            json_error(
                f"Wiki directory not found: {wiki_dir}",
                hint="Run /jarfis:org-init first",
            )
        cmd_index(wiki_dir)

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
        wiki_dir = os.path.join(org_root, WIKI_REL)
        if not os.path.isdir(wiki_dir):
            json_error(
                f"Wiki directory not found: {wiki_dir}",
                hint="Run /jarfis:org-init first",
            )
        # Use legacy output format (no source field) for backward compat
        _ensure_dependencies()
        results, stale_warning = _search_index(wiki_dir, query, top_k, source_label="wiki")
        # Strip source field for legacy compat
        for r in results:
            r.pop("source", None)
        output = {"query": query, "results": results, "total_indexed": 0}
        if stale_warning:
            output["stale_warning"] = stale_warning
        json_output(output)

    elif subcmd == "status":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py wiki status <org_root>")
        org_root = os.path.abspath(args[1])
        wiki_dir = os.path.join(org_root, WIKI_REL)
        if not os.path.isdir(wiki_dir):
            json_error(
                f"Wiki directory not found: {wiki_dir}",
                hint="Run /jarfis:org-init first",
            )
        status = cmd_status_dir(wiki_dir)
        # Legacy format: flatten (no source/directory fields)
        status.pop("source", None)
        status.pop("directory", None)
        json_output(status)

    else:
        json_error(f"Unknown wiki subcommand: {subcmd}. Available: index, search, status")
