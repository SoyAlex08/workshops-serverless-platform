"""Handler for POST /workshops/{id}/register — idempotent student registration."""
import time

from aws_lambda_powertools import Tracer
from botocore.exceptions import ClientError

from common import responses
from common.auth import get_user_id
from common.ddb import table, workshop_pk, registration_sk
from common.events import publish

tracer = Tracer()


@tracer.capture_method
def register(event, _context):
    user_id = get_user_id(event)
    if not user_id:
        return responses.unauthorized("Valid Cognito JWT required")

    workshop_id = event["pathParameters"]["id"]

    workshop = table().get_item(Key={"PK": workshop_pk(workshop_id), "SK": "META"}).get("Item")
    if not workshop:
        return responses.not_found(f"Workshop '{workshop_id}' not found")
    if workshop.get("status") == "cancelled":
        return responses.conflict("Workshop is cancelled")

    now = int(time.time())
    try:
        table().put_item(
            Item={
                "PK": workshop_pk(workshop_id),
                "SK": registration_sk(user_id),
                "userId": user_id,
                "workshopId": workshop_id,
                "registeredAt": now,
            },
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return responses.conflict("Already registered for this workshop")
        raise

    publish(
        "STUDENT_REGISTERED",
        {"workshopId": workshop_id, "userId": user_id, "workshopName": workshop.get("name"), "startAt": workshop.get("startAt")},
    )
    return responses.ok({"workshopId": workshop_id, "userId": user_id, "registeredAt": now}, status=201)


def route(event, context):
    try:
        return register(event, context)
    except Exception as exc:  # noqa: BLE001
        tracer.put_annotation("error", str(exc))
        return responses.server_error(str(exc))
