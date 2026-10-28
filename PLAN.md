# Literature evidence and data coverage for BBNJ site assessment

Working plan, begun 2026-10-27 in `boettiger-lab/bosl-high-seas` and moved here. Status: draft
for discussion. Numbers marked [verify] are estimates. The first application is the High Seas
app (`boettiger-lab/bosl-high-seas`), which holds the BBNJ codebook.

## Goal

**We want a user to propose a high-seas area and see, criterion by criterion, what evidence
supports it, how strong that evidence is, and how much is simply unknown.** The app already
answers the spatial half through the DuckDB MCP server. This plan adds the literature, and a
measure of how data-poor each site is.

- The unit of assessment is either an existing EBSA (`GLOBAL_ID`) or a drawn polygon, both
  reduced to H3 cells as the explorer already does.
- The criteria are the 22 indicative criteria of BBNJ Annex I, (a) uniqueness to
  (v) existing conservation and management measures. Article 19(4) lists what a proposal must
  contain, including (b) information on the criteria, (c) human activities and (d) the state
  of the marine environment.
- The data-poverty question has equal weight: without it, priority areas become the
  best-studied areas.

## Design

**The design mirrors the spatial stack, one repository per role.** Names give the kind of
data and the role, follow the open standards underneath rather than a brand or a transport,
and keep the GLEN name for front ends. Each component is open by default with authentication
as an option.

| Role | Spatial and tabular data | Text corpora |
|---|---|---|
| Builder | `geo-ingest` (now `cng-datasets`): source files to GeoParquet, H3 hex, PMTiles and COG | `corpus-ingest`: PDFs to passage tables, bibliographic records and H3 places |
| Workflows | `geo-workflows` (now `data-workflows`): one recipe and one issue per dataset | `corpus-workflows`: one recipe and one issue per corpus, and per coded run |
| Resource metadata | STAC, following Portolan | Croissant and CSL-JSON, with a thin STAC record for discovery |
| Query tool | `geo-query` (now `mcp-data-server`): SQL over S3 parquet, tuned for H3 joins | `text-query`: codebooks and structured extraction over any text column a SQL query returns |
| Front end | geo-agent chat apps and the glen-charts explorer | the same front ends |

The layers connect through S3. Builders write AI-ready parquet. `text-query` reads it and writes
coded tables back as new datasets. `geo-query` then joins those to the H3 grid like any other
layer. Nothing below the front end knows about BBNJ: that lives in the codebook and the
application.

We build around the high-seas case because a concrete use keeps the design honest, but the
first two layers are meant for every GLEN app. An app that today answers questions only from
SQL-queried data could add a PDF corpus of reports, management plans or studies the same way it
adds a layer. It would process the corpus with the pipeline, list it in its catalog and give
the agent `text-query`. Nothing is hard-wired that does not need to be: models are
endpoints, corpora are catalog entries and codebooks are files.

## The corpus

**The corpus is a dossier on one site, the Emperor Seamount Chain, organised by the sections
of a site description.** "ESC" in the original zip name is the Emperor Seamount Chain, and it
matches EBSA `NP_18`, "Emperor Seamount Chain and Northern Hawaiian Ridge", 310,271 km².

- It is stored in `s3://high-seas-lit/` on NRP (private), one prefix per original folder:
  12 folders, 202 PDFs, 1 CSV, 1 DOCX, 1.04 GiB.
- There are 6,102 pages and 18.2 M characters of extractable text. Eight PDFs (about 720 pages)
  are scans with no text layer, including Hess 1946, Wilson 1963 and the 280-page INPFC
  bulletin.
- There are 193 unique PDFs. Eight files are byte-identical copies under different names or
  folders, e.g. Prokofiev 2025/2026 appears in three folders. Some near-duplicates are whole
  volumes filed under one chapter's name: the Morato and Thompson files are the same 556-page
  seamount book.
- The section numbers have gaps (7.1.1, 7.1.2, 7.1.4, 7.2.2 onward, 7.3, 8.1, 8.2.2, 8.2.6,
  8.3, 8.4). We should get the full outline from the team that compiled the dossier. The empty
  sections are a first, honest inventory of what is not known.
