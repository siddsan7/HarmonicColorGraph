"""Database-independent v2 analysis endpoint."""

from fastapi import APIRouter, HTTPException

from app.schemas.analysis_v2 import AnalysisV2, AnalyzeV2Request
from app.theory.roman import analyze_v2

router = APIRouter(prefix="/v2", tags=["analysis-v2"])


@router.post("/analyze", response_model=AnalysisV2)
def analyze_endpoint(request: AnalyzeV2Request) -> AnalysisV2:
    try:
        return analyze_v2(request.chords, request.key, request.section_markers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
