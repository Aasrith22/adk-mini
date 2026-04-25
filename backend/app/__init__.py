from __future__ import annotations

import logging

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.agents import build_agent_bundle
from app.config import Config
from app.routes.generate import generate_bp
from app.routes.upload import upload_bp


def create_app() -> Flask:
    load_dotenv()
    Config.ensure_directories()
    Config.validate_required_settings()

    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(level=logging.INFO)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(upload_bp)
    app.register_blueprint(generate_bp)

    adk_agents = build_agent_bundle(
        router_model=app.config["ADK_ROUTER_MODEL"],
        generator_model=app.config["ADK_GENERATION_MODEL"],
    )
    app.extensions["adk_agents"] = adk_agents
    app.extensions["adk_orchestrator"] = adk_agents.ingestion_orchestrator

    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "ok", "service": app.config["APP_NAME"]}), 200

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        if isinstance(exc, HTTPException):
            return exc

        app.logger.exception("Unhandled server error at path %s", request.path)

        if request.path.startswith("/api/"):
            return jsonify({"error": "Unhandled server error.", "details": str(exc)}), 500

        return jsonify({"error": "Unhandled server error."}), 500

    return app
