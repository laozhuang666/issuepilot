from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from issuepilot import __version__
from issuepilot.config import get_settings
from issuepilot.errors import IssuePilotError
from issuepilot.models import AnalysisRequest, AnalysisResponse
from issuepilot.service import AnalysisService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.analysis_service = AnalysisService(get_settings())
    yield
    await app.state.analysis_service.close()


app = FastAPI(
    title="IssuePilot API",
    version=__version__,
    description="Turn public GitHub issues into evidence-backed implementation plans.",
    lifespan=lifespan,
)
app.mount("/ui", StaticFiles(directory=WEB_ROOT), name="ui")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "model_provider": settings.llm_provider,
        "agent_configured": settings.agent_enabled,
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(payload: AnalysisRequest, request: Request) -> AnalysisResponse:
    service: AnalysisService = request.app.state.analysis_service
    try:
        return await service.analyze(payload.issue_url)
    except IssuePilotError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