- Much of the evidence comes from other regions. 31 of 34 geology PDFs mention the chain or a
  named seamount in it, but only 2 of 12 mid-water nekton PDFs, 1 of 14 carbon-flux PDFs and
  2 of 12 chemistry PDFs do. A folder can look full while its site-specific evidence is thin,
  so every passage needs a location.
- `6.Chemical oceanography/Kassem and Shamberger, 2026_Data file.csv` is a station-level
  bottle dataset (cruise KM2212, 2022) that belongs in the spatial catalog as point data. The
  Korean `참고문헌 링크.docx` ("reference links") may list more sources.

## Corpus processing

**Corpus processing should be a pipeline of idempotent cluster jobs that turn a folder of PDFs
into cloud-native tables with complete metadata, in the same spirit as `geo-ingest`.** It is
general purpose: the same command should process this dossier, the CBD EBSA descriptions, or
any other document collection.

### Stages

| Stage | What it does | Tools | Output |
|---|---|---|---|
| Inventory | Lists every object, hashes it, records original path and folder | `rclone`, sha256 | `manifest.parquet`: path, folder, sha256, bytes, media type |
| Deduplication | Collapses identical files to one document, keeping every path and folder as a list; flags near-duplicates (same DOI, same first-page text) for review | sha256, then text similarity | `doc_id` = content hash; `paths[]`, `sections[]` |
| Text layer check | Decides per page, not per file, whether the page needs OCR | PyMuPDF character counts | page flags |
| OCR | Adds a text layer to scanned pages | OCRmyPDF (Tesseract) | OCR'd PDF stored next to the original, never replacing it |
| Structure | Extracts title, authors, abstract, sections, paragraphs and parsed references, with page numbers | GROBID (TEI), with PyMuPDF as fallback | `passages.parquet`, `references.parquet` |
| Metadata | Resolves DOI and completes bibliographic fields; detects language; records licence and open-access status | Crossref, OpenAlex, Unpaywall | `documents.parquet` |
| Places | Finds place names and coordinates in each passage, matches them to gazetteers, assigns H3 res-5 cells (about 250 km²) with a precision class | GEBCO Gazetteer of Undersea Feature Names, Marine Regions, coordinate regex, an extraction model for names | `places.parquet` (h5, h0) |
| Search index | Optional full-text and embedding indexes over passages | DuckDB FTS; an open-weights embedding model on NRP | index files or an embedding column |
| Publish | Validates the outputs, writes the corpus description and a thin STAC record | `mlcroissant` validation, the corpus checks below | `croissant.json`, README, `AGENTS.md`, `stac-collection.json` |

- **Async and resumable.** Each stage is an indexed Kubernetes Job with one document or a batch
  of documents per index. Outputs are keyed by content hash, so a rerun skips finished work
  and a new PDF dropped into the bucket is processed incrementally.
- **Provenance in the file.** Every parquet carries the tool version, stage, OCR engine,
  GROBID version and build time in its key-value metadata, as `cng_datasets/provenance.py`
  does. A bad OCR or parse can then be traced to every table it touched.
- **Checks before publish,** as in `hex_checks.py`: the share of pages with text after OCR,
  passages per page, unresolved DOIs, duplicates and places that fall on land.
- **Originals are never modified.** The original folder layout stays as uploaded. Everything
  derived goes under `derived/<snapshot>/`, keyed by `doc_id`.
- **Snapshots are frozen.** Coded tables cite passage ids, so each build is an immutable
  snapshot named by date. A passage id is a hash of the document, its position and its text,
  so ids survive when papers are added and a rebuild makes a new snapshot.
- **Small row groups.** Passage text is wide, so the parquet should use small row groups for
  fast range reads, as the data-workflows serialisation standard already requires.

### Output layout

```
s3://high-seas-lit/
  <12 original folders>/                      source files, unchanged
  README.md                                   what the corpus is, its scope, caveats and licences
  AGENTS.md                                   how an agent should use it, and what it must not do
  croissant.json                              tables, columns, files, licence (current snapshot)
  stac-collection.json                        thin discovery record pointing to croissant.json
  derived/2026-10-27/
    manifest.parquet       path, folder, sha256, bytes, media_type
    pdf-ocr/<doc_id>.pdf   OCR'd copies of scanned documents
    tei/<doc_id>.xml       GROBID's structured form of each paper
    documents.parquet      doc_id, paths[], sections[], doi, title, authors, year, container,
                           abstract, language, licence, oa_status, pages, text_source
    passages.parquet       passage_id, doc_id, section_heading, page, ordinal, text, n_chars
    references.parquet     doc_id, cited_doi, cited_title, cited_year
    places.parquet         passage_id, doc_id, place_name, gazetteer, gazetteer_id,
                           precision, h5, h0
```

