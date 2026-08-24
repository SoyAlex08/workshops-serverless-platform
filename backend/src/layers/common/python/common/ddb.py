"""DynamoDB single-table access helpers for the workshops table."""
import os
import boto3

_dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "")


def table():
    return _dynamodb.Table(TABLE_NAME)


def workshop_pk(workshop_id):
    return f"WORKSHOP#{workshop_id}"


def user_pk(user_id):
    return f"USER#{user_id}"


def registration_sk(user_id):
    return f"REG#USER#{user_id}"
