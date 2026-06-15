"""
OpenAI Controller
Handles all OpenAI-backed routes for both approaches:

  Approach 2 — Direct RAG
    POST /api/openai/query
    Uses file_search in a single Responses API call.

  Approach 3 — Skills + RAG
    GET  /api/openai/skill/list
    POST /api/openai/skill/upload
    POST /api/openai/skill/query
    Two-step: file_search retrieval then skill-guided evaluation.

Model is read from the OPENAI_MODEL environment variable (default: gpt-4o).
Skill resolution order for /skill/query:
  1. skill_id in the POST body
  2. OPENAI_SKILL_ID environment variable
  3. Fallback: SKILL.md injected as instructions
"""

import json
import os
import pathlib
import time
from datetime import datetime

import requests as http_requests
from flask import Blueprint, request, jsonify
from openai import OpenAI

_OPENAI_API_BASE = "https://api.openai.com/v1"

POLL_INTERVAL = 1
POLL_TIMEOUT = 120

_SKILL_MD_PATH = (
    pathlib.Path(__file__).parent.parent
    / "Assets"
    / "design-standard-checker"
    / "SKILL.md"
)

SYSTEM_PROMPT = """You are a road design standards expert.
Use the file_search tool to locate requirements in the indexed PDF documents.

Given a description of one or more horizontal curves, you must:
1. Extract every curve parameter provided (design speed, radius, superelevation, lane width, etc.) and note its unit.
2. Search the knowledge base for the governing threshold or requirement for each parameter. Cite the document name, section, and page number.
3. Compare each provided value against the required threshold and record PASS or FAIL.
4. If non-compliant, give a specific corrective action (e.g., "Increase radius from 200 ft to at least 350 ft").
5. If a required input is absent, state "Not provided" and indicate whether a compliance verdict is still possible.

Respond using this exact format:

## Assessment: [COMPLIANT | NON-COMPLIANT | INSUFFICIENT DATA]

## Parameters Checked
| Parameter | Provided | Required | Result |
|---|---|---|---|
| [name] | [value + unit] | [value + unit] | PASS / FAIL |

## Citations
- [document], Section [X], Page [Y]: "[relevant text]"

## Recommendations
- [Only if non-compliant: specific corrective actions]

Be precise with numbers and units. Do not truncate or summarise the compliance table."""

_RETRIEVAL_INSTRUCTIONS = (
    "You are a standards retrieval assistant. "
    "Given road design parameters, retrieve every relevant clause from the indexed documents. "
    "For each clause include its section number, page, and full verbatim text. "
    "Be comprehensive — include all potentially applicable requirements."
)

_client = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def _api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return key


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_api_key()}"}


def _resolve_vector_store_ids(client: OpenAI, vector_store_id: str | None) -> list[str]:
    """Return vector store IDs to search. Raises ValueError when none are indexed."""
    if vector_store_id:
        vs = client.vector_stores.retrieve(vector_store_id)
        return [vs.id]
    stores = client.vector_stores.list()
    ids = [vs.id for vs in stores.data]
    if not ids:
        raise ValueError("No PDFs indexed yet. Use /api/openai/indexpdf first.")
    return ids


def _upload_file(file_storage) -> str:
    """Upload a PDF to OpenAI and return the file ID."""
    client = _get_client()
    response = client.files.create(
        file=(file_storage.filename, file_storage.stream, file_storage.content_type),
        purpose="assistants",
    )
    return response.id


def _poll_batch(vector_store_id: str, batch_id: str):
    """Wait for a file batch to finish processing. Raises on failure or timeout."""
    client = _get_client()
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        batch = client.vector_stores.file_batches.retrieve(
            vector_store_id=vector_store_id,
            batch_id=batch_id,
        )
        if batch.status == "completed":
            return batch
        if batch.status in ("failed", "cancelled"):
            raise Exception(f"Vector store file batch ended with status: {batch.status}")
        time.sleep(POLL_INTERVAL)
    raise Exception(f"Timed out waiting for vector store indexing after {POLL_TIMEOUT}s")


