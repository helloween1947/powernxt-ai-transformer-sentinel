"""Database operations. Parent-row locking serializes writers per asset."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Asset, AssetConfiguration
from backend.app.schemas.assets import (
    AssetCreate,
    AssetResponse,
    ConfigurationCreate,
    ConfigurationResponse,
)


class AssetNotFound(Exception):
    pass


def require_asset(db: Session, asset_id: str, *, lock: bool = False) -> Asset:
    statement = select(Asset).where(Asset.asset_id == asset_id)
    if lock:
        statement = statement.with_for_update()
    asset = db.scalar(statement)
    if asset is None:
        raise AssetNotFound
    return asset


def asset_response(db: Session, asset: Asset) -> AssetResponse:
    current = db.scalar(
        select(AssetConfiguration)
        .where(AssetConfiguration.asset_id == asset.asset_id)
        .order_by(AssetConfiguration.version.desc())
        .limit(1)
    )
    response = AssetResponse.model_validate(asset)
    response.current_configuration = (
        ConfigurationResponse.model_validate(current) if current else None
    )
    return response


def create_asset(db: Session, payload: AssetCreate) -> AssetResponse:
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.flush()
    response = asset_response(db, asset)
    db.commit()
    return response


def list_assets(db: Session, limit: int, offset: int) -> list[AssetResponse]:
    assets = db.scalars(
        select(Asset).order_by(Asset.asset_id).limit(limit).offset(offset)
    )
    return [asset_response(db, asset) for asset in assets]


def create_configuration(
    db: Session, asset_id: str, payload: ConfigurationCreate
) -> ConfigurationResponse:
    # Acquire the parent lock BEFORE querying versions. PostgreSQL READ COMMITTED
    # gives the second statement a fresh snapshot after any preceding writer commits.
    require_asset(db, asset_id, lock=True)
    latest = (
        db.scalar(
            select(func.max(AssetConfiguration.version)).where(
                AssetConfiguration.asset_id == asset_id
            )
        )
        or 0
    )
    configuration = AssetConfiguration(
        asset_id=asset_id, version=latest + 1, **payload.model_dump(exclude_none=True)
    )
    db.add(configuration)
    db.flush()
    response = ConfigurationResponse.model_validate(configuration)
    db.commit()
    return response


def configuration_history(
    db: Session, asset_id: str, limit: int, offset: int
) -> list[ConfigurationResponse]:
    require_asset(db, asset_id)
    rows = db.scalars(
        select(AssetConfiguration)
        .where(AssetConfiguration.asset_id == asset_id)
        .order_by(AssetConfiguration.version)
        .limit(limit)
        .offset(offset)
    )
    return [ConfigurationResponse.model_validate(row) for row in rows]
