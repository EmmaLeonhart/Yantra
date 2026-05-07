"""Extract saved Claude / Grok conversation HTML pages into readable Markdown.

The HTML files in this repo are "Save Page As" snapshots from claude.ai and
grok.com. Each one contains a single conversation. This script walks every
*.html file at the repo root, identifies user and assistant turns, converts
them to Markdown, and writes one .md file per conversation under chats/.

Selectors:
- Claude:  user turns         -> any element with data-testid="user-message"
          assistant turns    -> top-level divs whose class contains
                                 "font-claude-response" (nested ones are
                                 ignored to avoid duplicating tool-use blocks)
- Grok:    user turns         -> data-testid="user-message"
          assistant turns    -> data-testid="assistant-message"

Turns are interleaved by their position in the source document so the resulting
Markdown reads in the same order as the original conversation.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "chats"


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    position: int  # source order key
    markdown: str


def _is_nested_in(node: Tag, predicate) -> bool:
    parent = node.parent
    while parent is not None:
        if isinstance(parent, Tag) and predicate(parent):
            return True
        parent = parent.parent
    return False


def _has_class_token(node: Tag, token: str) -> bool:
    cls = node.get("class")
    return bool(cls) and token in cls


def _to_markdown(node: Tag) -> str:
    md = markdownify(str(node), heading_style="ATX", bullets="-")
    # Collapse runs of >2 blank lines and trim
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md


def extract_claude(soup: BeautifulSoup) -> list[Turn]:
    turns: list[Turn] = []
    for node in soup.find_all(attrs={"data-testid": "user-message"}):
        turns.append(Turn("user", node.sourcepos or 0, _to_markdown(node)))
    for node in soup.find_all(
        class_=lambda c: c and "font-claude-response" in c
    ):
        if _is_nested_in(
            node, lambda p: _has_class_token(p, "font-claude-response")
        ):
            continue
        turns.append(Turn("assistant", node.sourcepos or 0, _to_markdown(node)))
    return turns


def extract_grok(soup: BeautifulSoup) -> list[Turn]:
    turns: list[Turn] = []
    for node in soup.find_all(attrs={"data-testid": "user-message"}):
        turns.append(Turn("user", node.sourcepos or 0, _to_markdown(node)))
    for node in soup.find_all(attrs={"data-testid": "assistant-message"}):
        turns.append(Turn("assistant", node.sourcepos or 0, _to_markdown(node)))
    return turns


def detect_source(filename: str) -> str:
    name = filename.lower()
    if "grok" in name:
        return "grok"
    if "claude" in name:
        return "claude"
    return "unknown"


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return s or "chat"


def conversation_title(soup: BeautifulSoup, fallback: str) -> str:
    title = soup.find("title")
    if title and title.get_text(strip=True):
        text = title.get_text(strip=True)
        # Strip trailing " - Claude" / " - Grok"
        return re.sub(r"\s*[-|]\s*(Claude|Grok)\s*$", "", text)
    return fallback


def render_markdown(title: str, source: str, turns: list[Turn]) -> str:
    turns = sorted(turns, key=lambda t: t.position)
    out: list[str] = [f"# {title}", "", f"_Source: {source}_", ""]
    for t in turns:
        label = "User" if t.role == "user" else "Assistant"
        out.append(f"## {label}")
        out.append("")
        out.append(t.markdown)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def process_file(html_path: Path, output_dir: Path) -> Path:
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    source = detect_source(html_path.name)
    if source == "claude":
        turns = extract_claude(soup)
    elif source == "grok":
        turns = extract_grok(soup)
    else:
        raise RuntimeError(f"Unknown source for {html_path.name}")

    title = conversation_title(soup, html_path.stem)
    md = render_markdown(title, source, turns)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{slugify(title)}.md"
    out_path.write_text(md, encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Directory containing the .html snapshots (default: repo root)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Where to write extracted .md files (default: chats/)",
    )
    args = parser.parse_args()

    html_files = sorted(args.root.glob("*.html"))
    if not html_files:
        print(f"No .html files found in {args.root}", file=sys.stderr)
        return 1

    for html in html_files:
        out = process_file(html, args.output)
        print(f"{html.name}  ->  {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
