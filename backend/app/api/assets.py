"""Public registry routes; database failures never leak driver messages."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.assets import (
    AssetCreate,
    AssetPage,
    AssetResponse,
    ConfigurationCreate,
    ConfigurationPage,
    ConfigurationResponse,
)
from backend.app.services import assets

router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])


def registry_db(db: Annotated[Session, Depends(get_db)]):
    try:
        yield db
    except assets.AssetNotFound:
        db.rollback()
        raise HTTPException(404, "Asset not found") from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Asset ID or configuration version already exists"
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Registry database operation unavailable") from None


Database = Annotated[Session, Depends(registry_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.post("", response_model=AssetResponse, status_code=201)
def create_asset(payload: AssetCreate, db: Database):
    return assets.create_asset(db, payload)


@router.get("", response_model=AssetPage)
def list_assets(db: Database, limit: Limit = 20, offset: Offset = 0):
    return AssetPage(
        items=assets.list_assets(db, limit, offset), limit=limit, offset=offset
    )


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, db: Database):
    return assets.asset_response(db, assets.require_asset(db, asset_id))


@router.post(
    "/{asset_id}/configurations", response_model=ConfigurationResponse, status_code=201
)
def create_configuration(asset_id: str, payload: ConfigurationCreate, db: Database):
    return assets.create_configuration(db, asset_id, payload)


@router.get("/{asset_id}/configurations", response_model=ConfigurationPage)
def configuration_history(
    asset_id: str, db: Database, limit: Limit = 20, offset: Offset = 0
):
    return ConfigurationPage(
        items=assets.configuration_history(db, asset_id, limit, offset),
        limit=limit,
        offset=offset,
    )
