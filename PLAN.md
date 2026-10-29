# Text stack for GLEN applications

Working plan, begun 2026-10-27 in `boettiger-lab/bosl-high-seas` and moved here. Status: draft
for discussion. Numbers marked [verify] are estimates. The first application is BBNJ site
assessment in the High Seas app (`boettiger-lab/bosl-high-seas`); the stack itself is meant
for any document corpus.

## Goal

**We want an agent in any GLEN app to answer questions from a collection of documents as
readily as it answers them from spatial data, with citations, and to say how much the
documents cover.** The apps already answer spatial questions through SQL over cloud-native
data. This plan adds the text half: processing a corpus into AI-ready tables, coding it with
typed questions, and joining the results to the same H3 grid and catalog as every other layer.

The corpora we have in view differ in subject, structure and licence:

- **Scientific literature on a place or a theme.** A dossier on the Emperor Seamount Chain for
  the High Seas app is the first. Terrestrial conservation research for the 30x30 app is a
  likely second.
- **Grey literature.** Agency reports, management plans, expedition reports and the CBD EBSA
  site descriptions.
- **Legal and policy documents.** Treaties, statutes, regulations, national biodiversity
  strategies and protected-area management plans.
- **Course and research corpora,** such as the corporate reports coded in CSOL 208.

Three questions recur across all of them. What do the documents say about a question? Where
does each statement apply? How well do the documents cover the places and topics a user cares
about? The stack answers the first two with codebooks and places, and the third with coverage
measures beside every score, so that a low score never hides the fact that nobody has looked.

## Design

**The design mirrors the spatial stack, one repository per role.** Names give the kind of
data and the role, follow the open standards underneath rather than a brand or a transport,
and keep the GLEN name for front ends. Each component is open by default with authentication
as an option.

| Role | Spatial and tabular data | Text corpora |
|---|---|---|
| Builder | `geo-ingest` (now `cng-datasets`): source files to GeoParquet, H3 hex, PMTiles and COG | `text-ingest`: documents to passage tables, bibliographic records and H3 places |
| Workflows | `geo-workflows` (now `data-workflows`): one recipe and one issue per dataset | `text-workflows`: one recipe and one issue per corpus, and per coded run |
| Resource metadata | STAC, following Portolan | Croissant and CSL-JSON, with a thin STAC record for discovery |
| Query tool | `geo-query` (now `mcp-data-server`): SQL over S3 parquet, tuned for H3 joins | `text-query`: codebooks and structured extraction over any text column a SQL query returns |
| Front end | geo-agent chat apps and the glen-charts explorer | the same front ends |

The layers connect through S3. Builders write AI-ready parquet. `text-query` reads it and writes
coded tables back as new datasets. `geo-query` then joins those to the H3 grid like any other
layer.

**Nothing in the stack knows about a particular application.** What is specific to an app is
configuration that the app or the corpus recipe supplies:

| Supplied by | Examples |
|---|---|
| Corpus recipe in `text-workflows` | sources, scope or outline, access, licence policy, languages, document kind, gazetteers |
| Codebook in the application repository | BBNJ Annex I criteria; conservation interventions and outcomes; obligations in a statute |
| Application configuration | which corpora and coded tables the agent sees, system-prompt guidance, the spatial units it reports on |
| Deployment | model endpoints and tokens, bucket credentials |

An app that today answers questions only from SQL-queried data can add a corpus the same way it
adds a layer: process it with `text-ingest`, list it in its catalog and give the agent
`text-query`. Models are endpoints, corpora are catalog entries and codebooks are files.

We build around the high-seas case because a concrete use keeps the design honest. The second
corpus should be of a different kind, terrestrial or legal, so that anything we hard-wired for
the first shows up early.

## Document kinds

**One pipeline handles several kinds of document, with a structure parser and a metadata source
chosen per kind.** The rest of the pipeline, from inventory to publishing, is the same.

