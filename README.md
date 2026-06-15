# APS Road Design Check

A Python Flask web application that uses [Autodesk Platform Services (APS)](https://aps.autodesk.com) to verify horizontal curve data from Civil 3D alignments (and NWC files) against Department of Transportation design standards.

Three verification approaches are supported: **deterministic** (JSON), **probabilistic RAG** (OpenAI), and **Skills + RAG hybrid** (OpenAI).

## Video
[![Walkthrough](https://i.ytimg.com/vi/hB_uJ4rXTzw/hqdefault.jpg)](https://www.youtube.com/watch?v=hB_uJ4rXTzw)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Approach 1 — Deterministic (JSON Standards)](#approach-1--deterministic-json-standards)
- [Approach 2 — Probabilistic RAG (OpenAI)](#approach-2--probabilistic-rag-openai)
- [Approach 3 — OpenAI Skills + RAG Hybrid](#approach-3--openai-skills--rag-hybrid)
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
┌────────────────────────────────────────────────────────────────────────────────┐
│  AlignmentCheckExtensionJSON   AlignmentCheckExtensionAI   AlignmentCheckExtensionSkill │
│  (deterministic check)         (RAG check)                 (Skills + RAG check) │
└──────────┬─────────────────────────────┬──────────────────────────┬────────────┘
           │                             │                          │
           ▼                             ▼                          ▼
  JSON standards file          /api/openai/query          /api/openai/skill/query
  (local comparison)                    │                          │
                                OpenAI gpt-4o              Step 1: file_search
                                + file_search tool         → retrieve clauses
                                + Vector Store (RAG)               │
                                                           Step 2: Responses API
                                                           + SKILL.md rubric
                                                           + structured JSON output
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
3. At query time (`/api/openai/query`), the `gpt-5.4` model uses its built-in `file_search` tool to:
   - Embed the question
   - Retrieve the most semantically relevant chunks from the vector store
   - Generate a structured compliance report with citations
4. The answer is probabilistic: the model reasons over the retrieved chunks using language understanding, not arithmetic.

### System prompt

The system prompt (`Controllers/OpenAIController.py › SYSTEM_PROMPT`) instructs `gpt-5.4` to:

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
| **API costs** | Both indexing (file upload + vector store) and querying (gpt-5.4 tokens) incur costs. |
| **Indexing latency** | Processing a new PDF is asynchronous and can take 30–120 seconds. |
| **Chunking loss** | Relevant context split across chunk boundaries may be missed. |
| **Citation accuracy** | The model may misattribute or paraphrase citations imprecisely. |
| **Service dependency** | Requires OpenAI availability; data is stored on OpenAI's infrastructure. |
| **Black-box reasoning** | Cannot fully trace why a specific threshold was or was not applied. |

### When to use

When the standards library is large or changes frequently, or when you want to query multiple documents with a single prompt. Good for design assistance and exploratory checks, where approximate answers with citations are more valuable than strict auditability.

---

## Approach 3 — OpenAI Skills + RAG Hybrid

> **Investigation reference:** `openai-skills-rag-handoff.md` — ChatGPT investigation into whether OpenAI Skills can replace or augment the RAG layer.

### How it works

1. A PDF is indexed the same way as Approach 2 (the same vector store is reused).
2. When the **AlignmentCheckExtensionSkill** toolbar button is clicked, the extension collects curve properties and sends them — as both a natural-language summary and a structured `design_data` JSON — to `/api/openai/skill/query`.
3. The backend performs two sequential Responses API calls:
   - **Step 1 — Retrieval:** A `file_search` call retrieves the most relevant standard clauses from the vector store. This call is retrieval-only; no evaluation happens here.
   - **Step 2 — Evaluation:** A second Responses API call receives the design data **plus the retrieved clause text** and evaluates compliance against them. The evaluation method is defined by `Assets/design-standard-checker/SKILL.md` — a reusable rubric that encodes the comparison rules, confidence-scoring logic, citation requirements, and the strict JSON output schema.
4. If `OPENAI_SKILL_ID` is set in `.env`, the hosted skill is attached via a `shell/container_auto/skill_reference` tool and SKILL.md is used as a fallback. If the env var is absent, SKILL.md content is injected as the `instructions` parameter directly.
5. The response is a structured JSON compliance report (see `Assets/design-standard-checker/references/output-schema.md`) displayed as a per-check table with status, confidence, and grounded remediation.

### Key architectural difference from Approach 2

```
Approach 2 — single Responses API call:
  file_search retrieves AND model reasons over results in one step.
  Output: markdown report.

Approach 3 — two decoupled steps:
  Step 1: file_search retrieves relevant clauses (retrieval layer).
  Step 2: skill-guided Responses API call evaluates design data
          against pre-retrieved clauses (evaluation layer).
  Output: strict JSON compliance report.

This means the standards index and the evaluation rubric can evolve
independently — re-index the PDF without touching the skill, or update
the rubric without re-indexing.
```

### Skill package

```
Assets/design-standard-checker/
  SKILL.md                        ← evaluation instructions and rules
  references/
    output-schema.md              ← strict JSON schema the model must return
    comparison-rubric.md          ← pass/fail/needs_review and confidence rules
    retrieval-contract.md         ← shape of retrieved_clauses passed to the model
```

To use a hosted OpenAI skill, package the directory as a ZIP, upload it, and set `OPENAI_SKILL_ID` in `.env`. Without it the app uses the SKILL.md content as instructions (fallback mode — functionally equivalent, no container environment).

### Pros

| | |
|---|---|
| **Reusable evaluation logic** | Rubric, output schema, and citation rules are defined once in the skill; every call reuses the same judge without repeating a long system prompt. |
| **Decoupled standards from process** | Update the PDF index without touching the evaluation rubric, or update the rubric without re-indexing. |
| **Structured JSON output** | Strict schema enforced by the skill; downstream tooling (issue creation, CI, audits) can parse the report directly. |
| **Grounded citations** | Skill explicitly forbids inventing standards; all citations must come from retrieved clauses. |
| **Per-check confidence** | Each check carries a `high / medium / low` confidence level alongside the pass/fail verdict. |
| **Grounded remediation** | Corrective actions are only generated when a specific clause supports them. |

### Cons

| | |
|---|---|
| **Skills API is newer / beta** | The `skill_reference` / container shell environment may not be in GA for all OpenAI accounts; the fallback (SKILL.md as instructions) works everywhere. |
| **Two-step latency** | Two sequential Responses API calls roughly double the wall-clock time versus Approach 2's single call. |
| **Skill management overhead** | Hosted skills must be uploaded, versioned, and re-uploaded when the rubric changes. |
| **Same service dependency** | Still requires OpenAI availability; same data-residency constraints as Approach 2. |
| **Higher token cost** | Two model calls consume more tokens than one, even though the second call receives pre-retrieved context rather than searching the full index. |

### When to use

When you need a **machine-readable compliance report** for downstream automation (CI gates, issue creation, audit trails), or when the evaluation rubric needs to be maintained and versioned separately from the standards content. Also useful when the same rubric will be applied across multiple projects or standards libraries.

---

## Approach Comparison

| | JSON (Deterministic) | OpenAI RAG (Probabilistic) | OpenAI Skills + RAG |
|---|---|---|---|
| **Result reproducibility** | 100% deterministic | Non-deterministic | Non-deterministic |
| **Standards source** | Hand-crafted JSON | Original PDF | Original PDF (same index as Approach 2) |
| **Indexing required** | No | Yes (async, ~30–120 s) | Yes (same as Approach 2) |
| **Per-query cost** | $0 | Low (retrieved chunk tokens only) | Moderate (two model calls) |
| **Output format** | Plain text | Markdown report | Structured JSON |
| **Citation accuracy** | Exact (rule-based) | Approximate | Clause-grounded (enforced by skill) |
| **Per-check confidence** | Implicit (pass/fail) | None | Explicit (high / medium / low) |
| **Offline capable** | Yes | No | No |
| **Evaluation rubric versioning** | In JSON file | In system prompt (code) | In SKILL.md (separate asset) |
| **Maintenance** | Manual JSON updates | Re-index updated PDF | Re-index PDF and/or update SKILL.md independently |
| **Skills API required** | No | No | Optional (fallback to SKILL.md instructions) |
| **Best for** | Audits, CI/CD, submissions | Large libraries, design assistance | Automated pipelines, audit trails, rubric reuse across projects |

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
- **OpenAI model** *(optional)*: Set `OPENAI_MODEL` to override the model used by Approaches 2 and 3. Defaults to `gpt-5.4` if not set.
- **OpenAI skill** *(optional)*: Set `OPENAI_SKILL_ID` to a hosted skill ID to enable the container-based skill tool in Approach 3. If not set, `Assets/design-standard-checker/SKILL.md` is injected as instructions instead (fallback mode).

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

### OpenAI Skills + RAG verification

1. Index a PDF the same way as above (the same vector store is reused).
2. *(Optional)* Set `OPENAI_SKILL_ID` in `.env` with the ID of a hosted `design-standard-checker` skill. If not set, the app falls back to loading `Assets/design-standard-checker/SKILL.md` as instructions.
3. Select one or more curves in the viewer.
4. Click the **AlignmentCheckExtensionSkill** toolbar button.
5. Set the design speed and click **Run Check**.
6. The backend runs two sequential calls: clause retrieval via `file_search`, then skill-guided evaluation. A per-check compliance table (with status, confidence, and remediation) is displayed. The issue description is pre-populated with the JSON summary.

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

See [LICENSE](LICENSE) for details.
