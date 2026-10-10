"""Public constant-load comparison; versioned codes within FastAPI's detail envelope."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.api.validation import original_payload
from backend.app.db.session import get_db
from backend.app.schemas.what_if import (
    WhatIfErrorResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from backend.app.services.what_if import WhatIfError, compare

Database = Annotated[Session, Depends(get_db)]


class WhatIfRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def wrapped(request):
            try:
                return await handler(request)
            except WhatIfError as error:
                status, code, message, reasons = (
                    error.status,
                    error.code,
                    error.message,
                    error.reasons,
                )
            except (RequestValidationError, HTTPException):
                status, code, message, reasons = (
                    422,
                    "invalid_request",
                    "Request does not match what-if-request-1.0.0",
                    [],
                )
            except SQLAlchemyError:
                status, code, message, reasons = (
                    503,
                    "database_unavailable",
                    "What-if database operation unavailable",
                    [],
                )
            return JSONResponse(
                status_code=status,
                content={
                    "detail": {
                        "schema_version": "what-if-error-1.0.0",
                        "code": code,
                        "message": message,
                        "reasons": reasons,
                    }
                },
            )

        return wrapped


router = APIRouter(
    tags=["What-if"],
    route_class=WhatIfRoute,
    responses={
        status: {"model": WhatIfErrorResponse} for status in (404, 409, 422, 503)
    },
)


@router.post(
    "/api/v1/assets/{asset_id}/what-if",
    response_model=WhatIfResponse,
    dependencies=[Depends(original_payload)],
)
def what_if(asset_id: str, payload: WhatIfRequest, db: Database):
    return compare(db, asset_id, payload)
