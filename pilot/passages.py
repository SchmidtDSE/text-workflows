"""Pilot passage extraction: PDFs to one row per paragraph.

A stand-in for the GROBID structure stage of corpus-ingest. Text blocks come from PyMuPDF.
Blocks repeated on three or more pages (download footers, running heads) and table-of-contents
lines are dropped, short consecutive blocks are merged up to paragraph length, and everything
after a References heading is dropped.

    python3 passages.py OUT.parquet PDF [PDF ...]

The output holds copyrighted text: write it to the scratchpad or the private bucket, never
to this repository.
"""

import collections
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd
import pymupdf

STOP = re.compile(r"^\s*(references|literature cited|bibliography|acknowledg(e)?ments?)\s*$", re.I)
DOTS = re.compile(r"(\. ){4,}|\.{5,}")
MIN_CHARS, TARGET_CHARS = 200, 400


def clean(text):
    text = re.sub(r"-\n(?=[a-z])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def title(doc, path):
    t = (doc.metadata or {}).get("title", "").strip()
    return t if len(t) > 15 and not t.lower().startswith(("doi", "microsoft word")) else path.stem


def passages(path):
    data = path.read_bytes()
    doc_id = hashlib.sha256(data).hexdigest()[:16]
    doc = pymupdf.open(stream=data, filetype="pdf")
    pages = [[clean(b[4]) for b in page.get_text("blocks")] for page in doc]
    seen = collections.Counter(t for blocks in pages for t in set(blocks) if t)
    rows, ordinal, buf, buf_page = [], 0, "", 1

    def emit(text, page):
        nonlocal ordinal
        if len(text) >= MIN_CHARS:
            pid = hashlib.sha256(f"{doc_id}|{ordinal}|{text}".encode()).hexdigest()[:16]
            rows.append(dict(passage_id=pid, doc_id=doc_id, title=title(doc, path), page=page,
                             ordinal=ordinal, text=text, n_chars=len(text)))
            ordinal += 1

    for number, blocks in enumerate(pages, start=1):
        for text in blocks:
            if STOP.match(text):
                emit(buf, buf_page)
                return doc_id, rows
            if not text or seen[text] >= 3 or DOTS.search(text):
                continue
            if not buf:
                buf_page = number
            buf = f"{buf} {text}".strip()
            if len(buf) >= TARGET_CHARS or text.endswith((".", ":")) and len(buf) >= MIN_CHARS:
                emit(buf, buf_page)
                buf = ""
    emit(buf, buf_page)
    return doc_id, rows


if __name__ == "__main__":
    out, pdfs = sys.argv[1], [Path(p) for p in sys.argv[2:]]
    rows = []
    for p in pdfs:
        doc_id, r = passages(p)
        for x in r:
            x.update(folder=p.parent.name, file=p.name)
        rows += r
        print(f"{len(r):4d} passages  {p.parent.name[:30]} / {p.name[:60]}")
    pd.DataFrame(rows).to_parquet(out, row_group_size=2000)
    print(len(rows), "passages written to", out)
