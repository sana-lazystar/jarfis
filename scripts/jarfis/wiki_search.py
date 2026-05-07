"""JARFIS Semantic Search — sentence-transformers bge-m3 based.

Supports wiki, meetings, and works directories with independent indices.

Legacy subcommands (via jarfis_cli.py wiki):
    index <org_root>                        Build wiki index
    search <org_root> <query> [--top-k N]   Search wiki
    status <org_root>                       Wiki index status
    rebuild-index <org_root>                Regenerate INDEX.md from section _index.md files (M6)

New subcommands (via jarfis_cli.py search):
    search {all|meetings|works|wiki|jarfis} <query> [--top-k N] [--pretty]
    index {all|meetings|works|wiki|jarfis} [--org-root PATH]
    status [--org-root PATH] [jarfis]
"""

import json
import os
import re
import sys
import time

from .utils import find_org_root, get_org_dir, json_error, json_output

# --- Constants ---
WIKI_REL = os.path.join(".jarfis-org", "wiki")
VECTORS_FILE = ".vectors.npz"
META_FILE = ".vectors-meta.json"
DEFAULT_TOP_K = 5
CHUNK_TOKEN_THRESHOLD = 500  # approx chars * 0.25; we use char count / 4 as proxy
SCORE_THRESHOLD = 0.5
MODEL_NAME = "BAAI/bge-m3"

VALID_SCOPES = ("all", "meetings", "works", "wiki", "jarfis")

# --- JARFIS self-knowledge scope (ADR-0002 — M3) ---
# Index location: {JARFIS_SOURCE}/.personal/.jarfis-index/  (org-agnostic, global)
JARFIS_INDEX_DIR_NAME = ".jarfis-index"

# Source roots scanned for jarfis-system index. Paths relative to ~/.claude/.
# (commands/jarfis/, agents/jarfis/, scripts/jarfis/, hooks/, plus a few config files)
JARFIS_INCLUDE_REL = (
    "commands/jarfis",
    "agents/jarfis",
    "scripts/jarfis",
    "scripts/tests",
    "hooks",
)
JARFIS_INCLUDE_FILES_AT_CLAUDE_ROOT = (
    "scripts/jarfis_cli.py",
    ".jarfis-source",
    ".jarfis-version",
    ".jarfis-personal-dir",
    ".jarfis-locale",
)
JARFIS_FILE_EXTS = (".md", ".py", ".sh", ".yaml", ".yml")
JARFIS_EXCLUDE_DIRS = (
    "__pycache__",
    ".distill-backup",
    ".implement-backup",
    ".compact-backups",
    ".jarfis-venv",
    JARFIS_INDEX_DIR_NAME,
)
MEMORY_THRESHOLD_GB = float(os.environ.get("JARFIS_MEMORY_THRESHOLD_GB", "4.0"))

VENV_DIR = os.path.join(os.path.expanduser("~"), ".claude", ".jarfis-venv")


# --- Utilities ---


