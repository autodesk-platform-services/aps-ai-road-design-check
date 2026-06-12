"""
OpenAI Skill Controller
Approach 3: two-step RAG retrieval + skill-guided evaluation.

Step 1  — file_search Responses API call to retrieve relevant standard clauses.
Step 2  — skill-guided Responses API call to evaluate design data against the
           retrieved clauses and return a structured JSON compliance report.

The skill instructions are loaded from Assets/design-standard-checker/SKILL.md.
If OPENAI_SKILL_ID is set, the hosted skill is attached via a shell/container
tool instead and SKILL.md is used only as a fallback.
"""

import json
import os
import pathlib

from flask import Blueprint, request, jsonify
from openai import OpenAI

_SKILL_MD_PATH = (
    pathlib.Path(__file__).parent.parent
    / "Assets"
    / "design-standard-checker"
    / "SKILL.md"
)

_RETRIEVAL_INSTRUCTIONS = (
    "You are a standards retrieval assistant. "
    "Given road design parameters, retrieve every relevant clause from the indexed documents. "
    "For each clause include its section number, page, and full verbatim text. "
    "Be comprehensive — include all potentially applicable requirements."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def _load_skill_instructions() -> str:
    try:
        return _SKILL_MD_PATH.read_text(encoding="utf-8")
    except OSError:
        return (
            "You are a road design compliance expert. "
            "Evaluate the provided design data against the retrieved standard clauses "
            "and return a strict JSON compliance report."
        )


def _build_skill_tools(skill_id: str | None) -> list:
    if not skill_id:
        return []
    return [
        {
            "type": "shell",
            "environment": {
                "type": "container_auto",
                "skills": [{"type": "skill_reference", "skill_id": skill_id}],
            },
        }
    ]


openai_skill_bp = Blueprint("openai_skill", __name__, url_prefix="/api/openai/skill")


@openai_skill_bp.route("/info", methods=["GET"])
def skill_info():
    """
    GET /api/openai/skill/info
    Returns whether a hosted skill ID is configured.
    """
    skill_id = os.getenv("OPENAI_SKILL_ID")
    return jsonify(
        {
            "skill_configured": bool(skill_id),
            "skill_id": skill_id or None,
            "fallback": "SKILL.md instructions" if not skill_id else None,
        }
    )


@openai_skill_bp.route("/query", methods=["POST"])
def query_with_skill():
    """
    POST /api/openai/skill/query
    Two-step compliance check:
      1. Retrieve relevant standard clauses from the vector store via file_search.
      2. Evaluate design data against retrieved clauses using skill instructions.

    Expects JSON:
    {
        "question": "Check the curves ... (units ft): Curve 1 Radius: 200 ft ...",
        "design_data": { "Curve 1": { "Radius": "200 ft", ... }, ... },
        "vector_store_id": "vs_..."   // optional; searches all stores if omitted
    }

    Returns JSON:
    {
        "success": true,
        "overall_status": "pass | fail | needs_review",
        "report": { ...output-schema... },
        "retrieved_context": "...",
        "model": "gpt-4o",
        "skill_used": "hosted | fallback"
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

    # Resolve vector store IDs
    try:
        if vector_store_id:
            vs = client.vector_stores.retrieve(vector_store_id)
            vector_store_ids = [vs.id]
        else:
            stores = client.vector_stores.list()
            vector_store_ids = [vs.id for vs in stores.data]
            if not vector_store_ids:
                return jsonify({"error": "No PDFs indexed yet. Use /api/openai/indexpdf first."}), 400
    except Exception as e:
        return jsonify({"error": f"Vector store error: {str(e)}"}), 404

    # Step 1: retrieve relevant standard clauses
    try:
        retrieval_response = client.responses.create(
            model="gpt-4o",
            instructions=_RETRIEVAL_INSTRUCTIONS,
            input=f"Retrieve standards relevant to:\n{question}",
            tools=[{"type": "file_search", "vector_store_ids": vector_store_ids}],
        )
        retrieved_context = retrieval_response.output_text
    except Exception as e:
        return jsonify({"error": f"Retrieval step failed: {str(e)}"}), 500

    # Step 2: evaluate using skill instructions
    skill_id = os.getenv("OPENAI_SKILL_ID")
    skill_tools = _build_skill_tools(skill_id)
    skill_instructions = (
        "Use the design-standard-checker skill."
        if skill_id
        else _load_skill_instructions()
    )
    skill_used = "hosted" if skill_id else "fallback"

    evaluation_input = (
        "Design data (JSON):\n"
        + json.dumps(design_data, indent=2)
        + "\n\nRetrieved standard clauses:\n"
        + retrieved_context
        + "\n\nReturn the compliance report as strict JSON matching the output schema. "
        "No markdown fences. No prose. Only the JSON object."
    )

    try:
        eval_response = client.responses.create(
            model="gpt-4o",
            instructions=skill_instructions,
            input=evaluation_input,
            tools=skill_tools if skill_tools else [],
        )
        raw_output = eval_response.output_text
    except Exception as e:
        return jsonify({"error": f"Evaluation step failed: {str(e)}"}), 500

    # Parse the structured JSON report
    report = None
    try:
        # Strip any accidental markdown fences if the model added them
        clean = raw_output.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        report = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        # Return raw text if parsing fails so the UI can still display something
        report = {"raw": raw_output, "parse_error": "Response was not valid JSON"}

    overall_status = report.get("overall_status", "needs_review") if isinstance(report, dict) else "needs_review"

    return jsonify(
        {
            "success": True,
            "overall_status": overall_status,
            "report": report,
            "retrieved_context": retrieved_context,
            "model": "gpt-4o",
            "skill_used": skill_used,
        }
    ), 200
