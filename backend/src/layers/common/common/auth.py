"""Helpers to read Cognito JWT claims injected by API Gateway's Cognito authorizer."""


def get_claims(event):
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
        or {}
    )


def get_user_id(event):
    claims = get_claims(event)
    return claims.get("sub")


def get_groups(event):
    claims = get_claims(event)
    groups = claims.get("cognito:groups", "")
    if isinstance(groups, str):
        return [g for g in groups.strip("[]").replace(" ", "").split(",") if g]
    return groups or []


def is_admin(event):
    return "admin" in get_groups(event)