def _load_skill_instructions() -> str:
    try:
        return _SKILL_MD_PATH.read_text(encoding="utf-8")
    except OSError:
        return (
            "You are a road design compliance expert. "
            "Evaluate the provided design data against the retrieved standard clauses "
            "and return a strict JSON compliance report."
        )


def _build_skill_tools(skill_id: str) -> list:
    return [
        {
            "type": "shell",
            "environment": {
                "type": "container_auto",
                "skills": [{"type": "skill_reference", "skill_id": skill_id}],
            },
        }
    ]


def _parse_json_report(raw: str) -> dict:
    """Parse a JSON compliance report from model output, stripping markdown fences."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(clean)


# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

openai_bp = Blueprint("openai", __name__, url_prefix="/api/openai")


# ---------------------------------------------------------------------------
# Approach 2 — Direct RAG
# ---------------------------------------------------------------------------

@openai_bp.route("/indexedpdfs", methods=["GET"])
def get_indexed_pdfs():
    """GET /api/openai/indexedpdfs — list all indexed vector stores."""
    try:
        client = _get_client()
        vector_stores = client.vector_stores.list()
        pdfs = [
            {"vector_store_id": vs.id, "filename": vs.name, "created_at": vs.created_at}
            for vs in vector_stores.data
        ]
        return jsonify(pdfs), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Failed to load indexed PDFs: {str(e)}"}), 500


@openai_bp.route("/indexpdf", methods=["POST"])
def index_pdf():
    """
    POST /api/openai/indexpdf — upload a PDF and create a vector store.
    Polls until indexing is complete before returning.
    Expects: multipart/form-data with 'file' field (PDF).
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    try:
        openai_file_id = _upload_file(file)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    try:
        vector_store = client.vector_stores.create(
            name=f"{file.filename} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        batch = client.vector_stores.file_batches.create(
            vector_store_id=vector_store.id,
            file_ids=[openai_file_id],
        )
        _poll_batch(vector_store.id, batch.id)
    except Exception as e:
        try:
            client.files.delete(openai_file_id)
        except Exception:
            pass
        return jsonify({"error": f"Failed to create vector store: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "message": "PDF indexed and ready for querying",
        "pdf": {
            "vector_store_id": vector_store.id,
            "openai_file_id": openai_file_id,
            "filename": file.filename,
        },
    }), 200


@openai_bp.route("/query", methods=["POST"])
def query_knowledge_base():
    """
    POST /api/openai/query — Approach 2: single RAG call with file_search.
    Expects JSON: { "question": "...", "vector_store_id": optional_id }
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data["question"]
    vector_store_id = data.get("vector_store_id")

    try:
        vector_store_ids = _resolve_vector_store_ids(client, vector_store_id)
        context_info = (
            f"Using PDF: {client.vector_stores.retrieve(vector_store_ids[0]).name}"
            if vector_store_id
            else f"Searching {len(vector_store_ids)} indexed PDF(s)"
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Vector store not found: {str(e)}"}), 404

    try:
        model = _get_model()
        response = client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=question,
            tools=[{"type": "file_search", "vector_store_ids": vector_store_ids}],
        )
        return jsonify({
            "success": True,
            "question": question,
            "answer": response.output_text,
            "context": context_info,
            "model": model,
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to query knowledge base: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Approach 3 — Skills + RAG
# ---------------------------------------------------------------------------

@openai_bp.route("/skill/list", methods=["GET"])
def list_skills():
    """GET /api/openai/skill/list — list uploaded skills. Returns [] if Skills API unavailable."""
    try:
        resp = http_requests.get(
            f"{_OPENAI_API_BASE}/skills",
            headers=_auth_headers(),
            timeout=10,
        )
        if resp.status_code == 404:
            return jsonify([]), 200
        resp.raise_for_status()
        skills = [
            {
                "skill_id": s["id"],
                "name": s.get("name", s["id"]),
                "description": s.get("description", ""),
            }
            for s in resp.json().get("data", [])
        ]
        return jsonify(skills), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Failed to list skills: {str(e)}"}), 500


@openai_bp.route("/skill/upload", methods=["POST"])
def upload_skill():
    """POST /api/openai/skill/upload — upload a skill ZIP. Expects multipart 'file' field."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    try:
        resp = http_requests.post(
            f"{_OPENAI_API_BASE}/skills",
            headers=_auth_headers(),
            files={"files": (file.filename, file.stream, "application/zip")},
            timeout=60,
        )
        resp.raise_for_status()
        skill_obj = resp.json()
        return jsonify({
            "success": True,
            "skill": {
                "skill_id": skill_obj["id"],
                "name": skill_obj.get("name", file.filename),
                "description": skill_obj.get("description", ""),
            },
        }), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except http_requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        return jsonify({"error": f"Failed to upload skill: {detail}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to upload skill: {str(e)}"}), 500


