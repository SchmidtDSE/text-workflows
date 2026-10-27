"""Pilot coding: run a codebook over a passage table on any Jev-compatible endpoint.

A stand-in for the batch mode of text-query. The model is configuration, not code:
DECISION_URL (the systemone endpoint), DECISION_TOKEN, and optionally DECISION_MODEL and
DECISION_BATCH (texts per request, for endpoints with a /batch route such as Laya).

    python3 code.py CODEBOOK.yaml PASSAGES.parquet OUT.parquet

Pass 1 (screen) runs on every passage, pass 2 (criteria) on passages with content > 0.5.
Every value is kept: P(yes) for noul, the label and all label probabilities for choice, and
the expected level for score.
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import yaml

URL = os.environ["DECISION_URL"].rstrip("/")  # e.g. https://openrouter.ai/api/v1/systemone
HEADERS = {"Authorization": f"Bearer {os.environ['DECISION_TOKEN']}"}
MODEL = os.environ.get("DECISION_MODEL")        # e.g. ~typesafe/jev-latest; omitted if unset
BATCH = int(os.environ.get("DECISION_BATCH", "0"))  # >0: POST {URL}/batch; 0: one request per text
WORKERS = 8


def post(url, body):
    if MODEL:
        body = {"model": MODEL, **body}
    for attempt in range(5):
        try:
            r = requests.post(url, headers=HEADERS, timeout=600, json=body)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print("retry", attempt, e, flush=True)
            time.sleep(2 ** attempt)
    raise RuntimeError("decision endpoint failed five times")


def ask(texts, questions):
    """All questions for a list of texts. Returns answers, model name and total cost."""
    if BATCH:
        out, body = [], {}
        for i in range(0, len(texts), BATCH):
            body = post(URL + "/batch", {"states": texts[i:i + BATCH], "questions": questions})
            out += [res["answers"] for res in body["results"]]
            print(f"  {len(out)}/{len(texts)}", flush=True)
        return out, body.get("model", ""), 0.0
    with ThreadPoolExecutor(WORKERS) as pool:
        bodies = list(pool.map(lambda t: post(URL, {"state": t, "questions": questions}), texts))
    cost = sum(b.get("usage", {}).get("cost", 0) or 0 for b in bodies)
    print(f"  {len(bodies)}/{len(texts)} for ${cost:.3f}", flush=True)
    return [b["answers"] for b in bodies], bodies[0].get("model", "") if bodies else "", cost


def columns(answers, questions):
    """One column per question, plus label probabilities for choice questions."""
    cols = {}
    for q, spec in questions.items():
        key = {"noul": "noul", "score": "score", "choice": "choice"}[spec["type"]]
        cols[q] = [a[q][key] for a in answers]
        if spec["type"] == "choice":
            cols[q + "_p"] = [a[q]["probabilities"][a[q]["choice"]] for a in answers]
    return cols


if __name__ == "__main__":
    book, src, out = yaml.safe_load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
    df = pd.read_parquet(src)
    t0 = time.time()

    # A paragraph alone rarely names its place, so the decision model sees the paper's title too.
    states = ("Paper: " + df.title + "\n\n" + df.text) if "title" in df else df.text
    df["_state"] = states

    screen = book["passes"]["screen"]
    print("screen:", len(df), "passages")
    ans, model, cost1 = ask(df._state.tolist(), screen)
    for k, v in columns(ans, screen).items():
        df[k] = v

    crit = book["passes"]["criteria"]
    keep = df.content > 0.5
    print("criteria:", keep.sum(), "passages")
    ans, _, cost2 = ask(df.loc[keep, "_state"].tolist(), crit)
    for k, v in columns(ans, crit).items():
        df.loc[keep, k] = pd.Series(v, index=df.index[keep])

    df = df.drop(columns="_state")
    meta = {"decision_endpoint": URL.split("//")[-1].split("/")[0], "decision_model": MODEL or model or "unreported", "cost_usd": round(cost1 + cost2, 4),
            "codebook": sys.argv[1], "coded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    table = pa.Table.from_pandas(df, preserve_index=False)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **{k: str(v) for k, v in meta.items()}})
    pq.write_table(table, out, row_group_size=2000)
    print(f"coded {len(df)} passages in {time.time() - t0:.0f} s ->", out, json.dumps(meta))
