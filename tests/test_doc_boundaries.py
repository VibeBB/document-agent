"""Boundary tests for figure viewing and the README quick-start rule.

Techniques follow docs/test-coverage.md: 3-value boundaries (below / on /
above) on the 5 MiB image limit and the 12-byte WebP signature, and
equivalence classes per image MIME type.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from conftest import BRIEF_REL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/doc/scripts"))

import doc_figures  # noqa: E402

sys.path.insert(0, str(ROOT / "plugins/doc/skills/doc-lint/scripts"))
from doc_markdown import MAX_QUICKSTART_STEPS  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n"
LIMIT = doc_figures.MAX_IMAGE_BYTES


@pytest.mark.parametrize(
    ("size", "ok"), [(LIMIT - 1, True), (LIMIT, True), (LIMIT + 1, False)]
)
def test_image_size_three_value_boundary(tmp_path: Path, size: int, ok: bool) -> None:
    image = tmp_path / "figure.png"
    image.write_bytes(PNG + b"\x00" * (size - len(PNG)))
    assert image.stat().st_size == size
    result = doc_figures.view_figure(image, tmp_path)
    assert result["ok"] is ok
    if not ok:
        assert "5 MiB" in result["errors"][0]


@pytest.mark.parametrize(
    ("data", "ok"),
    [
        (b"RIFF\x04\x00\x00\x00WEB", False),
        (b"RIFF\x04\x00\x00\x00WEBP", True),
        (b"RIFF\x04\x00\x00\x00WEBPx", True),
        (b"RIFX\x04\x00\x00\x00WEBP", False),
    ],
)
def test_webp_signature_length_boundary(tmp_path: Path, data: bytes, ok: bool) -> None:
    (tmp_path / "render.webp").write_bytes(data)
    assert doc_figures.view_figure("render.webp", tmp_path)["ok"] is ok


# Equivalence classes: each MIME type accepts only its own signature.
@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("photo.jpg", PNG),
        ("photo.jpeg", b"GIF89a"),
        ("animation.gif", b"GIF88a"),
        ("figure.png", b"\xff\xd8\xff\x00"),
    ],
)
def test_signature_must_match_extension(tmp_path: Path, name: str, data: bytes) -> None:
    (tmp_path / name).write_bytes(data)
    result = doc_figures.view_figure(name, tmp_path)
    assert result["ok"] is False
    assert "does not match" in result["errors"][0]


def test_empty_image_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "empty.png").write_bytes(b"")
    assert doc_figures.view_figure("empty.png", tmp_path)["ok"] is False


STEP_2 = "2. Turn the knob until the ring shows the minutes you want."
STEP_3 = "3. Press the knob. The ring starts counting down."
STEP_4 = "4. When it chimes, press the knob to stop the glow."


def _quick_start_problems(doc_lint: ModuleType, root: Path, steps: int) -> list[str]:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert f"{STEP_2}\n{STEP_3}\n{STEP_4}" in text
    if steps == 1:
        replacement = "Then turn and press the knob."
    elif steps == 2:
        replacement = STEP_2
    else:
        replacement = "\n".join(
            [STEP_2, STEP_3, *(f"{n}. Step {n}." for n in range(4, steps + 1))]
        )
    readme.write_text(
        text.replace(f"{STEP_2}\n{STEP_3}\n{STEP_4}", replacement), encoding="utf-8"
    )
    report = doc_lint.build_report(root / BRIEF_REL, root)
    return [
        p for doc in report["documents"] for p in doc["problems"] if "Quick start" in p
    ]


@pytest.mark.parametrize(
    ("steps", "needle"),
    [
        (1, "needs >=2 numbered steps"),
        (2, None),
        (3, None),
        (6, None),
        (MAX_QUICKSTART_STEPS, None),
        (MAX_QUICKSTART_STEPS + 1, f"(max {MAX_QUICKSTART_STEPS})"),
    ],
)
def test_quick_start_step_count_three_value_boundary(
    doc_lint: ModuleType, workspace: Path, steps: int, needle: str | None
) -> None:
    problems = _quick_start_problems(doc_lint, workspace, steps)
    if needle is None:
        assert problems == []
    else:
        assert any(needle in problem for problem in problems), problems
