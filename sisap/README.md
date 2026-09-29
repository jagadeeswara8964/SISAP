# SISAP — Smart Indian Standards Advisor for Procurement

**Problem statement:** SIH26108 — *AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications*
**Theme:** Smart Automation

SISAP helps government departments, PSUs, procurement agencies and organisations analyse tender
documents / product specifications and identify the **applicable Indian Standards** — with an
explainable, evidence-based trail behind every recommendation.

It is **not** a chatbot. It is a standards-recommendation engine:

```
UPLOAD → UNDERSTAND → RECOMMEND → VALIDATE → EXPLAIN → REPORT
```

---

## 1. Project overview

A procurement officer uploads a tender PDF (or pastes the specification text). SISAP:

1. Extracts the document text with PyMuPDF and detects scanned / image-only PDFs.
2. Extracts a **structured requirement object** (product, category, intended use, materials,
   technical, performance, safety, testing, installation and certification requirements).
3. Embeds the requirements and the standards corpus with Sentence-Transformers.
4. Searches the corpus with a **FAISS** inner-product index.
5. Ranks candidates with a **composite score** (never raw cosine similarity).
6. Traverses the **NetworkX** standards relationship graph to pull in testing, safety,
   installation, reference and related standards.
7. **Validates** version, amendment and supersession status against the curated dataset.
8. **Detects specification gaps** and suggests actions.
9. **Explains** every recommendation with stored metadata evidence.
10. Generates a **professional PDF report**.

### Safety / accuracy stance

SISAP provides recommendations, **not legal or regulatory decisions**.

- It never states "this tender is legally compliant". It says
  *"Potentially applicable standards identified. Review required."*
- It never invents standard numbers, BIS certification requirements, amendment dates or official
  titles. Where information is unavailable it says **"Not available in the current dataset."**
- Validation is performed against a **curated demo dataset**. No live BIS verification is claimed;
  every report states `Validation source: Curated demo dataset`.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend — React 19 + TypeScript + Tailwind v4 + React Router       │
│  Recharts (confidence chart) · custom SVG/DOM relationship graph     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  /api (relative, proxied by Vite)
┌───────────────────────────────▼──────────────────────────────────────┐
│  Backend — FastAPI (Python 3.13)                                     │
│                                                                      │
│  api/routes.py ────────────── REST endpoints                         │
│                                                                      │
│  document_processing/   PyMuPDF extraction, cleaning, sections       │
│  recommendation/        RequirementExtractor                         │
│                         StandardRecommendationEngine (composite)     │
│                         SpecificationGapDetector                     │
│  ai/                    EmbeddingService (ST / TF-IDF fallback)      │
│                         VectorStore (FAISS)                          │
│                         LLM provider abstraction (optional)          │
│  graph/                 StandardsGraph (NetworkX MultiDiGraph)       │
│  validation/            StandardsValidator                           │
│  reports/               ReportBuilder (ReportLab PDF)                │
│  services/              Orchestration + repositories                 │
│  database/              SQLite + repository layer                    │
│  schemas/               Pydantic API contract                        │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
  data/standards.json    data/embeddings/         SQLite (sisap.db)
  (curated dataset)      FAISS index + metadata   documents, requirements,
                                                recommendations, gaps
