# APS Road Design Check

A Python Flask web application that uses [Autodesk Platform Services (APS)](https://aps.autodesk.com) to verify horizontal curve data from Civil 3D alignments against design standards.

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

> **Note — Model Derivative translation:** Files must be translated to SVF/SVF2 format by the Model Derivative API before the APS Viewer can display them and before `getBulkProperties` can access the property database. ACC and BIM 360 projects translate files automatically on upload; OSS-hosted files require an explicit translation job.

---

Pros
- Fully reproducible: Same inputs always produce the same output
- Auditable: The result traces back to an exact rule in the standards file
- Version-controllable: Standards live in source control alongside the code

Cons
- Manual conversion required: Official documents must be translated into structured data by hand
- No semantic understanding: Cannot handle conditional or nuanced requirements
- Maintenance burden: Must be updated whenever standards change
- Limited scope: Only checks what is explicitly defined. implicit requirements are missed

When to use
When you have restrictions to probabilistic approaches and the standards are stable and well-defined.

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

Pros
- Works from official documents: No manual conversion needed
- Semantic retrieval: Finds relevant standards even with varied phrasing
- Scales to large libraries: Multiple documents can be searched in a single query
- Lower setup cost: Index once, reuse across many queries

Cons
- Non-deterministic: The same query may return different results across runs
- Requires human verification: Citations may be incomplete, misquoted, or incorrect
- Service dependency: Design data is sent to an external provider
- Indexing latency: Processing new documents takes time
- Black-box reasoning: Cannot fully trace why a specific threshold was or was not applied

When to use
When the standards library is difficult to automate or changes frequently, and you need a tool to help reviewers navigate large documents faster. Treat the output as a first-pass triage.
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

Pros
- Structured output: Enforced schema makes results easier to parse by downstream tools
- Decoupled: Update the standards index or the evaluation rubric independently
- Consistent evaluation: Rubric is defined once and reused across checks

Cons
- Non-deterministic: The same query may return different results across runs
- Requires human verification: Same hallucination risk as Approach 2
- Higher latency and token cost: Two model calls instead of one
- Service dependency: Design data is sent to an external provider
- Rubric overhead: Evaluation logic must be maintained and versioned separately
- Black-box reasoning: Cannot fully trace why a specific threshold was or was not applied

When to use
When you need a more structured compliance report, or when the evaluation rubric needs to be maintained and versioned separately from the standards content. Also useful when the same rubric will be applied across multiple projects or standards libraries.

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
  - Set `APS_CLIENT_ID`, `APS_CLIENT_SECRET`, and `APS_CALLBACK_URL`
    (`APS_CALLBACK_URL` defaults to `http://localhost:8080/api/auth/callback`; update this for non-local deployments)
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
