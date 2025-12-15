#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一次性工具：把“编号清晰”的访谈提纲 docx 转成结构化 questions.json + questions.txt

用法：
  python tools/convert_docx_questions.py "survey/xxx.docx"
  python tools/convert_docx_questions.py "survey/xxx.docx" --out-dir survey

输出：
  <out-dir>/questions.json
  <out-dir>/questions.txt
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from docx import Document


Q_RE = re.compile(
    r"^(?:Q\s*)?(?P<id>\d{1,3})\s*(?:[\.、:：\)）]|（(?P=id)）)\s*(?P<text>.+)$",
    re.IGNORECASE,
)


def extract_questions(docx_path: Path) -> list[dict]:
    doc = Document(str(docx_path))
    questions: list[dict] = []

    # 1) 普通段落（少量 docx 会直接按段落列题）
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        m = Q_RE.match(t)
        if not m:
            continue
        qid = m.group("id").strip()
        qtext = m.group("text").strip()
        if qtext:
            questions.append({"id": qid, "text": qtext, "source": "paragraph"})

    # 2) 表格（你的模板是表格：题号/提纲原题）
    for ti, tb in enumerate(doc.tables):
        for ri, row in enumerate(tb.rows):
            cells = row.cells
            if len(cells) < 2:
                continue
            c0 = "\n".join((p.text or "").strip() for p in cells[0].paragraphs).strip()
            c1 = "\n".join((p.text or "").strip() for p in cells[1].paragraphs).strip()
            if not c0 or not c1:
                continue
            if c0 in ("题号", "编号", "序号"):
                continue
            if c1 in ("提纲原题",):
                continue
            if not re.fullmatch(r"\d{1,3}", c0):
                continue
            questions.append({"id": c0, "text": c1, "source": f"table[{ti}].row[{ri}]"})

    return questions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx", help="问题模板 docx 路径")
    ap.add_argument("--out-dir", default="survey", help="输出目录（默认 survey）")
    args = ap.parse_args()

    docx_path = Path(args.docx).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    questions = extract_questions(docx_path)
    payload = {
        "source_docx": str(docx_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(questions),
        "questions": questions,
    }

    json_path = out_dir / "questions.json"
    txt_path = out_dir / "questions.txt"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_lines = [f"Q{q['id']}\\t{q['text']}" for q in questions]
    txt_path.write_text("\\n".join(txt_lines) + ("\\n" if txt_lines else ""), encoding="utf-8")

    print(f"OK: {len(questions)} questions")
    print(f"- {json_path}")
    print(f"- {txt_path}")


if __name__ == "__main__":
    main()
