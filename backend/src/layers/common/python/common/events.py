"""Helpers to publish domain events to EventBridge."""
import json
import os
import boto3

_eventbridge = boto3.client("events")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")
EVENT_SOURCE = "workshops.api"


def publish(detail_type, detail: dict):
    _eventbridge.put_events(
        Entries=[
            {
                "Source": EVENT_SOURCE,
                "DetailType": detail_type,
                "Detail": json.dumps(detail),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )
