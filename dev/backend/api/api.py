"""The single NinjaAPI instance, mounted at /api/ by core/urls.py."""
from ninja import NinjaAPI

from api.routers.analysis import router as analysis_router
from api.routers.market import router as market_router
from api.schemas import HealthOut

api = NinjaAPI(title="AI Career Navigator API", version="0.1.0")

api.add_router("", market_router)
api.add_router("", analysis_router)


@api.get("/health", response=HealthOut)
def health(request):
    return {"status": "ok"}
