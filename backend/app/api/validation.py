"""Reject nonfinite JSON before validation-error serialization."""

import json

from fastapi import HTTPException, Request


async def original_payload(request: Request):
    # Reject JSON's nonstandard NaN/Infinity tokens before validation errors can
    # try to serialize them; keep the original parsed object for auditing.
    def invalid_constant(value):
        raise ValueError("Non-finite JSON constant")

    try:
        original = json.loads(await request.body(), parse_constant=invalid_constant)
        json.dumps(original, allow_nan=False)  # Also rejects overflowing exponents.
        return original
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            422, "Payload must be valid JSON with finite numbers"
        ) from None
