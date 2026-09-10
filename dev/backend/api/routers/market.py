"""Market insights + role catalogue.

Phase 1: serves hardcoded data from api.stub_data.
Phase 2: swap the bodies for calls into api/services/market_insights.py.
"""
from ninja import Router

from api.schemas import MarketInsightsOut, RolesOut
from api.stub_data import MARKET_INSIGHTS, ROLES

router = Router()


@router.get("/market-insights", response=MarketInsightsOut)
def market_insights(request):
    return MARKET_INSIGHTS


@router.get("/roles", response=RolesOut)
def roles(request):
    return {"roles": ROLES}
