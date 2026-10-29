# Pilot of 2026-10-27

The pilot coded 1,534 passages from 12 papers of the `high-seas-lit` corpus, one per section
folder, with the BBNJ Annex I codebook, on Laya and on Jev. Results and conclusions are in the
Pilot results section of [PLAN.md](../PLAN.md). Inputs and outputs, which contain passage
text, are in the private bucket at `s3://high-seas-lit/pilot/2026-10-27/`.

These scripts are stand-ins for `text-ingest` and `text-query`, kept so the comparison can be
rerun.

| Script | Purpose |
|---|---|
| `passages.py` | PDFs to one row per paragraph with PyMuPDF, standing in for GROBID |
| `code.py` | Runs a codebook on any Jev-compatible endpoint, configured by environment variables |
| `labels.py` | Reference labels for the 48-passage sample, written blind to both models; a person should check them |
| `score.py` | Scores each model's codes against the labels |
| `compare.py` | Compares Kev with the stored Laya and Jev codes, against the labels and against Jev |

## Rerunning

The codebook is `codebooks/bbnj-annex1.yaml` in
[`bosl-high-seas`](https://github.com/boettiger-lab/bosl-high-seas). Write outputs to a local
scratch directory or the private bucket, never to this repository.

```bash
python3 passages.py passages.parquet PDF [PDF ...]

# Jev on OpenRouter: one request per passage
DECISION_URL=https://openrouter.ai/api/v1/systemone DECISION_TOKEN=$JEV_KEY \
DECISION_MODEL='~typesafe/jev-latest' python3 code.py bbnj-annex1.yaml passages.parquet jev.parquet

# Laya: batched requests
DECISION_URL=$LAYA_URL/v1/systemone DECISION_TOKEN=$LAYA_API_KEY DECISION_BATCH=32 \
python3 code.py bbnj-annex1.yaml passages.parquet laya.parquet

# Kev: one request per passage; it takes the Laya key
DECISION_URL=https://kev.carlboettiger.info/v1/systemone DECISION_TOKEN=$LAYA_API_KEY \
DECISION_MODEL=kev-latest python3 code.py bbnj-annex1.yaml passages.parquet pilot2-kev.parquet
```

`score.py` expects `label-sample.parquet`, `pilot2-coded.parquet` (Laya) and
`pilot2-jev.parquet` in the working directory; copy them from the bucket. `compare.py` also
expects `pilot2-kev.parquet` and the full run's Jev codes at `../full/coded-jev.parquet`.