```

The REST layer is decoupled from storage, so **SQLite → PostgreSQL** and
**FAISS → pgvector** can be swapped by re-implementing `database/repositories.py`
and `ai/vector_store.py` without touching the services or the API.

---

## 3. Features

| Area | What it does |
|---|---|
| Upload | PDF upload with type/size validation, sanitised filenames, scanned-document detection |
| Manual input | Paste specification text and analyse it without a PDF |
| Requirement extraction | Product, category, intended use, materials, technical / performance / safety / testing / installation / certification requirements |
| Semantic search | Sentence-Transformers embeddings + FAISS index |
| Ranking | Composite score: semantic 0.45, requirement coverage 0.25, product 0.15, application 0.10, category 0.05 |
| Classification | Primary, Testing, Safety, Reference/Normative, Installation, Terminology, Related |
| Relationship graph | Interactive node/edge graph with typed relationships |
| Validation | Status, version, amendments, supersession, certification (with source attribution) |
| Gap detection | Critical / High / Medium / Low findings with suggested actions |
| Explainability | Evidence-based "why this standard?" plus score component breakdown |
| Reports | 12-section PDF export |
| Dashboard | Live counters, recent analyses, confidence by type, dataset coverage |
| Standards explorer | Search, filter, paginate, standard detail, relationship graph |
| History | Sortable, searchable table of past analyses |
| UX | Toasts, skeleton loaders, empty states, tooltips, modals, responsive tables, keyboard navigation, `prefers-reduced-motion` support |

---

## 4. Technology stack

**Frontend** — React 19, TypeScript, Tailwind CSS v4, React Router 7, Recharts 3, Lucide icons,
Vite 7. UI primitives (`components/ui/*`) follow shadcn/ui conventions (`cn`, variant props,
composable Card/Badge/Modal primitives).

**Backend** — Python 3.13, FastAPI, Uvicorn, Pydantic v2, PyMuPDF, Sentence-Transformers,
FAISS (CPU), scikit-learn, NetworkX, NumPy, ReportLab.

**Storage** — SQLite (WAL mode) for the MVP; FAISS flat inner-product index for vectors.

---

## 5. Installation

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

> **Note on torch:** `sentence-transformers` pulls a large PyTorch wheel. If the default wheel is
> slow to download, install the much smaller CPU build first:
>
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### Frontend

```bash
cd frontend
npm install
```

---

## 6. Environment variables

Copy the templates and adjust as needed. **Every value has a working default — the application runs
fully offline with no configuration at all.**

```bash
cp backend/.env.example .env        # or backend/.env
cp frontend/.env.example frontend/.env.local
```

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | Offline mode: curated standards, local embeddings, rule-based extraction |
| `SISAP_DATA_DIR` | `../data` | Dataset, database and index location |
| `SISAP_UPLOAD_DIR` | `./uploads` | Uploaded file storage |
| `SISAP_REPORTS_DIR` | `../reports` | Generated PDF reports |
| `SISAP_INDEX_DIR` | `../data/embeddings` | FAISS index files |
| `SISAP_MAX_UPLOAD_MB` | `25` | Upload size limit |
| `SISAP_CORS_ORIGINS` | `*` | Allowed browser origins |
| `SISAP_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformer model |
| `SISAP_EMBEDDING_BACKEND` | `auto` | `auto` \| `sentence-transformers` \| `tfidf` |
| `SISAP_LLM_PROVIDER` | `auto` | `auto` \| `anthropic` \| `openai-compatible` |
| `SISAP_LLM_API_KEY` | *(empty)* | Optional LLM key — read server-side only, never exposed to the frontend |
| `SISAP_LLM_MODEL` | `claude-sonnet-4-5` | Optional LLM model name |
| `SISAP_LLM_BASE_URL` | *(empty)* | Optional OpenAI-compatible base URL |
| `VITE_API_TARGET` | `http://127.0.0.1:8000` | Backend target for the Vite dev proxy |

API keys are only ever read by the backend and are never returned by any endpoint.

---

## 7. Running the backend

```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
uvicorn main:app --reload
```

- API root: http://127.0.0.1:8000/
- Interactive docs: http://127.0.0.1:8000/api/docs
- Health check: http://127.0.0.1:8000/api/health

On startup the app loads the dataset into SQLite and loads (or builds) the FAISS index, so the
first request is fast.

## 8. Running the frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend, so all requests
are relative and the frontend never needs to know the backend address.

Production build:

```bash
npm run build      # type-checks then emits frontend/dist
npm run preview
```

---

## 9. Loading the standards dataset

The dataset (`data/standards.json`, **63 standards** across 9 categories) is loaded automatically at
startup. To load or refresh it manually:

```bash
cd backend && source venv/bin/activate
python3 ../scripts/load_standards.py
```

The dataset is marked **Demo / Curated Dataset** throughout. Standard numbers, titles and scope
statements are compiled from publicly available BIS catalogue summaries; edition years, amendment
numbers and status values are **indicative** and must be re-verified against the live BIS catalogue
before any procurement decision.

To extend the dataset, add entries to `scripts/extend_dataset.py` and re-run it — it is idempotent.

## 10. Building the FAISS index

```bash
cd backend && source venv/bin/activate
python3 ../scripts/build_faiss_index.py           # builds only if needed
python3 ../scripts/build_faiss_index.py --force   # forces a rebuild
```

The index is persisted under `data/embeddings/` (`standards.faiss`, `standards_ids.json`,
`standards_meta.json`) and reused on subsequent startups.

## 11. Running the demo

The fastest path to a live demonstration:

1. Start the backend and frontend (sections 7 and 8).
2. Open http://localhost:5173.
3. Go to **Analyze Tender** and click **Load demo tender**
   (`data/sample_tenders/industrial_electrical_control_panel_tender.pdf`).
4. Click **Extract requirements** — the structured requirement object appears on the right.
5. Click **Find Applicable Standards**.
6. Review the ranked recommendations, expand a card to see *"Why this standard?"*, open the
   relationship graph, inspect version/amendment validation and the specification gaps.
7. Click **Generate PDF report** to export the full analysis.

The demo flow deliberately shows the whole chain:

```
Tender → Requirements → Primary standards → Testing standards → Safety standards
       → Related standards → Validation → Specification gaps → Explainable report
```

### Sample documents

| File | Purpose |
|---|---|
| `industrial_electrical_control_panel_tender.pdf` | Primary demo (415 V control panel) |
| `cement_supply_for_concrete_works_tender.pdf` | Cement / concrete category |
| `water_supply_upvc_piping_tender.pdf` | Water systems / piping category |
| `scanned_tender_image_only.pdf` | Image-only PDF — demonstrates the "OCR is required" path |

Regenerate the samples at any time:

```bash
cd backend && ./venv/bin/python ../scripts/create_sample_tenders.py
```

### DEMO_MODE

With `DEMO_MODE=true` (the default) the application needs **no API keys and no internet access**
after the initial model download:

- curated local standards dataset
- local sentence-transformer embeddings (with a deterministic TF-IDF fallback)
- rule-based requirement extraction
- deterministic, reproducible recommendations

If `all-MiniLM-L6-v2` cannot be downloaded, SISAP silently falls back to the TF-IDF backend and
keeps working — check `/api/health` to see which backend is active.

---

## 12. API documentation

Base path: `/api`. Interactive docs at `/api/docs`.

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/upload` | Upload a tender PDF (`multipart/form-data`, field `file`) |
| `POST` | `/documents/text` | Register pasted specification text (`form`, field `text`) |
| `GET` | `/documents/{document_id}` | Document details + extracted requirements |
| `POST` | `/documents/{document_id}/extract?use_llm=false` | Run requirement extraction |
| `GET` | `/documents/{document_id}/gaps` | Specification gap analysis |

### Recommendations

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/recommendations` | Run the pipeline (`{"document_id": "..."}` or `{"text": "..."}`) |
| `GET` | `/recommendations/{document_id}` | Stored recommendations for a document |

### Standards

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/standards` | Search/filter/paginate (`query`, `category`, `standard_type`, `status`, `page`, `page_size`) |
| `GET` | `/standards/categories` | Category counts |
| `GET` | `/standards/{standard_id}` | Full standard record |
| `GET` | `/standards/{standard_id}/graph?depth=1` | Relationship graph payload |
| `POST` | `/standards/reload?rebuild_index=true` | Reload dataset and rebuild the index |

### Reports, dashboard and system

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reports/{document_id}` | Generate the PDF report |
| `GET` | `/reports/{document_id}/download?file=<filename>` | Download the generated PDF |
| `GET` | `/dashboard/stats` | Dashboard aggregates |
| `GET` | `/health` | Pipeline status and non-sensitive settings |
| `GET` | `/demo/tender` | Bundled sample tender text |
| `GET` | `/config` | Non-sensitive public configuration |

### Example response — `POST /api/recommendations`

```json
{
  "document_id": "DOC-001",
  "product": "control panel",
  "category": "Electrical",
  "summary": {
    "total": 39, "primary": 4, "testing": 5, "safety": 1,
    "reference": 1, "installation": 7, "terminology": 0,
    "related": 21, "high_relevance": 4, "potential_gaps": 2
  },
  "recommendations": [
    {
      "standard_id": "IS 8623-1:2002",
      "standard_number": "IS 8623 (Part 1) : 2002",
      "title": "Specification for switchgear and controlgear assemblies for voltages not exceeding 1000 V, Part 1: General requirements",
      "type": "Primary",
      "score": 76.6,
      "status": "Active",
      "score_breakdown": {
        "semantic_similarity": 0.64,
        "requirement_coverage": 0.83,
        "product_match": 1.0,
        "application_match": 0.5,
        "category_match": 1.0,
        "weights": {
          "semantic_similarity": 0.45, "requirement_coverage": 0.25,
          "product_match": 0.15, "application_match": 0.10, "category_match": 0.05
        }
      },
      "explanation": [
        "Product type matches: switchgear assembly, controlgear assembly, control panel",
        "Technical requirement overlap: degree of protection",
        "Testing requirement overlap: type tests",
        "Safety requirement overlap: protection against direct contact",
        "Installation requirement overlap: indoor installation",
        "Material requirement matches: steel sheet enclosure, aluminium enclosure",
        "Category match: Electrical"
      ],
      "matched_requirements": ["degree of protection", "temperature rise limits", "..."],
      "missing_requirements": ["..."],
      "related_standards": ["IS 8623-2:2006", "IS 4237:2013", "..."],
      "validation": {
        "status": "Active",
        "version": "2002",
        "amendments": ["Amendment No. 1", "Amendment No. 2"],
        "superseded_by": [],
        "checks": [
          "✓ Status: Active in the curated dataset",
          "✓ Version recorded: 2002",
          "⚠ Amendment available: Amendment No. 1, Amendment No. 2",
          "✓ No known superseding standard in the curated dataset"
        ],
        "validation_source": "Curated demo dataset"
      },
      "scope": "Applies to low-voltage switchgear and controlgear assemblies..."
    }
  ],
  "gaps": [
    {
      "gap_type": "Standards referenced",
      "severity": "Medium",
      "description": "The tender does not cite any Indian Standard. SISAP identified 39 potentially applicable standards from the curated dataset.",
      "suggested_action": "Cite the applicable Indian Standards (with edition year) in the specification so that suppliers bid against a common technical baseline.",
      "related_standards": ["IS 8623-1:2002", "IS 4237:2013"]
    }
  ],
  "extraction_method": "rule-based",
  "review_note": "AI-generated recommendations should be reviewed by the responsible procurement/technical authority."
}
```

### Error handling

Errors return a JSON body with a stable `code`:

```json
{ "detail": "Text could not be reliably extracted. OCR is required for this document.", "code": "scanned" }
```

| Situation | Code | Status |
|---|---|---|
| Unsupported file type / empty / not a PDF / too large | `invalid_upload` | 400 |
| Scanned or image-only PDF | `scanned` (reported in the upload response) | 200 + `is_scanned: true` |
| Document or standard not found | `document_not_found` / `standard_not_found` | 404 |
| Report not found / path traversal attempt | `report_not_found` | 404 |
| Malformed request body | `validation_error` | 422 |
| Missing `document_id` and `text` | `invalid_request` | 400 |
| No sufficiently relevant standard found | *(empty recommendations + `Primary standard` gap)* | 200 |

---

## 13. Project structure

```
sisap/
├── backend/
│   ├── main.py                     FastAPI app + lifespan startup
│   ├── config.py                   Settings (env-driven)
│   ├── requirements.txt
│   ├── api/routes.py               REST endpoints
│   ├── ai/
│   │   ├── embeddings.py           Sentence-Transformers / TF-IDF backend
│   │   ├── vector_store.py         FAISS index wrapper
│   │   └── llm_provider.py         Optional LLM abstraction
│   ├── database/
│   │   ├── db.py                   SQLite schema + migrations
│   │   └── repositories.py         Standards / documents / recommendations / gaps
│   ├── document_processing/
│   │   ├── pdf_extractor.py        PyMuPDF extraction + scanned detection
│   │   └── text_processor.py       Cleaning + section detection
│   ├── recommendation/
│   │   ├── requirement_extractor.py  Rule-based + LLM extraction
│   │   ├── recommendation_engine.py  Composite scoring + graph expansion
│   │   └── gap_detector.py         Specification gap detection
│   ├── graph/standards_graph.py    NetworkX relationship graph
│   ├── validation/standards_validator.py
│   ├── reports/pdf_report.py       ReportLab PDF report
│   ├── schemas/schemas.py          Pydantic API contract
│   ├── services/                   Orchestration layer
│   └── utils/                      Logging + text helpers
├── frontend/
│   ├── src/
│   │   ├── components/             Domain + UI components
│   │   ├── components/ui/          shadcn-style primitives
│   │   ├── components/layout/      App shell and navigation
│   │   ├── pages/                  Dashboard, Analyze, Recommendations, ...
│   │   ├── services/api.ts         Typed API client
│   │   ├── hooks/                  useApi, useAnalysis, useDebounced
│   │   ├── types/                  Shared API types
│   │   └── utils/cn.ts             Class merge + formatters
│   ├── vite.config.ts              Dev server + /api proxy
│   └── package.json
├── data/
│   ├── standards.json              Curated demo dataset (63 standards)
│   ├── sample_tenders/             Demo PDFs + text
│   └── embeddings/                 Persisted FAISS index
├── models/                         Reserved for cached ML artifacts
├── scripts/
│   ├── extend_dataset.py           Add standards to the dataset
│   ├── create_sample_tenders.py    Regenerate sample tenders
│   ├── load_standards.py           Load the dataset into SQLite
│   └── build_faiss_index.py        Build the FAISS index
├── reports/                        Generated PDF reports
└── README.md
```

### Database tables

| Table | Purpose |
|---|---|
| `standards` | Standard records with all metadata facets |
| `standard_relationships` | Typed edges (`references`, `referenced_by`, `related`, `testing`, `safety`, `installation`, `terminology`, `supersedes`) |
| `documents` | Uploaded documents and extracted text |
| `extracted_requirements` | Structured requirement objects per document |
| `recommendations` | Scored recommendations with explanations |
| `specification_gaps` | Detected gaps with severity and suggested actions |

---

## 14. Security

- **File type validation** — only `application/pdf` uploads are accepted; the magic bytes
  (`%PDF`) are verified, not just the extension.
- **File size limits** — configurable via `SISAP_MAX_UPLOAD_MB` (default 25 MB).
- **Sanitised filenames** — uploads are stored under a UUID prefix with a whitelist-sanitised name;
  report downloads resolve only inside `reports/` and reject path traversal.
- **No arbitrary file execution** — uploaded files are read as bytes and parsed by PyMuPDF only.
- **Input validation** — all request bodies are validated by Pydantic; malformed requests return
  structured 422 errors.
- **Secrets** — API keys live in environment variables, are read server-side only, and are never
  returned by any endpoint (`/api/config` and `/api/health` return non-sensitive settings only).
- **Error handling** — every endpoint returns a JSON error with a stable `code`; unhandled
  exceptions are logged and return a generic 500 without leaking internals.

---

## 15. Accessibility

- Semantic landmarks, a skip-to-content link, and labelled form controls.
- Full keyboard navigation, focus-visible outlines, and focus trapping in modals.
- `aria-live` toast notifications, `aria-expanded` disclosure buttons, `role="progressbar"` with
  `aria-valuenow` on every score bar.
- `prefers-reduced-motion` disables skeleton shimmer animations.
- Responsive layouts from 320 px upward with horizontally scrollable tables on small screens.

---

## 16. Future improvements

The code is structured so these can be added without re-architecting:

- **PostgreSQL + pgvector** — re-implement `database/repositories.py` and `ai/vector_store.py`
  behind the existing interfaces.
- **Live BIS data ingestion** — add a `BISCatalogueAdapter` behind a provider protocol; the dataset
  metadata already carries `source`, `source_url` and `bis_verified` fields.
- **OCR** — the pipeline already reports the scanned condition; plug an OCR adapter into
  `document_processing/` and the rest of the flow is unchanged.
- **Multilingual tender analysis** — swap the embedding model and extend the requirement lexicons.
- **Government procurement portal integration** — GeM and CPPP adapters behind an interface, with no
  fake integrations shipped.
- **Authentication / RBAC, audit logs, human review workflow** — add middleware and review-state
  columns; the recommendation records already persist validation and explanation JSON.
- **Feedback-based recommendation improvement** — capture officer accept/reject signals against
  `recommendations` rows and retrain the composite weights.

---

## 17. Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend shows "Could not reach the SISAP backend" | Start the backend (`uvicorn main:app --reload`) and reload the page |
| `/api/health` shows `embedding_backend: tfidf` | The sentence-transformer model is unavailable; the TF-IDF fallback is active and results are still deterministic |
| Upload returns "OCR is required" | The PDF is image-only; enable an OCR adapter or upload a text-based PDF |
| First request is slow | The model is being downloaded/cached; subsequent requests are fast |
| Report download 404s | Regenerate the report — the file name is returned by `POST /api/reports/{id}` |

---

## 18. Disclaimer

This project is an academic/demonstration prototype built for Smart India Hackathon 2026
(SIH26108). The standards dataset is a **curated demo dataset** compiled from publicly available BIS
catalogue summaries. It is **not verified against the live BIS catalogue** and contains no live BIS
data. Nothing in this project constitutes legal, regulatory or certification advice.

*Potentially applicable standards identified. Review required.*
