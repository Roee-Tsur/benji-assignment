"""Every error leaves the API as an RFC 9457 `application/problem+json` document."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from webhooks.services.errors import (
    IdempotencyKeyReusedError,
    NotFoundError,
    NotReplayableError,
    PayloadTooLargeError,
)

PROBLEM_MEDIA_TYPE = "application/problem+json"


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationProblem(Problem):
    errors: list[ValidationIssue]


def problem_response(
    status: int,
    detail: str | None = None,
    *,
    title: str | None = None,
    headers: Mapping[str, str] | None = None,
    **extensions: Any,
) -> JSONResponse:
    problem = {"type": "about:blank", "title": title or HTTPStatus(status).phrase, "status": status}
    if detail is not None:
        problem["detail"] = detail
    return JSONResponse(
        {**problem, **extensions},
        status_code=status,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI declarations for a route's error responses (see `use_problem_media_type`)."""
    return {
        status: {
            "model": ValidationProblem if status == 422 else Problem,
            "description": HTTPStatus(status).phrase,
        }
        for status in statuses
    }


def use_problem_media_type(schema: dict[str, Any]) -> dict[str, Any]:
    """FastAPI documents every response model as `application/json`; errors are problem+json."""
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            for status, response in operation.get("responses", {}).items():
                content = response.get("content", {})
                if int(status) >= 400 and "application/json" in content:
                    content[PROBLEM_MEDIA_TYPE] = content.pop("application/json")
    return schema


def install_problem_handlers(app: FastAPI) -> None:
    async def http_error(_request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, HTTPException)
        phrase = HTTPStatus(error.status_code).phrase
        detail = None if error.detail == phrase else str(error.detail)
        return problem_response(error.status_code, detail, headers=error.headers)

    async def validation_error(_request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, RequestValidationError)
        issues = [
            {"loc": list(issue["loc"]), "msg": issue["msg"], "type": issue["type"]}
            for issue in error.errors()
        ]
        return problem_response(422, title="Request validation failed", errors=issues)

    async def not_found(_request: Request, error: Exception) -> JSONResponse:
        return problem_response(404, str(error))

    async def not_replayable(_request: Request, error: Exception) -> JSONResponse:
        return problem_response(409, str(error), title="Not replayable")

    async def idempotency_key_reused(_request: Request, error: Exception) -> JSONResponse:
        return problem_response(422, str(error), title="Idempotency key reused")

    async def payload_too_large(_request: Request, error: Exception) -> JSONResponse:
        return problem_response(413, str(error))

    async def unexpected(_request: Request, _error: Exception) -> JSONResponse:
        return problem_response(500)

    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(NotFoundError, not_found)
    app.add_exception_handler(NotReplayableError, not_replayable)
    app.add_exception_handler(IdempotencyKeyReusedError, idempotency_key_reused)
    app.add_exception_handler(PayloadTooLargeError, payload_too_large)
    app.add_exception_handler(Exception, unexpected)
