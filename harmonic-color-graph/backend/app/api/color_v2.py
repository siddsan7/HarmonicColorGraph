"""F43: database-independent progression color profile and compare API."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.color_v2 import ColorCompareResponse, ColorProfileRequest, ColorProfileResponse
from app.services.color_profile import compute_color_compare, compute_color_profile

router = APIRouter(prefix="/v2/color", tags=["color-v2"])


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("/profile", response_model=ColorProfileResponse)
def color_profile(request: ColorProfileRequest) -> ColorProfileResponse | JSONResponse:
    try:
        return compute_color_profile(request.progression, request.key)
    except ValueError as exc:
        return _error(422, "parse_error", str(exc))


@router.get("/compare", response_model=ColorCompareResponse)
def color_compare(
    a: str, b: str, key_a: str | None = None, key_b: str | None = None
) -> ColorCompareResponse | JSONResponse:
    try:
        profile_a, profile_b, raw_deltas, perceptual_deltas = compute_color_compare(
            a, key_a, b, key_b
        )
    except ValueError as exc:
        return _error(422, "parse_error", str(exc))
    return ColorCompareResponse(
        a=profile_a, b=profile_b, raw_deltas=raw_deltas, perceptual_deltas=perceptual_deltas
    )