def _check_available_memory_gb():
    """Check available memory in GB. Returns float or None if unsupported.

    macOS: parses vm_stat (free + speculative + inactive pages).
    Linux: reads /proc/meminfo MemAvailable.
    Other/failure: returns None (caller should treat as pass-through).
    """
    import platform
    import subprocess

    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return None
            output = result.stdout
            page_size = 16384  # ARM Mac default
            # Try to parse page size from first line
            first_line = output.split("\n")[0]
            if "page size of" in first_line:
                try:
                    page_size = int(first_line.split("page size of")[1].strip().rstrip(".").split()[0])
                except (ValueError, IndexError):
                    pass
            free = spec = inactive = 0
            for line in output.split("\n"):
                if "Pages free:" in line:
                    free = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages speculative:" in line:
                    spec = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages inactive:" in line:
                    inactive = int(line.split(":")[1].strip().rstrip("."))
            total_bytes = (free + spec + inactive) * page_size
            return total_bytes / (1024 ** 3)
        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
            return None
        else:
            return None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def _get_mps_allocated_gb():
    """Return MPS (Metal) driver-allocated memory in GB, or 0.0 if unavailable.

    On Apple Silicon, MPS allocations consume unified memory but are invisible
    to vm_stat. This captures GPU memory pressure from other processes.
    """
    try:
        import torch

        if hasattr(torch, "mps") and hasattr(torch.mps, "driver_allocated_memory"):
            return torch.mps.driver_allocated_memory() / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def _ensure_dependencies():
    """Check that sentence-transformers, numpy are available and memory is sufficient."""
    # Memory check first — prevent OOM/kernel panic
    threshold = float(os.environ.get("JARFIS_MEMORY_THRESHOLD_GB", str(MEMORY_THRESHOLD_GB)))
    available = _check_available_memory_gb()
    if available is not None:
        # Deduct MPS GPU memory (invisible to vm_stat on Apple Silicon)
        mps_gb = _get_mps_allocated_gb()
        effective = available - mps_gb
        if effective < threshold:
            mps_note = f" (MPS GPU: {mps_gb:.1f}GB in use)" if mps_gb > 0.1 else ""
            json_error(
                f"Insufficient memory: available {effective:.1f}GB{mps_note} / minimum {threshold:.0f}GB required. "
                "Cannot load SentenceTransformer. "
                "Close other apps or adjust threshold via JARFIS_MEMORY_THRESHOLD_GB env variable.",
                hint="memory_insufficient",
            )

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
    """Lazy-load the sentence-transformers model.

    Forces CPU to avoid MPS (Metal) unified-memory exhaustion on Apple Silicon.
    MPS driver allocates ~3.8GB that persists even after empty_cache(), causing
    macOS kernel panic under repeated invocations.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, device="cpu")


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
        org_root: Organization root (project root with .jarfis-org/). For wiki.
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
        lines.append("  No results")
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
            "Usage: jarfis_cli.py search {all|meetings|works|wiki|jarfis} <query> [--top-k N] [--pretty]\n"
            "       jarfis_cli.py search index {all|meetings|works|wiki|jarfis} [--org-root PATH]\n"
            "       jarfis_cli.py search status [--org-root PATH] [jarfis]"
        )

    subcmd = args[0]

    # --- search index ---
    if subcmd == "index":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py search index {all|meetings|works|wiki|jarfis} [--org-root PATH]")
        scope = args[1]
        if scope not in VALID_SCOPES:
            json_error(f"Unknown scope: {scope}. Available: {', '.join(VALID_SCOPES)}")

        # JARFIS self-knowledge — org-agnostic, separate path
        if scope == "jarfis":
            incremental = "--incremental" in args
            files_filter = None
            if "--files" in args:
                idx = args.index("--files")
                if idx + 1 < len(args):
                    files_filter = [
                        p.strip() for p in args[idx + 1].split(",") if p.strip()
                    ]
            cmd_index_jarfis(incremental=incremental, files_filter=files_filter)
            return

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
        # Check if user specifically wants the jarfis-system index status
        if "jarfis" in args:
            statuses = [cmd_status_jarfis()]
            pretty = "--pretty" in args
            _output({"statuses": statuses}, pretty)
            return

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

    # JARFIS self-knowledge scope — org-agnostic, separate index
    if scope == "jarfis":
        cmd_search_jarfis(query, top_k, pretty)
        return

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


# --- JARFIS self-knowledge scope (ADR-0002 — M3) ---


def get_jarfis_index_dir():
    """Return {JARFIS_SOURCE}/.personal/.jarfis-index/."""
    from .utils import get_personal_dir
    return os.path.join(get_personal_dir(), JARFIS_INDEX_DIR_NAME)


def _is_excluded_jarfis_path(rel_path):
    """True if any path component matches JARFIS_EXCLUDE_DIRS."""
    parts = rel_path.split(os.sep)
    return any(p in JARFIS_EXCLUDE_DIRS for p in parts)


def _collect_jarfis_files(claude_dir=None):
    """Walk ~/.claude/ JARFIS roots and collect indexable files.

    Returns list of {rel_path, full_path, content, ext} dicts.
    `rel_path` is relative to claude_dir (e.g. "commands/jarfis/sys-implement.md").
    """
    from .utils import get_claude_dir
    if claude_dir is None:
        claude_dir = get_claude_dir()
    files = []

    # Walk include directories
    for include_rel in JARFIS_INCLUDE_REL:
        root = os.path.join(claude_dir, include_rel)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded subdirs in-place so os.walk skips them
            dirnames[:] = [d for d in dirnames if d not in JARFIS_EXCLUDE_DIRS]
            for fname in filenames:
                if fname.startswith("."):
                    # Skip dotfiles inside walk targets (e.g. .DS_Store)
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext not in JARFIS_FILE_EXTS:
                    continue
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, claude_dir)
                if _is_excluded_jarfis_path(rel_path):
                    continue
                try:
                    with open(full_path, encoding="utf-8") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                if not content.strip():
                    continue
                files.append({
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "content": content,
                    "ext": ext,
                })

    # Top-level individual files (jarfis_cli.py + .jarfis-* configs)
    for rel in JARFIS_INCLUDE_FILES_AT_CLAUDE_ROOT:
        full_path = os.path.join(claude_dir, rel)
        if not os.path.isfile(full_path):
            continue
        ext = os.path.splitext(rel)[1].lower() or ".txt"
        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if not content.strip():
            continue
        files.append({
            "rel_path": rel,
            "full_path": full_path,
            "content": content,
            "ext": ext,
        })

    return files


def _chunk_python_file(rel_path, content):
    """Split a Python file into function/class units.

    Strategy: for files <= CHUNK_TOKEN_THRESHOLD tokens, single chunk.
    Otherwise split on top-level `def `, `async def `, or `class `.
    """
    if _estimate_tokens(content) <= CHUNK_TOKEN_THRESHOLD:
        return [{"file": rel_path, "section": None, "text": f"[{rel_path}]\n{content}"}]
    # Split on top-level definitions (line starts with def/async def/class)
    parts = re.split(r"(?m)^(?=(?:async\s+def\s+|def\s+|class\s+))", content)
    chunks = []
    for part in parts:
        part = part.rstrip()
        if not part:
            continue
        # Extract first def/class name as section heading
        head = re.match(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", part)
        section = head.group(1) if head else None
        prefixed = f"[{rel_path}] {f'[{section}] ' if section else ''}{part}"
        chunks.append({"file": rel_path, "section": section, "text": prefixed})
    return chunks if chunks else [{"file": rel_path, "section": None, "text": f"[{rel_path}]\n{content}"}]


def _chunk_jarfis_file(rel_path, content, ext):
    """Dispatch chunking by file extension."""
    if ext == ".md":
        # Reuse markdown chunker (## heading split)
        return _chunk_file(rel_path, content)
    if ext == ".py":
        return _chunk_python_file(rel_path, content)
    # .sh, .yaml, .yml — small, single chunk
    if _estimate_tokens(content) <= CHUNK_TOKEN_THRESHOLD * 2:
        return [{"file": rel_path, "section": None, "text": f"[{rel_path}]\n{content}"}]
    # Long shell/yaml — split by blank-line groups (rare)
    blocks = re.split(r"\n\s*\n", content)
    chunks = []
    for i, blk in enumerate(blocks):
        blk = blk.strip()
        if not blk:
            continue
        chunks.append({
            "file": rel_path,
            "section": f"block-{i}",
            "text": f"[{rel_path}] [block-{i}]\n{blk}",
        })
    return chunks if chunks else [{"file": rel_path, "section": None, "text": f"[{rel_path}]\n{content}"}]


def _filter_chunks_for_incremental(meta: dict, embeddings, removed_files):
    """Return (filtered_meta_chunks, filtered_embeddings) excluding chunks
    whose `file` is in removed_files. Preserves index ↔ embedding alignment.
    """
    import numpy as np
    chunks_meta = meta.get("chunks", [])
    keep_indices = [
        i for i, c in enumerate(chunks_meta)
        if c.get("file") not in removed_files
    ]
    new_meta_chunks = [chunks_meta[i] for i in keep_indices]
    if len(keep_indices) == len(chunks_meta):
        return new_meta_chunks, embeddings  # nothing removed, fast path
    new_embeddings = embeddings[keep_indices] if len(keep_indices) > 0 else embeddings[:0]
    return new_meta_chunks, new_embeddings


def cmd_index_jarfis(incremental: bool = False, files_filter=None):
    """Build embedding index for the JARFIS self-knowledge corpus.

    Args:
        incremental: when True, re-encode only `files_filter` and merge with
                     existing index (existing chunks for those files are removed first).
                     When False (default), full rebuild from scratch.
        files_filter: list of source_relpath strings (relative to ~/.claude/) to
                      include in the incremental update. Required when incremental=True.

    Output (overwrites in place):
        {JARFIS_SOURCE}/.personal/.jarfis-index/.vectors.npz
        {JARFIS_SOURCE}/.personal/.jarfis-index/.vectors-meta.json
    """
    _ensure_dependencies()
    import numpy as np

    if incremental:
        if not files_filter:
            json_error(
                "Incremental update requires --files <comma-separated paths>"
            )
        # Filter existing files corpus to only the files_filter set
        all_files = _collect_jarfis_files()
        target_set = set(files_filter)
        files = [f for f in all_files if f["rel_path"] in target_set]
        # Some files may have been deleted — those won't appear in all_files
        # but we still need to remove their chunks from the existing index.
        deleted = [p for p in files_filter if p not in {f["rel_path"] for f in files}]
    else:
        files = _collect_jarfis_files()
        deleted = []

    if not files and not (incremental and deleted):
        json_error("No JARFIS files collected for indexing")

    new_chunks = []
    for f in files:
        chunks = _chunk_jarfis_file(f["rel_path"], f["content"], f["ext"])
        for c in chunks:
            c["ext"] = f["ext"]
            new_chunks.append(c)

    if not new_chunks and not (incremental and deleted):
        json_error("No content to index after chunking")

    index_dir = get_jarfis_index_dir()
    os.makedirs(index_dir, exist_ok=True)
    vectors_path = os.path.join(index_dir, VECTORS_FILE)
    meta_path = os.path.join(index_dir, META_FILE)

    # Encode new chunks (skip if no new content — pure deletion case)
    if new_chunks:
        model = _load_model()
        texts = [c["text"] for c in new_chunks]
        new_embeddings = model.encode(
            texts, batch_size=2, show_progress_bar=True, normalize_embeddings=True
        )
    else:
        new_embeddings = None

    if incremental and os.path.isfile(vectors_path) and os.path.isfile(meta_path):
        # Merge with existing index
        existing = np.load(vectors_path)
        existing_embeddings = existing["embeddings"]
        with open(meta_path, encoding="utf-8") as fh:
            existing_meta = json.load(fh)

        # Remove all chunks whose `file` matches files_filter (both updated and deleted)
        kept_chunks, kept_embeddings = _filter_chunks_for_incremental(
            existing_meta, existing_embeddings, set(files_filter)
        )

        if new_embeddings is not None and len(new_chunks) > 0:
            all_embeddings = np.vstack([kept_embeddings, new_embeddings])
            new_chunks_meta = [
                {
                    "file": c["file"],
                    "section": c.get("section"),
                    "ext": c.get("ext"),
                    "preview": c["text"][:120],
                }
                for c in new_chunks
            ]
            chunks_meta = kept_chunks + new_chunks_meta
        else:
            all_embeddings = kept_embeddings
            chunks_meta = kept_chunks

        # Recount total_files: collect_jarfis_files length on full corpus
        total_files = len(_collect_jarfis_files())
        meta = {
            "indexed_at": time.time(),
            "model": MODEL_NAME,
            "scope": "jarfis",
            "jarfis_version": existing_meta.get("jarfis_version", "unknown"),
            "total_files": total_files,
            "total_chunks": len(chunks_meta),
            "chunks": chunks_meta,
        }
        chunks_added = len(new_chunks)
        chunks_removed = len(existing_meta.get("chunks", [])) - len(kept_chunks)
    else:
        # Full rebuild
        all_embeddings = new_embeddings
        chunks_meta = [
            {
                "file": c["file"],
                "section": c.get("section"),
                "ext": c.get("ext"),
                "preview": c["text"][:120],
            }
            for c in new_chunks
        ]
        # JARFIS version for metadata
        from .utils import get_claude_dir
        version_file = os.path.join(get_claude_dir(), ".jarfis-version")
        jarfis_version = "unknown"
        if os.path.isfile(version_file):
            try:
                with open(version_file) as fh:
                    jarfis_version = fh.read().strip()
            except OSError:
                pass
        meta = {
            "indexed_at": time.time(),
            "model": MODEL_NAME,
            "scope": "jarfis",
            "jarfis_version": jarfis_version,
            "total_files": len(files),
            "total_chunks": len(chunks_meta),
            "chunks": chunks_meta,
        }
        chunks_added = len(new_chunks)
        chunks_removed = 0

    np.savez_compressed(vectors_path, embeddings=all_embeddings)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    json_output({
        "status": "indexed",
        "scope": "jarfis",
        "directory": index_dir,
        "incremental": incremental,
        "files_processed": len(files),
        "files_deleted_from_index": len(deleted) if incremental else 0,
        "chunks_added": chunks_added,
        "chunks_removed": chunks_removed,
        "total_chunks": meta["total_chunks"],
        "vectors_path": vectors_path,
    })


def _check_staleness_jarfis(meta, claude_dir=None):
    """Check for stale JARFIS files (modified after last indexing)."""
    from .utils import get_claude_dir
    if claude_dir is None:
        claude_dir = get_claude_dir()
    indexed_at = meta.get("indexed_at", 0)
    stale = []
    files = _collect_jarfis_files(claude_dir)
    for f in files:
        try:
            mtime = os.path.getmtime(f["full_path"])
            if mtime > indexed_at:
                stale.append(f["rel_path"])
        except OSError:
            continue
    return stale


def _search_jarfis_index(query, top_k=DEFAULT_TOP_K):
    """Search the JARFIS self-knowledge index. Returns (results, stale_warning)."""
    import numpy as np

    index_dir = get_jarfis_index_dir()
    vectors_path = os.path.join(index_dir, VECTORS_FILE)
    meta_path = os.path.join(index_dir, META_FILE)
    if not os.path.isfile(vectors_path) or not os.path.isfile(meta_path):
        return [], None

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    stale = _check_staleness_jarfis(meta)
    stale_warning = None
    if stale:
        stale_warning = f"{len(stale)} JARFIS file(s) modified since last indexing: {', '.join(stale[:5])}"

    data = np.load(vectors_path)
    embeddings = data["embeddings"]
    model = _load_model()
    query_vec = model.encode([query], normalize_embeddings=True)
    scores = np.dot(embeddings, query_vec.T).flatten()

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
        if file_path in seen_files:
            continue
        seen_files.add(file_path)
        results.append({
            "source": "jarfis",
            "file_path": file_path,
            "section": chunk.get("section"),
            "ext": chunk.get("ext"),
            "score": round(score, 4),
            "preview": chunk.get("preview", "")[:200],
        })
    return results, stale_warning


def cmd_search_jarfis(query, top_k=DEFAULT_TOP_K, pretty=False):
    """Run a search against the JARFIS self-knowledge index."""
    _ensure_dependencies()
    results, stale_warning = _search_jarfis_index(query, top_k)
    output = {"query": query, "scope": "jarfis", "results": results, "total_results": len(results)}
    if stale_warning:
        output["stale_warning"] = stale_warning
    _output(output, pretty)


def cmd_status_jarfis():
    """Show JARFIS index status."""
    index_dir = get_jarfis_index_dir()
    meta_path = os.path.join(index_dir, META_FILE)
    if not os.path.isfile(meta_path):
        return {"source": "jarfis", "indexed": False, "directory": index_dir}
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    stale = _check_staleness_jarfis(meta)
    from datetime import datetime as _dt
    indexed_at = meta.get("indexed_at", 0)
    return {
        "source": "jarfis",
        "indexed": True,
        "directory": index_dir,
        "model": meta.get("model", "unknown"),
        "jarfis_version": meta.get("jarfis_version", "unknown"),
        "total_files": meta.get("total_files", 0),
        "total_chunks": meta.get("total_chunks", 0),
        "indexed_at": _dt.fromtimestamp(indexed_at).isoformat() if indexed_at else None,
        "stale_files": len(stale),
        "stale_list": stale[:10] if stale else [],
    }


# --- INDEX.md rebuild (M6) ---

SECTIONS = ("PO", "DESIGN", "TA", "QA")


def _parse_section_index(section_index_path):
    """Parse the 4-column markdown table in a section _index.md.

    Expected format (per templates/wiki-section-index.md):
        | File | Summary | Projects | Updated |
        |------|---------|----------|---------|
        | file.md | summary | [proj] | 2026-04-19 |

    Returns list of dicts: [{"file", "summary", "projects", "updated"}, ...]
    Skips placeholder rows where the file cell is empty or "(none)".
    """
    if not os.path.isfile(section_index_path):
        return []
    try:
        with open(section_index_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    entries = []
    header_seen = False
    for line in content.splitlines():
        line = line.rstrip()
        if not line.startswith("|"):
            if header_seen:
                # Table ended; no more rows
                break
            continue
        # Separator row
        if re.match(r"^\|[\s\-:|]+\|[\s\-:|]*$", line):
            header_seen = True
            continue
        # First pipe-line = header
        if not header_seen:
            continue
        # Data row
        parts = [c.strip() for c in line.strip("|").split("|")]
        if len(parts) < 4:
            continue
        file_cell = parts[0]
        # Skip placeholder
        if file_cell.lower() in ("(none)", "", "-"):
            continue
        entries.append(
            {
                "file": file_cell,
                "summary": parts[1],
                "projects": parts[2],
                "updated": parts[3],
            }
        )
    return entries


def _render_index_md(sections_entries, preserved_design_marker=None):
    """Render INDEX.md content from parsed section entries.

    preserved_design_marker: if the existing INDEX.md had a DESIGN_LAST_UPDATED marker line,
    we preserve it to avoid breaking Track B's sed-based update target.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counts = {s: len(sections_entries.get(s, [])) for s in SECTIONS}
    total = sum(counts.values())

    lines = []
    lines.append("# Wiki Index")
    lines.append("")
    lines.append("## Quick Reference")
    lines.append(
        f"- Total files: {total} (PO: {counts['PO']}, DESIGN: {counts['DESIGN']}, "
        f"TA: {counts['TA']}, QA: {counts['QA']})"
    )
    lines.append(f"- Last updated: {now} (auto-rebuilt by `jarfis_cli.py wiki rebuild-index`)")
    lines.append("")
    lines.append("## Usage Guide")
    lines.append(
        "- Information priority: $DOCS_DIR > project/.jarfis-project/ > "
        ".jarfis-org/wiki/ > INDEX.md"
    )
    lines.append(
        "- Topics covered by current task: $DOCS_DIR takes priority. "
        "Topics not covered: wiki remains valid."
    )
    lines.append("")
    lines.append("## Directory Map")
    lines.append("")

    for section in SECTIONS:
        entries = sections_entries.get(section, [])
        lines.append(f"### {section}/ ({len(entries)} files)")
        if not entries:
            lines.append("Key: (none)")
        else:
            # Key = up to 3 most recently updated file names (sorted by `updated` desc)
            sorted_entries = sorted(
                entries, key=lambda e: e.get("updated", ""), reverse=True
            )
            key_files = [e["file"] for e in sorted_entries[:3]]
            lines.append(f"Key: {', '.join(key_files)}")
        lines.append(f"Details: {section}/_index.md")
        lines.append("")

    # Preserve DESIGN_LAST_UPDATED marker line (used by Track B sed update)
    if preserved_design_marker:
        lines.append(preserved_design_marker)
    else:
        lines.append("<!-- DESIGN_LAST_UPDATED --> (not yet synced)")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _extract_design_marker(index_path):
    """Extract the existing DESIGN_LAST_UPDATED marker line, if any."""
    if not os.path.isfile(index_path):
        return None
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("<!-- DESIGN_LAST_UPDATED -->"):
                    return line
    except (OSError, UnicodeDecodeError):
        pass
    return None


