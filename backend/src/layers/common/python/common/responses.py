"""Helpers to build API Gateway proxy responses, including RFC 7807 problem+json errors."""
import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def ok(body, status=200, extra_headers=None):
    headers = {"Content-Type": "application/json", **CORS_HEADERS, **(extra_headers or {})}
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def problem(status, title, detail=None, errors=None):
    """RFC 7807 problem+json error response."""
    payload = {"type": "about:blank", "title": title, "status": status}
    if detail:
        payload["detail"] = detail
    if errors:
        payload["errors"] = errors
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/problem+json", **CORS_HEADERS},
        "body": json.dumps(payload),
    }


def bad_request(detail, errors=None):
    return problem(400, "Bad Request", detail, errors)


def not_found(detail="Resource not found"):
    return problem(404, "Not Found", detail)


def forbidden(detail="Forbidden"):
    return problem(403, "Forbidden", detail)


def unauthorized(detail="Unauthorized"):
    return problem(401, "Unauthorized", detail)


def conflict(detail="Conflict"):
    return problem(409, "Conflict", detail)


def server_error(detail="Internal server error"):
    return problem(500, "Internal Server Error", detail)
