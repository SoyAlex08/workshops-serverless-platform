import importlib
import json
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "layers", "common", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "handlers", "workshops"))


@pytest.fixture
def app_module():
    os.environ["TABLE_NAME"] = "workshops-test"
    os.environ["EVENT_BUS_NAME"] = "test-bus"
    with mock.patch("boto3.resource"), mock.patch("boto3.client"):
        module = importlib.import_module("app")
        importlib.reload(module)
        yield module


def _admin_event(method, resource, path_params=None, body=None):
    return {
        "httpMethod": method,
        "resource": resource,
        "pathParameters": path_params,
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {"authorizer": {"claims": {"sub": "admin-1", "cognito:groups": "[admin]"}}},
    }


def test_create_workshop_requires_admin(app_module):
    event = {
        "httpMethod": "POST",
        "resource": "/workshops",
        "pathParameters": None,
        "body": json.dumps({"name": "Taller X"}),
        "requestContext": {"authorizer": {"claims": {"sub": "student-1", "cognito:groups": "[student]"}}},
    }
    result = app_module.route(event, None)
    assert result["statusCode"] == 403


def test_create_workshop_validates_required_fields(app_module):
    event = _admin_event("POST", "/workshops", body={"name": "Taller X"})
    result = app_module.route(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "errors" in body


def test_route_not_found_returns_404(app_module):
    event = {"httpMethod": "PATCH", "resource": "/unknown", "pathParameters": None, "body": None}
    result = app_module.route(event, None)
    assert result["statusCode"] == 404