def cmd_rebuild_index(org_root_str):
    """Regenerate $ORG_ROOT/.jarfis-org/wiki/INDEX.md from section _index.md files."""
    org_root = os.path.abspath(org_root_str)
    wiki_dir = os.path.join(org_root, WIKI_REL)
    if not os.path.isdir(wiki_dir):
        json_error(
            f"Wiki directory not found: {wiki_dir}",
            hint="Run /jarfis:org-init first",
        )

    sections_entries = {}
    for section in SECTIONS:
        section_index = os.path.join(wiki_dir, section, "_index.md")
        sections_entries[section] = _parse_section_index(section_index)

    index_path = os.path.join(wiki_dir, "INDEX.md")
    preserved = _extract_design_marker(index_path)
    rendered = _render_index_md(sections_entries, preserved_design_marker=preserved)

    try:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(rendered)
    except OSError as e:
        json_error(f"Failed to write INDEX.md: {e}")

    json_output(
        {
            "status": "ok",
            "sections": {s: len(sections_entries[s]) for s in SECTIONS},
            "total_entries": sum(len(e) for e in sections_entries.values()),
            "index_path": index_path,
            "design_marker_preserved": preserved is not None,
        }
    )


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

    elif subcmd == "rebuild-index":
        if len(args) < 2:
            json_error("Usage: jarfis_cli.py wiki rebuild-index <org_root>")
        cmd_rebuild_index(args[1])

    else:
        json_error(
            f"Unknown wiki subcommand: {subcmd}. "
            "Available: index, search, status, rebuild-index"
        )
