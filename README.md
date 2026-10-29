# text-workflows

Recipes, scope and coded runs for document corpora used by GLEN applications: scientific
literature, grey literature, and legal and policy documents. A corpus is processed into AI-ready,
cloud-native tables by [`text-ingest`](https://github.com/SchmidtDSE/text-ingest), and
coded with a codebook by [`text-query`](https://github.com/SchmidtDSE/text-query). This
repository records what each corpus is meant to cover and how each published table was made.
It is the text counterpart of
[`data-workflows`](https://github.com/boettiger-lab/data-workflows), which does the same for
spatial datasets.

**Status:** planning and pilot. The design is in [PLAN.md](PLAN.md).

## Contents

| Path | Purpose |
|---|---|
| `PLAN.md` | The design of the text stack for GLEN applications, with its first application, BBNJ site assessment in the [High Seas app](https://github.com/boettiger-lab/bosl-high-seas), and candidate terrestrial and legal corpora |
| `corpora/<corpus>/corpus.yaml` | The recipe for one corpus: sources, scope, access and processing options |
| `coded/<corpus>--<codebook>/run.yaml` | One coded run: corpus snapshot, codebook and commit, model endpoint and output |
| `pilot/` | The pilot scripts that compared Laya, Jev and Kev on the Emperor Seamount Chain corpus |

## Principles

- Scope lives in the GitHub issue for each corpus or coded run.
- Source documents and derived tables live on S3, with their metadata (Croissant, README,
  `AGENTS.md` and a thin STAC record) kept beside them in the bucket, not in this repository.
- Passage text from a private corpus is never committed here or published.
- Models are configuration: an endpoint and a token, never hard-wired.
- Application specifics live in recipes and codebooks: a corpus recipe sets its document kind,
  gazetteers and H3 resolution, and each application keeps its codebooks in its own
  repository.