| Kind | Structure | Bibliographic record | Location cues |
|---|---|---|---|
| Scholarly papers | title, abstract, sections, paragraphs, references; GROBID is built for these | DOI, resolved through Crossref and OpenAlex | study sites, coordinates, place names in methods and results |
| Reports and grey literature | headings and paragraphs, often with tables and figures; a general layout parser such as Docling [verify] | often no DOI; title, issuing body, year, report number | the area the report covers, named sites |
| Legal and policy documents | a hierarchy of parts, articles, sections and clauses; often available as HTML or XML (Akoma Ntoso, USLM) rather than only PDF | jurisdiction, instrument type, enactment and effective dates, amendments and versions | the jurisdiction, and the places or areas the provisions name |
| Scanned archives | OCR first, then one of the above | as above, often entered by hand | as above |

- **The passage is the unit everywhere.** For a paper it is a paragraph; for a statute it is
  the smallest provision, such as a clause or subsection, with its full path (article,
  section, clause) kept as a column. Codebooks and citations work the same way for both.
- **CSL-JSON covers these kinds.** It has types for articles, reports, legislation, bills and
  legal cases, so one `documents` table holds them all.
- **Versions matter for legal text.** A statute is amended, so a legal corpus records the
  version and its effective dates, and a snapshot pins them.

## Location

**Location is resolved at three levels, and only the first two are part of the stack.** The
pilot showed that a paragraph alone rarely names its place, and that much of the evidence in a
site dossier comes from other regions.

1. **Places.** `text-ingest` finds place names and coordinates in each passage, matches them to
   gazetteers and stores the result as H3 cells with a precision class: point, named feature,
   administrative or protected area, region, or global. A place with an area becomes the set
   of cells it covers. This is general: it needs only gazetteers.
2. **Document location.** Each document gets the places of its study area, from its abstract,
   methods and title. A passage without a place, such as a methods paragraph, can then inherit
   its document's location, flagged as inherited.
3. **Scope of a statement.** Whether a passage reports a finding at its place, applies a finding
   from elsewhere by analogy, or states a general result is a question for the codebook, not
   the gazetteer. A general reusable question (`scope`: site-specific, regional, general)
   lets an agent separate direct evidence for a place from general knowledge that may
   transfer to it. Deciding whether it does transfer stays with the user, and the agent
   reports the two separately.

Gazetteers are chosen per corpus in the recipe:

| Domain | Candidate gazetteers |
|---|---|
| Any | GeoNames; Overture or Who's On First administrative areas; coordinate patterns in the text |
| Marine | Marine Regions; GEBCO Gazetteer of Undersea Feature Names; EBSA and MPA boundaries |
| Terrestrial conservation | WDPA; PAD-US and other national protected-area databases; ecoregions |
| Legal and policy | the jurisdiction's own boundaries; areas the instrument designates |

- **The resolution is a recipe setting.** The high-seas corpus uses H3 res-5 (about 250 km²),
  coarse enough for named seamounts. A terrestrial corpus about individual reserves may need a
  finer resolution.
- **Coarse labels from the codebook are a cross-check.** An application may also ask the
  decision model where a passage's observations were made, as the BBNJ codebook does with
  `site`. These labels are fast and cheap, but they are not coordinates, and they inherit the
  model's biases: Kev, for example, places too much on the Emperor chain.
- **Places that fall where they cannot be** (on land for a marine corpus, at sea for a
  terrestrial one) are flagged by the checks.

## Corpus processing

**Corpus processing should be a pipeline of idempotent cluster jobs that turn a collection of
documents into cloud-native tables with complete metadata, in the same spirit as
`geo-ingest`.** The same command should process a scientific dossier, a set of agency reports
or a body of legislation.

### Stages

