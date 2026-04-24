from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.services.ingestion import get_ingestion_service

upload_bp = Blueprint("upload", __name__)


def _is_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"


@upload_bp.post("/api/upload")
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request. Use form-data key 'file'."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "No file selected."}), 400

    if not _is_pdf(uploaded_file.filename):
        return jsonify({"error": "Only PDF files are supported for this endpoint."}), 400

    document_id = str(uuid4())
    safe_filename = secure_filename(uploaded_file.filename)

    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    saved_path = upload_dir / f"{document_id}-{safe_filename}"
    uploaded_file.save(saved_path)

    ingestion_service = get_ingestion_service()

    try:
        ingestion_result = ingestion_service.ingest_pdf(
            saved_path=saved_path,
            original_filename=safe_filename,
            document_id=document_id,
        )
    except ValueError as exc:
        saved_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 400
    except (OSError, RuntimeError, TypeError) as exc:
        current_app.logger.exception("Failed to ingest uploaded file: %s", safe_filename)
        saved_path.unlink(missing_ok=True)
        return (
            jsonify(
                {
                    "error": "Unexpected ingestion error.",
                    "details": str(exc),
                }
            ),
            500,
        )

    saved_path.unlink(missing_ok=True)

    return jsonify({"status": "success", "data": ingestion_result}), 201
