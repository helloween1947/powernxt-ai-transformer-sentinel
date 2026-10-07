"""Import every model so Alembic can discover its metadata."""

from backend.app.models.assets import Asset, AssetConfiguration

__all__ = ["Asset", "AssetConfiguration"]