| Stage | What it does | Tools | Output |
|---|---|---|---|
| Inventory | Lists every object, hashes it, records original path and folder | `rclone`, sha256 | `manifest.parquet`: path, folder, sha256, bytes, media type |
| Deduplication | Collapses identical files to one document, keeping every path and folder as a list; flags near-duplicates (same DOI, same first-page text, a preprint and its published version) | sha256, then text similarity | `doc_id` = content hash; `paths[]`, `sections[]` |
| Text layer check | Decides per page, not per file, whether the page needs OCR | PyMuPDF character counts | page flags |
| OCR | Adds a text layer to scanned pages, in the recipe's languages | OCRmyPDF (Tesseract) | OCR'd PDF stored next to the original, never replacing it |
| Structure | Extracts title, authors, sections and passages with page numbers, and parsed references, with a parser chosen by document kind | GROBID for scholarly papers; a layout parser for reports; the source's own markup for legal XML and HTML; PyMuPDF as fallback | `passages.parquet`, `references.parquet` |
| Metadata | Completes the bibliographic record; detects language; records licence and access status | Crossref, OpenAlex and Unpaywall for scholarly work; the issuing body or legislative source otherwise | `documents.parquet` |
| Places | Finds place names and coordinates in each passage and document, matches them to the recipe's gazetteers, assigns H3 cells with a precision class | gazetteers from the recipe, coordinate patterns, an extraction model for names | `places.parquet` |
| Search index | Optional full-text and embedding indexes over passages | DuckDB FTS; an open-weights embedding model on NRP | index files or an embedding column |
| Publish | Validates the outputs, writes the corpus description and a thin STAC record | `mlcroissant` validation, the corpus checks below | `croissant.json`, README, `AGENTS.md`, `stac-collection.json` |

- **Async and resumable.** Each stage is an indexed Kubernetes Job with one document or a batch
  of documents per index. Outputs are keyed by content hash, so a rerun skips finished work
  and a new document dropped into the bucket is processed incrementally.
- **Provenance in the file.** Every parquet carries the tool version, stage, OCR engine,
  parser version and build time in its key-value metadata, as `cng_datasets/provenance.py`
  does. A bad OCR or parse can then be traced to every table it touched.
- **Checks before publish,** as in `hex_checks.py`: the share of pages with text after OCR,
  passages per page, unresolved identifiers, duplicates and implausible places.
- **Originals are never modified.** The original folder layout stays as uploaded. Everything
  derived goes under `derived/<snapshot>/`, keyed by `doc_id`.
- **Snapshots are frozen.** Coded tables cite passage ids, so each build is an immutable
  snapshot named by date. A passage id is a hash of the document, its position and its text,
  so ids survive when documents are added and a rebuild makes a new snapshot.
- **Small row groups.** Passage text is wide, so the parquet should use small row groups for
  fast range reads, as the data-workflows serialisation standard already requires.

### Output layout

```
s3://<corpus-bucket>/
  <original folders>/                         source files, unchanged
  README.md                                   what the corpus is, its scope, caveats and licences
  AGENTS.md                                   how an agent should use it, and what it must not do
  croissant.json                              tables, columns, files, licence (current snapshot)
  stac-collection.json                        thin discovery record pointing to croissant.json
  derived/<snapshot>/
    manifest.parquet       path, folder, sha256, bytes, media_type
    pdf-ocr/<doc_id>.pdf   OCR'd copies of scanned documents
    structure/<doc_id>.*   the parser's structured form of each document (TEI for GROBID)
    documents.parquet      doc_id, paths[], sections[], type, identifiers, title, authors or
                           issuing body, year, container, abstract, language, licence,
                           access, pages, text_source, and for legal text jurisdiction,
                           version and effective dates
    passages.parquet       passage_id, doc_id, section_path, page, ordinal, text, n_chars
    references.parquet     doc_id, cited identifier, cited_title, cited_year
    places.parquet         passage_id or doc_id, place_name, gazetteer, gazetteer_id,
                           precision, inherited, h3 cells at the recipe's resolution
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
- **The structured form of each document** is kept: TEI XML from GROBID, or the source markup
  for legal text.
- **README and `AGENTS.md`** sit at the corpus root. This is Portolan's rule for catalogs and is
  just as useful here. They say what the corpus covers, where it is thin, the licence policy
  and what an agent must not do with passage text.
- **A thin STAC collection** points to `croissant.json`, so `geo-query` and the agents find a
  corpus the same way they find everything else. A private corpus is listed in a private
  catalog (`STAC_CATALOG_TOKEN`).
- **Derived spatial products are ordinary STAC collections.** The H3 places and the coded
  tables joined to the grid are published in the application's public bucket like any other
  layer, and link back to the corpus snapshot they came from.

### Workflows

**Corpora get their own workflows repository, `text-workflows`, parallel to
`data-workflows`.** It has the same discipline: scope in the issue, cluster jobs, provenance,
and outputs published to S3 with their metadata kept in the bucket, not the repository.

```
text-workflows/
  AGENTS.md                         scope, licence and publication rules
  .github/ISSUE_TEMPLATE/
    corpus.yml                      sources, scope or outline, access, licence policy, curator,
                                    languages, document kind
    coded-run.yml                   corpus snapshot, codebook, model, output
  corpora/<corpus>/
    corpus.yaml                     sources (bucket prefix, DOI list, OpenAlex query, Zotero group,
                                    legislative source), outline, access, document kind, OCR
                                    languages, gazetteers and H3 resolution
    k8s/                            generated by text-ingest
  coded/<corpus>--<codebook>/
    run.yaml                        corpus snapshot, codebook file and commit,
                                    model endpoint (no token), output path
