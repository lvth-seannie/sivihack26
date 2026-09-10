"""Market insights + role catalogue.

`GET /market-insights` is served from api/services/market_insights.py (job
dataset aggregation, cached, with a stub fallback). `GET /roles` is served
from the curated role map.
"""
from ninja import Router

from api.data.role_skill_map import role_catalogue
from api.schemas import MarketInsightsOut, RolesOut
from api.services import market_insights

router = Router()


@router.get("/market-insights", response=MarketInsightsOut)
def market_insights_view(request):
    return market_insights.get_insights()


@router.get("/roles", response=RolesOut)
def roles(request):
    return {"roles": role_catalogue()}
