# APS Road Design Check

A Python Flask web application that uses [Autodesk Platform Services (APS)](https://aps.autodesk.com) to verify horizontal curve data from Civil 3D alignments (and NWC files) against Department of Transportation design standards.

Two fundamentally different verification philosophies are supported: **deterministic** (JSON) and **probabilistic** (OpenAI RAG).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Approach 1 — Deterministic (JSON Standards)](#approach-1--deterministic-json-standards)
- [Approach 2 — Probabilistic RAG (OpenAI)](#approach-2--probabilistic-rag-openai)
- [Approach Comparison](#approach-comparison)
- [Setup](#setup)
- [Usage](#usage)
- [License](#license)

---

## Architecture Overview

```
Civil 3D / NWC model
        │  (APS Viewer — curve properties via getBulkProperties)
        ▼
┌──────────────────────────────────────────────────────────────┐
│  AlignmentCheckExtensionJSON        AlignmentCheckExtensionAI │
│  (deterministic check)              (AI-assisted check)       │
└────────────┬─────────────────────────────┬───────────────────┘
             │                             │
             ▼                             ▼
    JSON standards file          /api/openai/query
    (local comparison)                     │
                                  OpenAI gpt-4o
                                  + Vector Store (RAG)
```

---

## Approach 1 — Deterministic (JSON Standards)

### How it works

1. A standards JSON file is uploaded via the **JSON Input** button.
   The file encodes design thresholds by speed class, e.g.:
   ```json
   { "horizontal_curve": { "minimum_radius_by_speed": { "50_mph": { "emax_4_percent_ft": 818 } } } }
   ```
2. The viewer extension (`AlignmentCheckExtensionJSON`) reads each selected curve's radius and design speed directly from the model.
3. It looks up the matching speed key in the JSON, retrieves `emax_4_percent_ft`, and compares the actual radius against it.
4. A pass/fail report is generated locally — no network call, no model inference.

### Pros

| | |
|---|---|
| **Fully reproducible** | Same inputs always produce the same output. |
| **No API costs** | Runs entirely in the browser / server with no external calls. |
| **Auditable** | Every pass/fail is traceable to an exact line in the JSON file. |
| **Instant** | Comparison is pure arithmetic — sub-millisecond per curve. |
| **Works offline** | No dependency on third-party services. |
| **Version-controllable** | Standards files live in git alongside the code. |

### Cons

| | |
|---|---|
| **Manual conversion required** | Official standards PDFs must be translated into JSON by hand. |
| **Brittle to schema changes** | Any restructure of the JSON breaks the comparison logic. |
| **No semantic understanding** | Cannot handle nuanced language in standards ("unless otherwise specified…"). |
| **Maintenance burden** | Must be updated manually whenever standards are revised. |
| **Limited scope** | Only checks what is explicitly in the JSON; misses implicit requirements. |

### When to use

When you need **reproducible, auditable compliance decisions** and the standards are stable and well-structured. Ideal for CI/CD pipelines, batch processing, and regulatory submissions.

---

## Approach 2 — Probabilistic RAG (OpenAI)

### How it works

1. A PDF is uploaded via the **Index PDF** button.  
   The backend (`/api/openai/indexpdf`) uploads it to OpenAI, creates a vector store, and **polls until indexing is complete** before returning — so the PDF is ready to query immediately.
2. OpenAI chunks the PDF into overlapping segments and embeds each chunk into a high-dimensional vector space. Chunks and their vectors are stored in OpenAI's managed vector store.
3. At query time (`/api/openai/query`), the `gpt-4o` model uses its built-in `file_search` tool to:
   - Embed the question
   - Retrieve the most semantically relevant chunks from the vector store
   - Generate a structured compliance report with citations
4. The answer is probabilistic: the model reasons over the retrieved chunks using language understanding, not arithmetic.

### System prompt

The system prompt (`Controllers/OpenAIController.py › SYSTEM_PROMPT`) instructs `gpt-4o` to:

- Extract every curve parameter from the question (radius, design speed, superelevation, etc.) and note its unit.
- Search the indexed documents for the governing threshold for each parameter, citing document name, section, and page.
- Record a **PASS** or **FAIL** per parameter and produce a specific corrective action for any failure.

The response is always returned in a fixed markdown structure — Assessment / Parameters Checked table / Citations / Recommendations — so the viewer extension can display it consistently regardless of the document content.

### Pros

| | |
|---|---|
| **Works from official PDFs** | No manual conversion — index the actual document. |
| **Semantic retrieval** | Finds relevant standards even with varied wording or phrasing. |
| **Index once, query many** | Vector stores persist on OpenAI; per-query cost covers only the retrieved chunks. |
| **Scales to large libraries** | Multiple PDFs can be indexed and searched across in a single query. |
| **Natural language reasoning** | Can handle conditional and nuanced standard requirements. |
| **Cross-document citations** | A single query can retrieve from multiple standards documents. |

### Cons

| | |
|---|---|
| **Non-deterministic** | The same query may return slightly different answers across runs. |
| **API costs** | Both indexing (file upload + vector store) and querying (gpt-4o tokens) incur costs. |
| **Indexing latency** | Processing a new PDF is asynchronous and can take 30–120 seconds. |
| **Chunking loss** | Relevant context split across chunk boundaries may be missed. |
| **Citation accuracy** | The model may misattribute or paraphrase citations imprecisely. |
| **Service dependency** | Requires OpenAI availability; data is stored on OpenAI's infrastructure. |
| **Black-box reasoning** | Cannot fully trace why a specific threshold was or was not applied. |

### When to use

When the standards library is large or changes frequently, or when you want to query multiple documents with a single prompt. Good for design assistance and exploratory checks, where approximate answers with citations are more valuable than strict auditability.

---

## Approach Comparison

| | JSON (Deterministic) | OpenAI RAG (Probabilistic) |
|---|---|---|
| **Result reproducibility** | 100% deterministic | Non-deterministic |
| **Standards source** | Hand-crafted JSON | Original PDF |
| **Indexing required** | No | Yes (async, ~30–120 s) |
| **Per-query cost** | $0 | Low (retrieved chunk tokens only) |
| **Citation accuracy** | Exact (rule-based) | Approximate |
| **Offline capable** | Yes | No |
| **Maintenance** | Manual JSON updates | Re-index updated PDF |
| **Best for** | Audits, CI/CD, submissions | Large libraries, design assistance |

---

## Setup

### Requirements

- Python 3.12
- OpenAI API key

### 1. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- **Autodesk Platform Services**: Get credentials at https://aps.autodesk.com/myapps
  - Set `APS_CLIENT_ID` and `APS_CLIENT_SECRET`
- **OpenAI API**: Get your API key at https://platform.openai.com/api-keys
  - Set `OPENAI_API_KEY`

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Run

```bash
python app.py
```

The application will be available at `http://localhost:8080`.

---

## Usage

### JSON-based verification (deterministic)

1. Click **JSON Input** and upload a standards JSON file (see `Assets/Highway-Design-Standards.json` for the schema).
2. Open a Civil 3D or NWC model in the APS Viewer.
3. Select one or more horizontal curves.
4. Click the **AlignmentCheckExtensionJSON** toolbar button.
5. Set the design speed and confirm — a pass/fail report is generated instantly.

### OpenAI RAG verification

1. Click **Index PDF** and upload a PDF copy of your design standards document.  
   Wait for the confirmation that indexing is complete (the server polls OpenAI until the vector store is ready).
2. Select one or more curves in the viewer.
3. Click the **AlignmentCheckExtensionAI** toolbar button.
4. Choose the indexed PDF from the dropdown, set the design speed, and confirm.
5. The query is sent to `gpt-4o` with the `file_search` tool; the structured compliance report is returned.

---

## Development

### Debug mode

**VS Code (recommended)**

1. Open the project in VS Code.
2. Go to **Run and Debug** (Ctrl+Shift+D).
3. Select **Python: Flask** from the dropdown.
4. Press **F5** — the app starts at `http://localhost:8080` with auto-reload.

**Terminal**

```bash
python app.py
```

> Remember to set `debug=False` in production.

---

## License

MIT