```

- **Codebook files live in the application repository,** for example
  `bosl-high-seas/codebooks/bbnj-annex1.yaml`, because they encode domain judgment and change
  with the app. A coded run pins one by commit, so every published coded table traces to an
  exact question set, corpus snapshot and model.
- **Curators work on S3; scope lives in issues.** Domain partners add documents to the bucket.
  The issue records what the corpus is meant to cover, such as a dossier outline and its empty
  sections, and a rebuild produces a new snapshot.

### Agent guidance

**Guidance about how a tool works ships with the tool. Guidance about what we publish and how
we decide stays in the workflows repository.** Tool knowledge then changes with the code it
describes, which is the pattern of Portolan's bootstrap skill.

| Guidance | Home |
|---|---|
| Scope in issues, publication boundaries, licence policy, worked recipes | workflows repository (`data-workflows`, `text-workflows`) |
| How the builder behaves: hex tuning, raster hexing, job troubleshooting; OCR, parsers, segmentation and gazetteers for corpora | builder repository (`geo-ingest`, `text-ingest`) |
| Writing codebooks: one idea per question, exact wording, labels with descriptions, measuring recall on the "yes" cases | `text-query` |
| Cluster operations: NRP usage policy, preemption, Armada, S3 endpoints | one shared NRP skill set used by both builders, not copied into each |
| Spatial metadata | Portolan's conventions and validator, replacing much of `stac-authoring` |

For `data-workflows` this means `hex-tuning`, `raster-hexing` and most of
`job-troubleshooting` move to `cng-datasets`. `armada-pipeline` and `pod-preemption` move to
the shared NRP set, and `stac-authoring` is reconciled with Portolan. For the text side we
start with this split rather than migrating to it later.

## Text query tool

**`text-query` should be as generic for text as `geo-query` is for tables.** Any SQL query that
returns an id column and a text column can be coded: passages of a corpus, the CBD EBSA
descriptions, OpenAlex abstracts, dataset descriptions in a STAC catalog, provisions of a
statute, or the corporate reports in CSOL 208.

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
  outputs record which endpoint and model produced them, so a table coded with Kev is never
  mistaken for one coded with Jev.

### Tools

| Tool | Purpose |
|---|---|
| `decide(sql, id_column, text_column, questions)` | Runs a codebook over the rows the query returns, up to an interactive limit (about 2,000 rows [verify]), and returns ids with probabilities as a table |
| `submit_decide(...)` and `job_status(job_id)` | The same for a whole corpus. Writes results to an S3 parquet path, which becomes a dataset the SQL tool can join |
| `extract(sql, id_column, text_column, schema)` | Structured extraction with a JSON schema, for names, species, places, dates and quantities, run only on rows a codebook has already flagged |
| `check_quotes(...)` | Confirms that each extracted quote appears in its source passage. In CSOL 208, 18 of 484 quotes were not found and 20 were edited |

- **A decision model does the classifying.** It returns probabilities for typed questions
  and generates no text: `noul` (P(yes)), `choice` (one label from a list) and `score` (a level
  on an ordered scale). In the CSOL 208 key runs Jev coded 6,900 paragraphs with 14 questions
  in 3.6 minutes for $0.32.
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

## Codebooks

**A codebook has a cheap screening pass over every passage, then a topic pass over the
passages that matter.** Each question asks about one idea, in exact wording, as CSOL 208 found
works best. The topic questions are the application's; a set of general questions can be
reused across applications.

| Question | Type | Use |
|---|---|---|
| `content` | noul | Does the passage carry substance (findings, provisions, analysis) rather than references, boilerplate or figure residue? |
| `scope` | choice | Is the statement specific to the place studied, regional, or general? |
| `evidence_type` | choice | Direct observation, repeated survey, model or remote sensing, findings from elsewhere applied by analogy, review or opinion, none |
| `direction` | choice | Does the passage support, weaken or say nothing about the claim of interest? |
| `strength` | score | From an anecdote or single record to a replicated quantitative study |

- **Topic questions come from the application's framework.** The BBNJ Annex I criteria for the
  high seas; for conservation research, perhaps the intervention, the outcome measured and
  the ecosystem; for legal text, perhaps whether a provision creates an obligation, a
  permission or a prohibition, and for whom.
- **Measure before trusting.** A person labels a stratified sample with "yes" cases for every
  question, and each codebook reports recall on those cases and precision at the threshold it
  uses. Questions that cannot be separated in single passages are merged or dropped.
- **Extraction follows coding.** Names, species (matched to a taxonomy such as WoRMS or GBIF),
  places, dates and quantities are extracted only from passages a codebook has flagged.

## Coverage

**Every application should report evidence and coverage as separate measures, so that a low
score never hides the fact that nobody has looked.** Coverage of the literature is one
dimension among several; the others come from the spatial catalog.

- **Score and coverage are separate axes.** A place can score high with good coverage, high
  with poor coverage, or low because it is unstudied. Views should be able to show each case.
- **Literature coverage is computed from places.** Documents and passages per H3 cell or per
  assessment unit, by topic, once the corpus is geolocated.
- **Absence of evidence is recorded as such.** A missing value is never shown as a measured 0.
- **Corpora have their own biases.** These include language, the nationality of the research
  effort, access to the site, and which documents a curator chose to include. Recipes record
  the selection, and coverage measures say what the corpus holds, not what exists.

## Applications

### High Seas

**A user proposes a high-seas area and sees, criterion by criterion, what evidence supports it,
how strong that evidence is, and how much is simply unknown.** The app already answers the
spatial half through the DuckDB MCP server; the text stack adds the literature.

- The unit of assessment is either an existing EBSA (`GLOBAL_ID`) or a drawn polygon, both
  reduced to H3 cells as the explorer already does.
- The criteria are the 22 indicative criteria of BBNJ Annex I, (a) uniqueness to
  (v) existing conservation and management measures. Article 19(4) lists what a proposal must
  contain, including (b) information on the criteria, (c) human activities and (d) the state
  of the marine environment.
- The data-poverty question has equal weight: without it, priority areas become the
  best-studied areas.

#### Emperor Seamount Chain corpus

**The first corpus is a dossier on one site, the Emperor Seamount Chain, organised by the
sections of a site description.** "ESC" in the original zip name is the Emperor Seamount Chain,
and it matches EBSA `NP_18`, "Emperor Seamount Chain and Northern Hawaiian Ridge", 310,271 km².
Its recipe is `corpora/high-seas-lit/corpus.yaml`.

- It is stored in the private bucket `high-seas-lit`, one prefix per original folder:
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
  which is why location and scope matter.
- `6.Chemical oceanography/Kassem and Shamberger, 2026_Data file.csv` is a station-level
  bottle dataset (cruise KM2212, 2022) that belongs in the spatial catalog as point data. The
  Korean `참고문헌 링크.docx` ("reference links") may list more sources.
- Places use Marine Regions and the GEBCO undersea feature gazetteer at H3 res-5.

A prototype snapshot of 14,513 passages from 186 PDFs, made with the pilot's PyMuPDF script and
coded with Jev, runs in the private High Seas app through a prototype of `text-query`. The
walkthrough is `docs/text-query-walkthrough.md` in `bosl-high-seas`.

#### BBNJ codebook

**The codebook is `codebooks/bbnj-annex1.yaml` in `bosl-high-seas`.** It follows the general
pattern: a screening pass over every passage, then the criteria over the substantive ones.

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

- **`site` is specific to this corpus.** It is the coarse location label described under
  Location. In the full run, most papers mix several labels, for good reason: introductions
  cite global work, results report the site and discussions compare with elsewhere. The
  general `scope` question is not yet in this codebook.
- **Extraction, on flagged passages only:** species names (matched to WoRMS), place names,
  depths and sampling years. These yield `occurrences.parquet`, which can be compared
  directly with OBIS.
- **Some criteria will be hard to separate in single paragraphs:** fragility from sensitivity,
  and dependency, representativeness, replication, and adequacy and viability. We should
  include them anyway, measure agreement, and drop or merge the ones that fail.

#### Data coverage for EBSAs

A first pass on two dimensions already shows that coverage varies by orders of magnitude and
does not move together across dimensions.

| | Deep-sea dives | OBIS records |
|---|---|---|
| EBSAs with none | 206 of 336 | n/a |
| Spread across EBSAs | top 10 EBSAs hold 9,205 of 13,997 dives | 0.018 to 9.7 per km² (10th to 90th percentile) |
| Emperor chain (`NP_18`) | 47 dives, above 84% of EBSAs per km² | 9,768 records, 0.031 per km², above only 14% of EBSAs |

The OBIS counts use res-6 cells, so boundary cells are counted whole. The Emperor chain has
been well dived but is thin in OBIS. Many of its benthic records are in Russian and Japanese
taxonomic papers in this corpus, not in OBIS. Extracting occurrences from the literature is
therefore also a way to fill an OBIS gap.

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

- **Exploration priority** combines predicted value with poor coverage. Predicted value comes
  from proxies with global coverage (geomorphology, productivity, carbon flux, temperature and
  oxygen), and coverage from the table above. Sites predicted to be important but rarely
  sampled are where ship time reduces the most uncertainty.
- **Proxies can be circular.** Bio-ORACLE and species distribution models are themselves fitted
  to biased sampling. We should prefer physical proxies, and state the risk where we cannot.
- **The explorer needs a coverage view next to each pillar score.** Features belong in
  glen-charts, so these are requests there; `bosl-high-seas` adds only the SQL and
  configuration. Each pillar card gets a coverage percentile beside its score; a
  score-against-coverage scatter shows the selected EBSA among all 336; a leaderboard ranks by
  exploration priority; and an evidence card shows the `Crit_*` ratings and the literature
  counts by criterion, once the literature covers more than one site.

#### Example interactions

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

#### Other sites

**A deep dossier for one site cannot rank 336, so the comparative layer must come from
sources with global reach.** The Emperor corpus is the test bed for the codebook and the
interactions.

- The CBD EBSA descriptions cover all 336 sites in a consistent format, with criteria tables
  and references.
- OpenAlex abstracts, geoparsed and coded with the same codebook, give a literature density
  for every EBSA.
- Dossiers for other candidate sites (e.g. the Sargasso Sea, the Salas y Gómez and Nazca
  ridges, the Thermal Dome) would enter by the same pipeline.

### Terrestrial conservation

**The 30x30 app could add a corpus of conservation research in the same way.** This is a
candidate, not yet scoped: the corpus, its curator and the questions are for the issue.

- Sources could be an OpenAlex query, a Zotero group or a partner's collection of reports and
  management plans.
- Places would use GeoNames, administrative areas and protected-area databases such as PAD-US
  and WDPA, likely at a finer H3 resolution than the high seas.
- A codebook might ask about the intervention, the outcome measured, the ecosystem and the
  evidence type, and join the coded passages to the app's protected-area and land-cover layers.

### Legal and policy documents

**Statutes, regulations and plans can be coded with the same tools, with provisions as
passages.** This is also a candidate.

- Structure comes from the source markup where it exists, with the article, section and clause
  path kept for citation, and the version and effective dates recorded.
- Location is mostly the jurisdiction and the areas a provision designates.
- A codebook might ask whether a provision creates an obligation, a permission or a
  prohibition, for whom, and about which activity or area. The BBNJ Agreement's own text is a
  natural first test, beside the High Seas app.

## Phases

**The order follows dependencies: first a processed corpus, then a coded table we trust, then
the services and applications.** Phases 1 and 2 can overlap once the passage schema is fixed.

0. **Pilot.** Done on 2026-10-27 for 12 papers of the Emperor corpus on Laya and Jev, and on
   2026-10-28 for Kev; see Pilot results. Still to do: a person checks the 48 reference labels
   and extends them to about 100 passages, reporting recall on the "yes" cases, not only
   overall agreement, which easy "no" cases inflate. The codebook wording for (n) and (t)
   should be sharpened and rerun.
1. **Corpus processing.** Build the stages above as cluster jobs in `text-ingest`, with
   provenance, checks, Croissant and a thin STAC record. Run them on `high-seas-lit`, then on a
   corpus of a different kind, terrestrial or legal, as the first test of generality.
2. **Text query tool.** Build `decide`, `submit_decide`, `extract` and `check_quotes` in
   `text-query`, with the content cache and optional token, S3 and model-key authentication.
   Run the BBNJ codebook over the full Emperor corpus as a batch job, and publish the coded
   tables to `public-high-seas`.
3. **Coverage.** Compute the coverage dimensions for all 336 EBSAs with `geo-query`, and add
   them to the High Seas explorer as a second axis on every pillar.
4. **Applications.** Give the High Seas chat app both tools and a system-prompt section on the
   coded tables. Passage text goes to the private instance, which passes the bucket
   credentials; the public app sees coded tables and citations. Then the second application.
5. **Evaluation.** Add the example interactions to `geo-agent-benchmark` with expected
   answers, and rerun the decision model on a sample to measure stability.

## Pilot results

**On 1,534 passages from 12 papers of the Emperor corpus, Jev was clearly better than Laya on
every measure except false positives on the criteria.** The scripts are in `pilot/`; inputs and
outputs are in `s3://high-seas-lit/pilot/2026-10-27/`. The reference labels are Claude's,
written blind to both models on 48 passages (4 per paper); a person should check them.

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
  title raised Jev's site accuracy sharply, but places should still come from extracted names
  matched to a gazetteer, with the decision model as a cross-check.
