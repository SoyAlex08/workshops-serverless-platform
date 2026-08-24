"""EventBridge-triggered handler: sends SNS notifications for workshop domain events."""
import json
import os

import boto3
from aws_lambda_powertools import Tracer

tracer = Tracer()
_sns = boto3.client("sns")
TOPIC_ARN = os.environ.get("NOTIFICATIONS_TOPIC_ARN", "")

MESSAGES = {
    "WORKSHOP_CREATED": lambda d: f"Nuevo taller creado: {d.get('name')} (inicia {d.get('startAt')})",
    "STUDENT_REGISTERED": lambda d: f"Inscripción confirmada al taller {d.get('workshopName')} para el usuario {d.get('userId')}",
    "WORKSHOP_REMINDER": lambda d: f"Recordatorio: el taller {d.get('workshopName')} inicia en 24 horas ({d.get('startAt')})",
    "WORKSHOP_DELETED": lambda d: f"Taller cancelado/eliminado: {d.get('workshopId')}",
}


@tracer.capture_lambda_handler
def handler(event, _context):
    detail_type = event.get("detail-type")
    detail = event.get("detail", {})

    builder = MESSAGES.get(detail_type)
    message = builder(detail) if builder else f"Evento {detail_type}: {json.dumps(detail)}"

    if TOPIC_ARN:
        _sns.publish(TopicArn=TOPIC_ARN, Subject=f"Workshops - {detail_type}", Message=message)

    return {"status": "notified", "detailType": detail_type}