### Metadata standard

**A corpus describes itself in standards made for document collections. STAC is only how
agents find it.** Corpora differ from spatial datasets in ways STAC does not model: they are
assembled by people and grow over time, each document has its own licence and bibliographic
record, many are private, and their geometry is inferred later and is absent for many
passages.

- **Croissant** (MLCommons' JSON-LD format for AI-ready datasets) describes the tables,
  columns, files, licence and snapshot. Hugging Face generates it for its datasets, so it is
  what other tools will look for, and `mlcroissant` validates it.
- **CSL-JSON field names** in `documents.parquet` hold the bibliographic record of each
  document, so citations convert directly to BibTeX.
- **TEI XML** from GROBID is kept as the structured form of each paper.
- **README and `AGENTS.md`** sit at the corpus root. This is Portolan's rule for catalogs and is
  just as useful here. They say what the corpus covers, where it is thin, the licence policy
  and what an agent must not do with passage text.
- **A thin STAC collection** points to `croissant.json`, so `geo-query` and the agents find a
  corpus the same way they find everything else. A private corpus is listed in a private
  catalog (`STAC_CATALOG_TOKEN`).
- **Derived spatial products are ordinary STAC collections.** The H3 places and the coded
  tables joined to the grid are published in `public-high-seas` like any other layer, and link
  back to the corpus snapshot they came from.

### Workflows

**Corpora get their own workflows repository, `corpus-workflows`, parallel to
`data-workflows`.** It has the same discipline: scope in the issue, cluster jobs, provenance,
and outputs published to S3 with their metadata kept in the bucket, not the repository.

```
corpus-workflows/
  AGENTS.md                         scope, licence and publication rules
  .github/ISSUE_TEMPLATE/
    corpus.yml                      sources, scope or outline, access, licence policy, curator, languages
    coded-run.yml                   corpus snapshot, codebook, model, output
  corpora/<corpus>/
    corpus.yaml                     sources (bucket prefix, DOI list, OpenAlex query, Zotero group),
                                    section outline, access, OCR languages
    k8s/                            generated by corpus-ingest
  coded/<corpus>--<codebook>/
    run.yaml                        corpus snapshot, codebook file and commit,
                                    model endpoint (no token), output path
```

- **Codebook files live in the application repository,** for example
  `bosl-high-seas/codebooks/bbnj-annex1.yaml`, because they encode domain judgment and change
  with the app. A coded run pins one by commit, so every published coded table traces to an
  exact question set, corpus snapshot and model.
- **Curators work on S3; scope lives in issues.** Domain partners add PDFs to the bucket, as
  they did here. The issue records what the corpus is meant to cover, such as the dossier
  outline and its empty sections, and a rebuild produces a new snapshot.

### Agent guidance

**Guidance about how a tool works ships with the tool. Guidance about what we publish and how
we decide stays in the workflows repository.** Tool knowledge then changes with the code it
describes, which is the pattern of Portolan's bootstrap skill.

| Guidance | Home |
|---|---|
| Scope in issues, publication boundaries, licence policy, worked recipes | workflows repository (`data-workflows`, `corpus-workflows`) |
| How the builder behaves: hex tuning, raster hexing, job troubleshooting; OCR, GROBID and segmentation for corpora | builder repository (`geo-ingest`, `corpus-ingest`) |
| Writing codebooks: one idea per question, exact wording, labels with descriptions, measuring recall on the "yes" cases | `text-query` |
| Cluster operations: NRP usage policy, preemption, Armada, S3 endpoints | one shared NRP skill set used by both builders, not copied into each |
| Spatial metadata | Portolan's conventions and validator, replacing much of `stac-authoring` |

For `data-workflows` this means `hex-tuning`, `raster-hexing` and most of
`job-troubleshooting` move to `cng-datasets`. `armada-pipeline` and `pod-preemption` move to
the shared NRP set, and `stac-authoring` is reconciled with Portolan. For the corpus side we
start with this split rather than migrating to it later.

## Text query tool

**`text-query` should be as generic for text as `geo-query` is for tables.** Any
SQL query that returns an id column and a text column can be coded. It is not specific to this
corpus, and it is useful for the CBD EBSA descriptions, OpenAlex abstracts, dataset
descriptions in a STAC catalog, or the corporate reports in CSOL 208.

### Front ends

**One core library has two front ends, because batch coding and interactive coding are
different jobs.** This is the same split as `geo-ingest` (batch on the cluster) and
`geo-query` (interactive queries).

- **Command line and cluster jobs, for batch.** Coding a whole corpus is a long, resumable
  job. It should be generated and run like a `geo-ingest` workflow, writing a coded parquet
  to S3. MCP is the wrong fit for a 40-minute job.
- **MCP server, for interactive use.** An agent in a geo-agent or GLEN app asks a new question
  of a few hundred passages during a conversation and reads the answer in seconds.
- **The library.** It holds the SQL read, batching, retries, the content cache, provenance and
  quote checking. Notebooks and course material can call it directly, as the CSOL 208 keys
  call Jev now.

### Pluggable models

**`text-query` hard-wires no model.** Every model is an endpoint and a token, configured by the
deployment or supplied per request.

- **Decision model:** any service that accepts the Jev request body, `state` plus named
  `noul`, `choice` and `score` questions, and returns per-question probabilities. Jev on
  OpenRouter (`https://openrouter.ai/api/v1/systemone`, `~typesafe/jev-latest`), Laya on
  the NRP course server and Kev (`https://kev.carlboettiger.info/v1/systemone`, `kev-latest`)
  are all of this kind today.
- **Extraction model:** any OpenAI-compatible chat endpoint with structured output, for
  example DeepSeek V4 Flash on OpenRouter or an open-weights model on NRP.
- **Embedding model, if used:** any OpenAI-compatible embeddings endpoint.
- **Configuration:** each model has `endpoint`, `model` and a token. A deployment sets defaults
  in its environment. A request may override them where the deployment allows it. Coded
  outputs record which endpoint and model produced them, so a table coded with Laya is never
  mistaken for one coded with Jev.

### Tools

| Tool | Purpose |
|---|---|
| `decide(sql, id_column, text_column, questions)` | Runs a Jev codebook over the rows the query returns, up to an interactive limit (about 2,000 rows [verify]), and returns ids with probabilities as a table |
| `submit_decide(...)` and `job_status(job_id)` | The same for a whole corpus. Writes results to an S3 parquet path, which becomes a dataset the SQL tool can join |
| `extract(sql, id_column, text_column, schema)` | Structured extraction with a JSON schema, for names, species, coordinates and years, run only on rows a codebook has already flagged |
| `check_quotes(...)` | Confirms that each extracted quote appears in its source passage. In CSOL 208, 18 of 484 quotes were not found and 20 were edited |

- **A decision model does the classifying.** It returns probabilities for typed questions
  and generates no text: `noul` (P(yes)), `choice` (one label from a list) and `score` (a level
  on an ordered scale). In the CSOL 208 key runs Jev coded 6,900 paragraphs with 14 questions
  in 3.6 minutes for $0.32. Laya's four-level scores collapsed to the middle on the same
  questions, so we start with Jev and keep Laya as a comparison.
- **Cache answers by content.** The key is (model, question text, passage text). Repeated
  questions then cost nothing and return the same answer. A deliberate rerun measures
  stability: in CSOL 208 two runs gave 2,337 and 2,330 candidates above 0.5.
- **Coded outputs are datasets.** The question text, its hash, the model and version and the
  run date go in the parquet's key-value metadata. A coded table is then as citable and
  auditable as any layer in the catalog.
- **The codebook is data.** It is a YAML or JSON file of named questions, versioned in the
  application repo. Changing a question changes its hash and so creates a new column.

### Authentication

**Authentication is optional at every point, following `geo-query`.** Open is the default;
private is configuration.

| Concern | Open default | Private option |
|---|---|---|
| Who can call the server | anyone | `MCP_AUTH_TOKEN` bearer token, the same middleware as `geo-query` |
| Which buckets it reads | public buckets | `s3_key`, `s3_secret`, `s3_endpoint` and `s3_scope` per request, as in the `query` tool of `geo-query`, held for that request only |
| Which models it calls, and whose credits | deployment defaults: an endpoint, a model and a token with a spending cap | the client passes its own endpoint and token per request, as the app already does for chat (`"user_provided": true`) |
| Which catalog it sees | the public catalog | a private catalog by deployment (`STAC_CATALOG_TOKEN`) |

`text-query` is a separate repository and deployment from `geo-query`, though it can share
its `s3config` and auth code. The two scale differently: SQL is bound by CPU and memory, while
codebook calls are bound by the network and the external API. Codebook calls also spend money,
so they need their own rate limits and failure domain.

## Codebook for site assessment

**The codebook has a cheap screening pass over every passage, then a criterion pass over the
substantive ones.** Each question asks about one idea, in exact wording, as CSOL 208 found
works best. The file is `codebooks/bbnj-annex1.yaml` in `bosl-high-seas`, not in `text-query`.

Pass 1, every passage:

| Name | Type | Question |
|---|---|---|
| `content` | noul | Does this paragraph report observations, measurements or analyses, as opposed to references, acknowledgements or figure residue? |
| `site` | choice | Where were the observations in this paragraph made? Labels: a named seamount or gap in the Emperor chain / the chain as a whole / elsewhere in the North Pacific / another ocean region / global synthesis / no location |

Pass 2, passages with `content` > 0.5:

| Name | Type | Question |
|---|---|---|
| `crit_a` … `crit_v` | noul | One per Annex I criterion, phrased as evidence. For example, (c): "Does this paragraph describe spawning, breeding, nursery, feeding or migration by a species in the area?" (q): "Does this paragraph describe a human activity or pressure such as fishing, bycatch, mining, shipping, noise or pollution affecting the area?" |
| `direction` | choice | Does the paragraph support the area's importance, argue against it, or neither? |
| `evidence_type` | choice | Direct observation at the site / repeated survey or time series at the site / model or remote sensing / inference from other regions / review or expert opinion |
| `strength` | score | Four levels, from an anecdote or single record to a replicated quantitative survey |
| `taxon` | choice | Microbes / plankton / mesopelagic fish and squid / demersal fish / corals and sponges / other benthic invertebrates / seabirds / marine mammals / turtles / none |
| `zone` | choice | Epipelagic / mesopelagic / bathypelagic / bathyal seafloor / abyssal / not stated |
| `pressure` | choice | Bottom trawling / other fishing / bycatch / mining / shipping / plastics / noise / climate and acidification / none |

Extraction, on flagged passages only: species names (matched to WoRMS), place names, depths
and sampling years. These yield `occurrences.parquet`, which can be compared directly with
OBIS. Some criteria will be hard to separate in single paragraphs: fragility from
sensitivity, and dependency, representativeness, replication, and adequacy and viability. We
should include them anyway, measure agreement, and drop or merge the ones that fail.

Scaled from the pilot by characters, the whole corpus is about 28,000 passages, about $3 on Jev
and about 50 minutes with 8 workers. GROBID's shorter paragraphs will raise the passage count.

## Data coverage

**We should report evidence and coverage as two separate measures for every site and pillar,
so a low score never hides the fact that nobody has looked.** A first pass on two dimensions
already shows that coverage varies by orders of magnitude and does not move together across
dimensions.

| | Deep-sea dives | OBIS records |
|---|---|---|
| EBSAs with none | 206 of 336 | n/a |
| Spread across EBSAs | top 10 EBSAs hold 9,205 of 13,997 dives | 0.018 to 9.7 per km² (10th to 90th percentile) |
| Emperor chain (`NP_18`) | 47 dives, above 84% of EBSAs per km² | 9,768 records, 0.031 per km², above only 14% of EBSAs |

The OBIS counts use res-6 cells, so boundary cells are counted whole. The Emperor chain has
been well dived but is thin in OBIS. Many of its benthic records are in Russian and Japanese
taxonomic papers in this corpus, not in OBIS. Extracting occurrences from the literature is
therefore also a way to fill an OBIS gap.

Candidate dimensions:

| Dimension | Measure | Source | Status |
|---|---|---|---|
| Visual seafloor exploration | dives per km², share of area within 10 km of a dive | `deep-submergence-dives` | in catalog |
| Biological inventory | records per km², sample coverage or Chao1 completeness, phyla sampled | `obis-derived` | in catalog |
| Recency | years since the last OBIS record and the last dive | both above | in catalog |
| Depth representation | share of records by depth zone against share of seafloor by depth zone | OBIS depth, `gebco-2025` | to compute |
| Seafloor mapping | share of cells with direct multibeam soundings | GEBCO type identifier grid | check whether our `gebco-2025` holds it |
| Water column sampling | profiles per km² | World Ocean Database, Argo, WOA23 observation counts | to add |
| Literature | geoparsed works per EBSA | OpenAlex abstracts and CBD EBSA descriptions, through the same pipeline | to add |
| Expert-declared gaps | criteria rated "no information" | `ebsa` `Crit_*` columns, 203 sites | in catalog |

- **Score and coverage are separate axes.** A site can be high on biodiversity with good
  coverage, high with poor coverage, or low because it is unsampled. The leaderboard should be
  able to show each quadrant.
- **Exploration priority** combines predicted value with poor coverage. Predicted value comes
  from proxies with global coverage (geomorphology, productivity, carbon flux, temperature and
  oxygen), and coverage from the table above. Sites predicted to be important but rarely
  sampled are where ship time reduces the most uncertainty.
- **Proxies can be circular.** Bio-ORACLE and species distribution models are themselves fitted
  to biased sampling. We should prefer physical proxies, and state the risk where we cannot.
- **Absence of evidence is recorded as such.** The explorer already separates NULL from a
  measured 0. Coverage makes that distinction visible to the reader.
- **Literature has its own biases.** These include language (OpenAlex records the language of
  each work), the nationality of the research fleet and access to the site. The Korean,
  Russian and Japanese sources in this corpus are a reminder.

## Example interactions

**These six interactions are the first examples to draft.** They run from the Emperor chain
outward, and each one uses only `geo-query`, `text-query` and coded tables.

1. **Life-history importance at the Emperor chain.** The user asks: "Does the Emperor Seamount
   Chain meet criterion (c)?" The agent selects passages located in `NP_18` with
   `crit_c > 0.5` and groups them by taxon and evidence type. It then puts these beside the
   spatial layers: MegaMove important areas, corridors and residencies. It reports the
   evidence it found and the taxa with none. A follow-up such as "is there evidence of
   armorhead spawning?" becomes a new `decide` call over a few hundred candidates, and the
   agent quotes the top passages after `check_quotes`.
2. **A drawn polygon around the Main Gap.** Watling et al. 2024 describe the Main and Small
   Gaps as a biogeographic boundary for bathyal fauna. The agent assembles evidence on
   uniqueness (a), representativeness (j) and connectivity (m) from the literature, with
   abyssal-current papers for the physical mechanism. It adds geomorphology and dive coverage
   from the catalog, and reports whether a polygon that splits at the gap would cover both
   faunas.
3. **Pressures and existing measures for Article 19(4)(c) and Annex I (q) and (v).** Literature
   on bottom trawling, armorhead stock collapse, longline bycatch and plastics meets GFW
   fishing effort, vessel density and the FAO VME bottom-fishing closures. Where the two
   disagree, the agent says so. An example is a pressure documented in papers but not visible
   in AIS.
4. **A proposal checklist.** For any EBSA or polygon, the app produces a table with one row per
   Article 19(4) element and Annex I criterion. Each row gives the evidence count by type and
   strength, the strongest three citations and the coverage on each data dimension. Rows with
   no evidence are listed explicitly. This becomes the scaffold for a proposal or a gap
   analysis.
5. **How well studied is the site.** The user asks: "How does the Emperor chain compare with
   other North Pacific seamount EBSAs?" The app returns the coverage profile across the
   dimensions above with percentiles. Today it would show many dives but few OBIS records. It
   also reports which criteria rest on evidence from elsewhere: mid-water nekton and carbon
   flux.
6. **Where the next expedition should go.** The user asks: "Which high-seas EBSAs are predicted
   to matter for seafloor habitats but have the least direct observation?" The app ranks
   sites by predicted value against coverage and shows them on the map.

## Explorer

**The explorer needs a coverage view next to each pillar score, and an exploration ranking.**
Features belong in glen-charts, so these are requests there; `bosl-high-seas` adds only the SQL
and configuration.

- Each pillar card gets a coverage percentile beside its score.
- A score-against-coverage scatter shows the selected EBSA among all 336.
- A leaderboard view ranks by exploration priority.
- An evidence card on each EBSA profile shows the `Crit_*` ratings (where they exist) and the
  literature counts by criterion, once the literature covers more than one site.

## Scaling beyond one site

**A deep dossier for one site cannot rank 336, so the comparative layer must come from
sources with global reach.** The Emperor corpus is the gold standard for testing the
codebook and the interactions. The general-purpose pipeline is what makes the next corpora
cheap.

- The CBD EBSA descriptions cover all 336 sites in a consistent format, with criteria tables
  and references. They are the obvious second corpus.
- OpenAlex abstracts, geoparsed and coded with the same codebook, give a literature density
  for every EBSA.
- Dossiers for other candidate sites (e.g. the Sargasso Sea, the Salas y Gómez and Nazca
  ridges, the Thermal Dome) would enter by the same pipeline.

## Phases

**The order follows dependencies: first a processed corpus, then a coded table we trust, then
the services and applications.** Phases 1 and 2 can overlap once the passage schema is fixed.

0. **Pilot.** Done on 2026-10-27 for 12 papers on Laya and Jev; see Pilot results. Still to do:
   a person checks the 48 reference labels and extends them to about 100 passages, reporting
   recall on the "yes" cases, not only overall agreement, which easy "no" cases inflate. The
   codebook wording for (n) and (t) should be sharpened and rerun.
1. **Corpus processing.** Build the stages above as cluster jobs in `corpus-ingest`, with
   provenance, checks, Croissant and a thin STAC record. Run them on `high-seas-lit`, then on
   the CBD EBSA descriptions as the first test of generality.
2. **Text query tool.** Build `decide`, `submit_decide`, `extract` and `check_quotes` in
   `text-query`, with the content cache and optional token, S3 and model-key authentication. Run the codebook
   over the full corpus as a batch job, and publish the coded tables to `public-high-seas`.
3. **Coverage metrics.** Compute the coverage dimensions for all 336 EBSAs with `geo-query`,
   and add them to the explorer as a second axis on every pillar.
4. **Applications.** Give the chat app both tools and a system-prompt section on the coded
   tables. Passage text goes to the private instance, which passes the bucket credentials;
   the public app sees coded tables and citations.
5. **Evaluation.** Add the six example interactions to `geo-agent-benchmark` with expected
   answers. Rerun Jev on a sample to measure stability.

## Pilot results

**On 1,534 passages from 12 papers, Jev was clearly better than Laya on every measure except
false positives on the criteria. We will use Jev for coding and keep Laya as a free comparison.**
The scripts are in `pilot/`; inputs and outputs are in `s3://high-seas-lit/pilot/2026-10-27/`. The reference labels are
Claude's, written blind to both models on 48 passages (4 per paper); a person should check them.

| | Laya | Jev |
|---|---|---|
| Time and cost | 406 s, free | 163 s, $0.17 |
| Site label correct | 37% | 74% |
| Taxon correct | 44% | 81% |
| Criteria a, c, i, n, q found (recall) | 9 of 31 | 29 of 31 |
| Criteria flags that were right (precision) | 9 of 15 | 29 of 52 |
| `strength` score spread (SD on a 0–3 scale) | 0.22 | 0.73 |

- **Laya's scores collapse.** Its `score` answers sit at the midpoint, as in CSOL 208, and its
  yes/no answers rarely pass 0.5. It also reads any seamount as an Emperor seamount: it placed
  70 passages of an Azores paper on the chain.
- **Jev over-flags, but its errors are near misses.** At a 0.7 threshold its false positives
  roughly halve with little loss of recall. Three apparent false positives were errors in the
  reference labels, which were made from the first 520 characters while Jev saw whole passages.
  `crit_t_replication` and `crit_n_processes` fire too often and need sharper wording.
- **Location needs the document.** A passage alone rarely names its place. Prefixing the paper
  title raised Jev's site accuracy sharply, but the places layer should still come from
  extracted names matched to a gazetteer, with the decision model as a cross-check.
- **Extraction quality matters as much as the model.** PyMuPDF blocks gave passages of up to
  1,900 characters mixing several ideas, let a download footer and a table of contents
  through, and lost the body text of one paper. Two PDFs carried useless embedded titles. These
  are the jobs of GROBID and the metadata stage.

### Kev comparison

**On 2026-10-28 we coded the same 1,534 passages with Kev, a free self-hosted decision model
(`kev-latest`, a 4B pointer head on Qwen3.5-4B-Base, `jaredpalmer/kev-4b@v1.0`). Kev lies
between Laya and Jev and much closer to Jev, except on location.** Jev was not rerun: Kev is
compared with the stored Jev and Laya answers and the same 48 reference labels. The script is
`pilot/compare.py`; Kev's codes were not kept, and `pilot/README.md` shows how to rerun them.

| | Laya | Kev | Jev |
|---|---|---|---|
| Time and cost | 406 s, free, batched | 1,011 s, free, 8 requests at a time | 163 s, $0.17 |
| Site label correct | 37% | 49% | 74% |
| Taxon correct | 44% | 70% | 81% |
| Criteria recall at P > 0.5 | 9 of 31 | 25 of 31 | 29 of 31 |
| Criteria precision at P > 0.5 | 9 of 15 | 25 of 45 | 29 of 52 |
| Criteria recall at P > 0.7 | 3 of 31 | 17 of 31 | 27 of 31 |
| `strength` score spread (SD on a 0–3 scale) | 0.20 | 0.47 | 0.73 |
| Correlation with Jev on criteria, all passages | 0.37 | 0.85 | |
| Site agreement with Jev, Emperor feature and chain merged | 64% | 79% | |

- **Both Jev and Kev are deterministic.** The full run recoded the pilot passages with Jev, and
  the two Jev runs agree on 97–99% of labels and score identically on the reference labels.
  A rerun of 200 passages on Kev changed no label or threshold call, and no probability by more
  than 0.005. The differences between the models are therefore real, not noise.
- **Kev tracks Jev on the criteria.** Its per-criterion correlation with Jev is 0.77–0.95 for 19
  of the 22 criteria. It over-fires less on `crit_n_processes` (17% of passages above 0.7,
  against 28%) and `crit_t_replication` (10% against 16%), but its probabilities reach 0.7 less
  often, so 0.5 is the better threshold for Kev.
- **Kev places too much on the Emperor chain.** It puts 174 passages on the chain that Jev puts
  elsewhere, and 25 the other way, including 43 of 81 passages of a paper that Jev places off the
  chain. It also prefers `emperor_feature` where Jev picks `emperor_chain`.
- **Kev is free but slower.** It has no batch route, so the full corpus would take about 2.5 hours
  at this concurrency, against 20 minutes and $1.53 for Jev.

**Jev remains the default decision model.** Kev is a reasonable choice for preprocessing where
speed does not matter, and for GLEN text deployments that need a free option. Laya is no longer
needed as the free comparison.

## Decisions for Carl

- Who holds the full dossier outline and the missing sections?

Decided:

- Coded tables, bibliographic metadata and places are public. Passage text stays in the
  private bucket.
- Every service is open by default, with authentication as an option.
- Places use H3 res-5.
- Data coverage is a second axis on every pillar, not a separate theme.
- Neither the corpus nor the data is final. Both will keep growing, so every build is a snapshot
  and every pipeline is incremental.
- Jev is the default decision model. Kev is the free option, for preprocessing where speed does
  not matter and for GLEN text deployments that need one (Kev comparison, 2026-10-28).
- New repositories in the SchmidtDSE organisation: `corpus-ingest`, `corpus-workflows` and
  `text-query`. Existing repositories will be renamed when they migrate: `cng-datasets` to
  `geo-ingest`, `data-workflows` to `geo-workflows` and `mcp-data-server` to `geo-query`.
- Corpora are described with Croissant, CSL-JSON and a README and `AGENTS.md`, with a thin STAC
  record for discovery. Spatial metadata follows Portolan.
- GROBID runs as a cluster service, deployed from the corpus processing repository.
- Models are pluggable endpoints with tokens. Jev, Kev and Laya are interchangeable decision models.
- The design serves any GLEN app; high seas is the first use case.
