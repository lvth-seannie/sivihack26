"""Request/response schemas.

Field names are camelCase on purpose: they are the API boundary and must match
the frontend contract in docs/BACKEND_SPEC.md §3 exactly.
"""
from typing import Literal, Optional

from ninja import Schema


class NamedPercentage(Schema):
    name: str
    percentage: int


class Trend(Schema):
    label: str
    percentage: int
    direction: Literal["up", "down"]


class MarketInsightsOut(Schema):
    updatedAt: Optional[str] = None
    topSkills: list[NamedPercentage]
    topRoles: list[NamedPercentage]
    topLocations: list[NamedPercentage]
    trends: list[Trend]


class RoleOut(Schema):
    id: str
    label: str
    requiredSkills: list[str]


class RolesOut(Schema):
    roles: list[RoleOut]


class AnalyzeIn(Schema):
    targetRole: str
    currentSkills: list[str]


class RoadmapStep(Schema):
    phase: str
    skill: str
    description: str


class AnalyzeOut(Schema):
    matchScore: int
    strengths: list[str]
    missingSkills: list[str]
    roadmap: list[RoadmapStep]
    recommendation: str


class HealthOut(Schema):
    status: str
