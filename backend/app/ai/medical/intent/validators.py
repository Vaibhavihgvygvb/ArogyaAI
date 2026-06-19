from app.ai.medical.exceptions.query_exceptions import ValidationError


def validate_query(query: str) -> str:
    cleaned = query.strip()
    if not cleaned:
        raise ValidationError("Query cannot be empty")
    if len(cleaned) > 10000:
        raise ValidationError("Query exceeds maximum length of 10000 characters")
    return cleaned
