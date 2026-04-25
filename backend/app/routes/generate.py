from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.generation import VALID_OUTPUT_TYPES, get_generation_service

generate_bp = Blueprint("generate", __name__)


@generate_bp.post("/api/generate")
def generate_artifact():
    payload = request.get_json(silent=True) or {}

    query = payload.get("query")
    output_type_raw = payload.get("output_type")
    output_type = output_type_raw.strip() if isinstance(output_type_raw, str) else None
    document_id = payload.get("document_id")

    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "Field 'query' is required and must be a non-empty string."}), 400

    if output_type_raw is not None and output_type not in VALID_OUTPUT_TYPES:
        return (
            jsonify({"error": "Field 'output_type' must be one of: quiz, flashcards, study_plan."}),
            400,
        )

    generation_service = get_generation_service()

    try:
        generation_result = generation_service.generate(
            query=query.strip(),
            output_type=output_type,
            document_id=document_id if isinstance(document_id, str) else None,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"status": "success", "data": generation_result}), 200