- **Extraction quality matters as much as the model.** PyMuPDF blocks gave passages of up to
  1,900 characters mixing several ideas, let a download footer and a table of contents
  through, and lost the body text of one paper. Two PDFs carried useless embedded titles. These
  are the jobs of the structure and metadata stages.

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

- Which corpus comes second, and who curates it: terrestrial conservation research for the
  30x30 app, a legal corpus such as the BBNJ Agreement, or another?
- Who holds the full Emperor dossier outline and the missing sections?

Decided:

- The stack is general: nothing in `text-ingest` or `text-query` is specific to one
  application. Codebooks, gazetteers and scope belong to applications and recipes.
- Coded tables, bibliographic metadata and places are public. Passage text stays in the
  corpus's private bucket when its licence requires it.
- Every service is open by default, with authentication as an option.
- Places are H3 cells, at a resolution set per corpus; the high-seas corpus uses res-5.
- Data coverage is a second axis on every score, not a separate theme.
- Neither the corpus nor the data is final. Both will keep growing, so every build is a snapshot
  and every pipeline is incremental.
- Jev is the default decision model. Kev is the free option, for preprocessing where speed does
  not matter and for GLEN text deployments that need one (Kev comparison, 2026-10-28).
- New repositories in the SchmidtDSE organisation: `text-ingest`, `text-workflows` and
  `text-query`. Existing repositories will be renamed when they migrate: `cng-datasets` to
  `geo-ingest`, `data-workflows` to `geo-workflows` and `mcp-data-server` to `geo-query`.
- Corpora are described with Croissant, CSL-JSON and a README and `AGENTS.md`, with a thin STAC
  record for discovery. Spatial metadata follows Portolan.
- GROBID runs as a cluster service, deployed from `text-ingest`.
- Models are pluggable endpoints with tokens. Jev, Kev and Laya are interchangeable decision models.
- The design serves any GLEN app; high seas is the first use case.
