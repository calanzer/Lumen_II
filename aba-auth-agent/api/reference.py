"""Reference data the screens need: the payor list."""

from fastapi import APIRouter

from data import store
from pipeline.exporter import list_available_payors

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/payors")
def payors() -> list[dict]:
    return [
        {
            "key": key,
            "display_name": info["display_name"],
            "subtitle": info["subtitle"],
            "has_custom_template": store.get_active_template(key) is not None,
        }
        for key, info in list_available_payors().items()
    ]
