from typing import List

from django.shortcuts import get_object_or_404
from ninja import Router

from .models import Company
from .schemas import CompanyOut, ScreenResultOut
from .services import run_screening, serialize_result

router = Router()


@router.get("/companies", response=List[CompanyOut])
def list_companies(request):
    return Company.objects.all()


@router.get("/companies/{company_id}", response=CompanyOut)
def get_company(request, company_id: int):
    return get_object_or_404(Company, id=company_id)


@router.post("/screen/{company_id}", response=ScreenResultOut)
def screen_company(request, company_id: int):
    company = get_object_or_404(Company, id=company_id)
    run_screening(company)
    return serialize_result(company)


@router.get("/results/{company_id}", response=ScreenResultOut)
def get_results(request, company_id: int):
    company = get_object_or_404(Company, id=company_id)
    return serialize_result(company)
