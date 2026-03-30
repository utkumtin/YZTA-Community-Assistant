from __future__ import annotations

from pathlib import Path
from typing import Any
from jinja2 import Template


HTML_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_html_template(
    template_name: str,
    *,
    templates_dir: Path | str | None = None,
    **context: Any,
) -> str:
    root = (Path(templates_dir) if templates_dir is not None else HTML_TEMPLATES_DIR).resolve()
    path = (root / template_name).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Geçersiz şablon yolu: {template_name!r}")

    if not path.is_file():
        raise FileNotFoundError(f"Şablon dosyası bulunamadı: {path}")

    content = path.read_text(encoding="utf-8")
    return Template(content).render(**context)

def render_html_string(template: str, **context: Any) -> str:
    return Template(template).render(**context)

def render_html_file(template_path: str | Path, **context: Any) -> str:
    path = Path(template_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Şablon dosyası bulunamadı: {path}")

    content = path.read_text(encoding="utf-8")
    return Template(content).render(**context)