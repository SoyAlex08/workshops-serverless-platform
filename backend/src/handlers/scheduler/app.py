"""EventBridge Scheduler-triggered handler: finds workshops starting in ~24h and emits reminders."""
import time

from aws_lambda_powertools import Tracer
from boto3.dynamodb.conditions import Key

from common.ddb import table
from common.events import publish

tracer = Tracer()

REMINDER_WINDOW_SECONDS = 24 * 3600
WINDOW_TOLERANCE_SECONDS = 15 * 60  # scheduler runs every 15 min


@tracer.capture_lambda_handler
def handler(_event, _context):
    now = int(time.time())
    window_start = now + REMINDER_WINDOW_SECONDS - WINDOW_TOLERANCE_SECONDS
    window_end = now + REMINDER_WINDOW_SECONDS + WINDOW_TOLERANCE_SECONDS

    result = table().query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq("WORKSHOP#ALL") & Key("GSI1SK").between(window_start, window_end),
    )

    reminders_sent = 0
    for workshop in result.get("Items", []):
        if workshop.get("status") == "cancelled":
            continue

        registrations = table().query(
            KeyConditionExpression=Key("PK").eq(workshop["PK"]) & Key("SK").begins_with("REG#USER#")
        ).get("Items", [])

        for reg in registrations:
            publish(
                "WORKSHOP_REMINDER",
                {
                    "workshopId": workshop["id"],
                    "workshopName": workshop["name"],
                    "startAt": workshop["startAt"],
                    "userId": reg["userId"],
                },
            )
            reminders_sent += 1

    return {"workshopsChecked": len(result.get("Items", [])), "remindersSent": reminders_sent}
