"""CRUD handlers for /workshops."""
import time
import uuid

from aws_lambda_powertools import Tracer
from boto3.dynamodb.conditions import Key

from common import responses
from common.auth import is_admin
from common.ddb import table, workshop_pk
from common.events import publish

tracer = Tracer()

VALID_STATUS = {"scheduled", "cancelled"}
REQUIRED_FIELDS = ["name", "category", "location", "startAt", "endAt", "capacity"]
PAGE_SIZE = 20


def _validate(body):
    errors = []
    for field in REQUIRED_FIELDS:
        if not body.get(field):
            errors.append(f"'{field}' is required")
    if body.get("capacity") is not None:
        try:
            if int(body["capacity"]) <= 0:
                errors.append("'capacity' must be a positive integer")
        except (ValueError, TypeError):
            errors.append("'capacity' must be a positive integer")
    if body.get("status") and body["status"] not in VALID_STATUS:
        errors.append(f"'status' must be one of {sorted(VALID_STATUS)}")
    return errors


@tracer.capture_method
def list_workshops(event, _context):
    qs = event.get("queryStringParameters") or {}
    category = qs.get("category")
    limit = min(int(qs.get("limit", PAGE_SIZE)), 100)

    kwargs = {"Limit": limit, "ScanIndexForward": True}
    if qs.get("nextToken"):
        import base64
        import json

        kwargs["ExclusiveStartKey"] = json.loads(base64.b64decode(qs["nextToken"]))

    if category:
        kwargs["IndexName"] = "GSI2"
        kwargs["KeyConditionExpression"] = Key("GSI2PK").eq(f"CATEGORY#{category}")
    else:
        kwargs["IndexName"] = "GSI1"
        kwargs["KeyConditionExpression"] = Key("GSI1PK").eq("WORKSHOP#ALL")

    result = table().query(**kwargs)
    items = result.get("Items", [])

    next_token = None
    if "LastEvaluatedKey" in result:
        import base64
        import json

        next_token = base64.b64encode(json.dumps(result["LastEvaluatedKey"]).encode()).decode()

    return responses.ok({"items": items, "nextToken": next_token})


@tracer.capture_method
def get_workshop(event, _context):
    workshop_id = event["pathParameters"]["id"]
    result = table().get_item(Key={"PK": workshop_pk(workshop_id), "SK": "META"})
    item = result.get("Item")
    if not item:
        return responses.not_found(f"Workshop '{workshop_id}' not found")
    return responses.ok(item)


@tracer.capture_method
def create_workshop(event, _context):
    if not is_admin(event):
        return responses.forbidden("Admin role required")

    import json

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return responses.bad_request("Invalid JSON body")

    errors = _validate(body)
    if errors:
        return responses.bad_request("Validation failed", errors)

    workshop_id = str(uuid.uuid4())
    now = int(time.time())
    item = {
        "PK": workshop_pk(workshop_id),
        "SK": "META",
        "GSI1PK": "WORKSHOP#ALL",
        "GSI1SK": body["startAt"],
        "GSI2PK": f"CATEGORY#{body['category']}",
        "GSI2SK": body["startAt"],
        "id": workshop_id,
        "name": body["name"],
        "description": body.get("description", ""),
        "category": body["category"],
        "location": body["location"],
        "startAt": body["startAt"],
        "endAt": body["endAt"],
        "status": body.get("status", "scheduled"),
        "capacity": int(body["capacity"]),
        "createdAt": now,
        "updatedAt": now,
    }
    table().put_item(Item=item)
    publish("WORKSHOP_CREATED", {"workshopId": workshop_id, "name": item["name"], "startAt": item["startAt"]})
    return responses.ok(item, status=201)


@tracer.capture_method
def update_workshop(event, _context):
    if not is_admin(event):
        return responses.forbidden("Admin role required")

    workshop_id = event["pathParameters"]["id"]
    import json

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return responses.bad_request("Invalid JSON body")

    existing = table().get_item(Key={"PK": workshop_pk(workshop_id), "SK": "META"}).get("Item")
    if not existing:
        return responses.not_found(f"Workshop '{workshop_id}' not found")

    if body.get("status") and body["status"] not in VALID_STATUS:
        return responses.bad_request(f"'status' must be one of {sorted(VALID_STATUS)}")

    updatable = ["name", "description", "category", "location", "startAt", "endAt", "status", "capacity"]
    now = int(time.time())
    update_expr_parts = ["updatedAt = :updatedAt"]
    expr_values = {":updatedAt": now}

    for field in updatable:
        if field in body:
            update_expr_parts.append(f"{field} = :{field}")
            expr_values[f":{field}"] = body[field]

    if "category" in body:
        update_expr_parts.append("GSI2PK = :gsi2pk")
        expr_values[":gsi2pk"] = f"CATEGORY#{body['category']}"
    if "startAt" in body:
        update_expr_parts.append("GSI1SK = :gsi1sk, GSI2SK = :gsi2sk")
        expr_values[":gsi1sk"] = body["startAt"]
        expr_values[":gsi2sk"] = body["startAt"]

    table().update_item(
        Key={"PK": workshop_pk(workshop_id), "SK": "META"},
        UpdateExpression="SET " + ", ".join(update_expr_parts),
        ExpressionAttributeValues=expr_values,
    )

    updated = table().get_item(Key={"PK": workshop_pk(workshop_id), "SK": "META"}).get("Item")
    return responses.ok(updated)


@tracer.capture_method
def delete_workshop(event, _context):
    if not is_admin(event):
        return responses.forbidden("Admin role required")

    workshop_id = event["pathParameters"]["id"]
    existing = table().get_item(Key={"PK": workshop_pk(workshop_id), "SK": "META"}).get("Item")
    if not existing:
        return responses.not_found(f"Workshop '{workshop_id}' not found")

    table().delete_item(Key={"PK": workshop_pk(workshop_id), "SK": "META"})
    publish("WORKSHOP_DELETED", {"workshopId": workshop_id})
    return {"statusCode": 204, "headers": responses.CORS_HEADERS, "body": ""}


def route(event, context):
    """Single Lambda entry point routed by HTTP method + resource (see template.yaml)."""
    method = event.get("httpMethod")
    resource = event.get("resource", "")

    try:
        if resource == "/workshops" and method == "GET":
            return list_workshops(event, context)
        if resource == "/workshops" and method == "POST":
            return create_workshop(event, context)
        if resource == "/workshops/{id}" and method == "GET":
            return get_workshop(event, context)
        if resource == "/workshops/{id}" and method == "PUT":
            return update_workshop(event, context)
        if resource == "/workshops/{id}" and method == "DELETE":
            return delete_workshop(event, context)
        return responses.not_found("Route not found")
    except Exception as exc:  # noqa: BLE001 - top-level Lambda handler boundary
        tracer.put_annotation("error", str(exc))
        return responses.server_error(str(exc))
