"""Uniform API error handling. Stack traces are logged, never returned to clients."""
from __future__ import annotations

import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    """An expected, user-presentable error."""

    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.details = code, message, status, details or {}


def ok(data=None, status: int = 200):
    return jsonify({"success": True, "data": data if data is not None else {}}), status


def fail(code: str, message: str, status: int = 400, details: dict | None = None):
    body = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _app_error(e: AppError):
        return fail(e.code, e.message, e.status, e.details)

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        code = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}.get(e.code or 500, "http_error")
        msg = "The uploaded file is too large." if e.code == 413 else (e.description or "Request failed.")
        return fail(code, msg, e.code or 500)

    @app.errorhandler(Exception)
    def _unhandled(e: Exception):
        log.exception("unhandled_error")
        return fail("internal_error", "Something went wrong on the server. Please try again.", 500)
