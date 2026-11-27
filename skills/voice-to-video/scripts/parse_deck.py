#!/usr/bin/env python3
"""Parse .pptx (pure Python stdlib OOXML) or .pdf decks into structured JSON/Markdown for video scripting.

Zero external Python packages required for .pptx text, tables, speaker notes, and embedded media.
If `libreoffice` and `pdftoppm` are installed, optionally renders each slide to PNG (`--render-slides`).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def extract_xml_paragraphs(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    lines: list[str] = []
    for p in root.findall(".//a:p", NS):
        texts = [t.text for t in p.findall(".//a:t", NS) if t.text]
        line = "".join(texts).strip()
        if line:
            lines.append(line)
    return lines


def slide_num_key(name: str) -> int:
    m = re.search(r"(\d+)\.xml$", name)
    return int(m.group(1)) if m else 0


def parse_pptx(pptx_path: Path, out_dir: Path, extract_media: bool = True) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    slides_data: list[dict] = []
    media_files: list[str] = []

    with zipfile.ZipFile(pptx_path, "r") as zf:
        names = zf.namelist()
        slide_xmls = sorted(
            [n for n in names if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
            key=slide_num_key,
        )

        # Build slide -> notesSlide mapping from slide rels
        notes_map: dict[int, str] = {}
        for s_xml in slide_xmls:
            idx = slide_num_key(s_xml)
            rels_name = f"ppt/slides/_rels/slide{idx}.xml.rels"
            if rels_name in names:
                rels_root = ET.fromstring(zf.read(rels_name))
                for rel in rels_root:
                    target = rel.attrib.get("Target", "")
                    if "notesSlide" in target:
                        norm = target.replace("../", "ppt/")
                        if norm in names:
                            notes_map[idx] = norm

        for seq, s_xml in enumerate(slide_xmls, start=1):
            idx = slide_num_key(s_xml)
            paragraphs = extract_xml_paragraphs(zf.read(s_xml))
            title = paragraphs[0] if paragraphs else f"第 {seq} 页"
            body = paragraphs[1:] if len(paragraphs) > 1 else []

            notes = ""
            if idx in notes_map:
                note_lines = extract_xml_paragraphs(zf.read(notes_map[idx]))
                # Filter standalone slide number footer if present
                note_lines = [ln for ln in note_lines if ln != str(seq) and ln != str(idx)]
                notes = "\n".join(note_lines)

            slides_data.append(
                {
                    "slide_number": seq,
                    "title": title,
                    "bullets": body,
                    "speaker_notes": notes,
                    "rendered_image": "",
                }
            )

        if extract_media:
            media_dir = out_dir / "media"
            for n in sorted(names):
                if n.startswith("ppt/media/") and not n.endswith("/"):
                    fname = Path(n).name
                    if Path(fname).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        media_dir.mkdir(parents=True, exist_ok=True)
                        dest = media_dir / fname
                        dest.write_bytes(zf.read(n))
                        media_files.append(str(dest))

    return {
        "source_file": str(pptx_path),
        "format": "pptx",
        "slide_count": len(slides_data),
        "slides": slides_data,
        "extracted_media": media_files,
    }


def parse_pdf(pdf_path: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    slides_data: list[dict] = []
    if shutil.which("pdftotext"):
        txt = subprocess.check_output(["pdftotext", str(pdf_path), "-"], text=True, errors="ignore")
        pages = [p.strip() for p in txt.split("\x0c") if p.strip()]
        for seq, page in enumerate(pages, start=1):
            lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
            slides_data.append(
                {
                    "slide_number": seq,
                    "title": lines[0] if lines else f"第 {seq} 页",
                    "bullets": lines[1:] if len(lines) > 1 else [],
                    "speaker_notes": "",
                    "rendered_image": "",
                }
            )
    return {
        "source_file": str(pdf_path),
        "format": "pdf",
        "slide_count": len(slides_data),
        "slides": slides_data,
        "extracted_media": [],
    }


def render_slides_to_png(input_path: Path, out_dir: Path, deck_data: dict) -> None:
    slides_dir = out_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = input_path

    if input_path.suffix.lower() in (".pptx", ".ppt"):
        soffice = shutil.which("libreoffice") or shutil.which("soffice")
        if not soffice:
            print("Note: libreoffice not installed; skipping slide PNG rendering (text/notes extracted cleanly).", file=sys.stderr)
            return
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(input_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        pdf_path = out_dir / f"{input_path.stem}.pdf"

    if not shutil.which("pdftoppm"):
        print("Note: pdftoppm not installed; skipping slide PNG rendering.", file=sys.stderr)
        return

    prefix = slides_dir / "slide"
    subprocess.run(
        ["pdftoppm", "-png", "-r", "150", str(pdf_path), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    rendered = sorted(slides_dir.glob("slide-*.png"))
    for idx, img_p in enumerate(rendered):
        norm_p = slides_dir / f"slide_{idx+1:02d}.png"
        img_p.rename(norm_p)
        if idx < len(deck_data["slides"]):
            deck_data["slides"][idx]["rendered_image"] = str(norm_p)
        else:
            deck_data["slides"].append(
                {
                    "slide_number": idx + 1,
                    "title": f"第 {idx + 1} 页",
                    "bullets": [],
                    "speaker_notes": "",
                    "rendered_image": str(norm_p),
                }
            )
    deck_data["slide_count"] = len(deck_data["slides"])


def write_markdown_summary(deck_data: dict, md_path: Path) -> None:
    lines = [
        f"# PPT/PDF 内容提取摘要 — `{Path(deck_data['source_file']).name}`",
        "",
        f"- **总页数**：{deck_data['slide_count']} 页",
        f"- **提取内嵌图片**：{len(deck_data.get('extracted_media', []))} 张",
        "",
    ]
    for s in deck_data["slides"]:
        lines.append(f"## 第 {s['slide_number']:02d} 页：{s['title']}")
        if s["bullets"]:
            for b in s["bullets"]:
                lines.append(f"- {b}")
        if s["speaker_notes"]:
            lines.append(f"\n> **演讲者备注**：{s['speaker_notes']}")
        if s.get("rendered_image"):
            lines.append(f"- **页面截图**：`{s['rendered_image']}`")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text, speaker notes, media, and optional slide PNGs from PPTX/PDF.")
    parser.add_argument("--input", required=True, help="Path to .pptx or .pdf file")
    parser.add_argument("--out-dir", required=True, help="Output directory (e.g. projects/<slug>/work/deck)")
    parser.add_argument("--render-slides", action="store_true", help="Render slides to PNG if libreoffice/pdftoppm available")
    args = parser.parse_args()

    in_path = Path(args.input).resolve()
    if not in_path.exists():
        print(f"Error: file not found: {in_path}", file=sys.stderr)
        return 1
    out_dir = Path(args.out_dir).resolve()

    ext = in_path.suffix.lower()
    if ext == ".pptx":
        data = parse_pptx(in_path, out_dir)
    elif ext == ".pdf":
        data = parse_pdf(in_path, out_dir)
    else:
        print(f"Error: unsupported deck format '{ext}'. Use .pptx or .pdf.", file=sys.stderr)
        return 1

    if args.render_slides:
        render_slides_to_png(in_path, out_dir, data)

    json_path = out_dir / "deck.json"
    md_path = out_dir / "deck.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_summary(data, md_path)

    print(
        json.dumps(
            {
                "deck_json": str(json_path),
                "deck_md": str(md_path),
                "slide_count": data["slide_count"],
                "extracted_media_count": len(data.get("extracted_media", [])),
                "rendered_slides": sum(1 for s in data["slides"] if s.get("rendered_image")),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
