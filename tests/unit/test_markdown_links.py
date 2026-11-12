"""Relative links in the project's Markdown files must resolve (T50, OPS-01..06, AZR-01)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# [text](target) or [text](target "title"); images ![alt](target) match too.
LINK_RE = re.compile(r'\[[^\]]*\]\(\s*([^)\s]+)(?:\s+"[^"]*")?\s*\)')
FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.DOTALL | re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


def markdown_files(root: Path) -> list[Path]:
    """README.md at the root, every docs/*.md and every README.md under terraform/."""
    files = [root / "README.md"]
    files += sorted((root / "docs").glob("*.md"))
    files += sorted((root / "terraform").rglob("README.md"))
    return [path for path in files if path.is_file()]


def relative_links(text: str) -> list[str]:
    """Link targets that point to files (code blocks, inline code, URLs and anchors ignored)."""
    text = FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    targets = [match.group(1) for match in LINK_RE.finditer(text)]
    return [t for t in targets if not t.lower().startswith(EXTERNAL_PREFIXES)]


def broken_links(files: list[Path]) -> list[str]:
    """``<file> -> <target>`` for every relative link whose file does not exist."""
    broken = []
    for path in files:
        for target in relative_links(path.read_text(encoding="utf-8")):
            file_part = target.split("#", 1)[0]
            if file_part and not (path.parent / file_part).exists():
                broken.append(f"{path.name} -> {target}")
    return broken


def test_all_relative_links_in_repository_resolve():
    # OPS-01..06, AZR-01: every relative link of the docs resolves to an existing file.
    files = markdown_files(REPO_ROOT)
    assert REPO_ROOT / "README.md" in files
    assert broken_links(files) == []


def test_broken_link_is_detected(tmp_path):
    # The check must fail on a synthetic broken link, and pass on a valid one.
    (tmp_path / "existing.md").write_text("# ok\n", encoding="utf-8")
    page = tmp_path / "page.md"
    page.write_text(
        "[ok](existing.md) [ok com âncora](existing.md#secao) "
        "[quebrado](missing.md) [site](https://example.com/x.md) [âncora](#topo)\n"
        "`[em código](ignored.md)`\n"
        "```\n[em bloco](ignored-too.md)\n```\n",
        encoding="utf-8",
    )
    assert broken_links([page]) == ["page.md -> missing.md"]


def test_root_readme_links_every_doc_and_the_terraform_readme():
    # T50 Done when: the root README points to every docs/*.md and to terraform/README.md.
    readme = REPO_ROOT / "README.md"
    linked = {
        (readme.parent / t.split("#", 1)[0]).resolve()
        for t in relative_links(readme.read_text(encoding="utf-8"))
    }
    expected = {path.resolve() for path in (REPO_ROOT / "docs").glob("*.md")}
    expected.add((REPO_ROOT / "terraform" / "README.md").resolve())
    assert expected - linked == set()
