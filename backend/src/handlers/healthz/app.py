"""Public health-check endpoint used by CI/CD smoke tests."""
from common import responses


def handler(_event, _context):
    return responses.ok({"status": "ok"})