@openai_bp.route("/skill/query", methods=["POST"])
def query_with_skill():
    """
    POST /api/openai/skill/query — Approach 3: two-step retrieve then skill-guided evaluate.
    Expects JSON:
    {
        "question":        "Check the curves ...",
        "design_data":     { "Curve 1": { "Radius": "200 ft", ... }, ... },
        "vector_store_id": "vs_...",   // optional
        "skill_id":        "skill_..." // optional; overrides OPENAI_SKILL_ID env var
    }
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data["question"]
    design_data = data.get("design_data", {})
    vector_store_id = data.get("vector_store_id")
    skill_id = data.get("skill_id") or os.getenv("OPENAI_SKILL_ID") or None
    model = _get_model()

    try:
        vector_store_ids = _resolve_vector_store_ids(client, vector_store_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Vector store error: {str(e)}"}), 404

    # Step 1: retrieve relevant standard clauses
    try:
        retrieval_response = client.responses.create(
            model=model,
            instructions=_RETRIEVAL_INSTRUCTIONS,
            input=f"Retrieve standards relevant to:\n{question}",
            tools=[{"type": "file_search", "vector_store_ids": vector_store_ids}],
        )
        retrieved_context = retrieval_response.output_text
    except Exception as e:
        return jsonify({"error": f"Retrieval step failed: {str(e)}"}), 500

    # Step 2: evaluate using skill
    evaluation_input = (
        "Design data (JSON):\n"
        + json.dumps(design_data, indent=2)
        + "\n\nRetrieved standard clauses:\n"
        + retrieved_context
        + "\n\nReturn the compliance report as strict JSON matching the output schema. "
        "No markdown fences. No prose. Only the JSON object."
    )

    skill_used = "fallback"
    try:
        if skill_id:
            try:
                eval_response = client.responses.create(
                    model=model,
                    instructions="Use the design-standard-checker skill.",
                    input=evaluation_input,
                    tools=_build_skill_tools(skill_id),
                )
                skill_used = "hosted"
            except Exception as tool_err:
                if "tool" in str(tool_err).lower() and (
                    "not supported" in str(tool_err).lower() or "400" in str(tool_err)
                ):
                    eval_response = client.responses.create(
                        model=model,
                        instructions=_load_skill_instructions(),
                        input=evaluation_input,
                    )
                else:
                    raise
        else:
            eval_response = client.responses.create(
                model=model,
                instructions=_load_skill_instructions(),
                input=evaluation_input,
            )
        raw_output = eval_response.output_text
    except Exception as e:
        return jsonify({"error": f"Evaluation step failed: {str(e)}"}), 500

    try:
        report = _parse_json_report(raw_output)
    except (json.JSONDecodeError, IndexError):
        report = {"raw": raw_output, "parse_error": "Response was not valid JSON"}

    overall_status = (
        report.get("overall_status", "needs_review") if isinstance(report, dict) else "needs_review"
    )

    return jsonify({
        "success": True,
        "overall_status": overall_status,
        "report": report,
        "retrieved_context": retrieved_context,
        "model": model,
        "skill_used": skill_used,
    }), 200
