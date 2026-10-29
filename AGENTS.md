# Agent instructions: corpus workflows

This repository holds recipes and scope for corpora, not code and not data. The design is in
[PLAN.md](PLAN.md). Tool knowledge belongs with the tools: OCR, GROBID and segmentation in
`text-ingest`, and codebook design and model endpoints in `text-query`.

## Scope lives in the issue

Every decision that defines what a corpus or coded run delivers belongs in its GitHub issue
before you act on it: sources, coverage or outline, access, licence policy, languages, the
codebook and its commit, the model, and the output location. Sessions are disposable, so do not
rely on memory for scope. When the user tells you a fact only they hold, such as who compiled a
corpus or why a section is empty, write it into the issue in the same turn.

## Copyrighted text stays private

Most documents in a corpus are publisher copyright. Never commit passage text, quotes beyond a
short citation, PDFs, or parquet files containing text to this repository, which is public.
Passage tables and pilot outputs go to the corpus's private bucket. Coded values,
bibliographic metadata and H3 places may be published.

## Snapshots

A corpus build is an immutable snapshot under `derived/<date>/`. Coded tables cite passage ids
from one snapshot. Never rewrite a published snapshot; rebuild into a new one.

## Credentials

Model endpoints and tokens, and S3 credentials, come from the environment. Never write a token
into a recipe, a run file or an issue. `run.yaml` names the endpoint, not the token.
