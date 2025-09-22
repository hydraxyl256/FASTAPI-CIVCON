from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from ..ug_locale import uga_locale, Location

router = APIRouter(prefix="/locations", tags=["Locations"])

class Location(BaseModel):
    id: str
    name: str

@router.get("/districts", response_model=List[Location])
async def get_districts():
    return uga_locale.get_districts()

@router.get("/counties/{district_id}", response_model=List[Location])
async def get_counties(district_id: str):
    district = uga_locale.find_district_by_id(district_id)
    if not district:
        raise HTTPException(status_code=404, detail=f"District with id '{district_id}' not found")
    return uga_locale.get_counties(district_id)

@router.get("/sub-counties/{county_id}", response_model=List[Location])
async def get_sub_counties(county_id: str):
    county = uga_locale.find_county_by_id(county_id)
    if not county:
        raise HTTPException(status_code=404, detail=f"County with id '{county_id}' not found")
    sub_counties = uga_locale.get_sub_counties(county_id)
    if not sub_counties:
        raise HTTPException(status_code=404, detail=f"No sub-counties found for county id '{county_id}'")
    return sub_counties

@router.get("/parishes/{sub_county_id}", response_model=List[Location])
async def get_parishes(sub_county_id: str):
    subcounty = uga_locale.find_subcounty_by_id(sub_county_id)
    if not subcounty:
        raise HTTPException(status_code=404, detail=f"Sub-county with id '{sub_county_id}' not found")
    parishes = uga_locale.get_parishes(sub_county_id)
    if not parishes:
        raise HTTPException(status_code=404, detail=f"No parishes found for sub-county id '{sub_county_id}'")
    return parishes

@router.get("/villages/{parish_id}", response_model=List[Location])
async def get_villages(parish_id: str):
    parish = uga_locale.find_parish_by_id(parish_id)
    if not parish:
        raise HTTPException(status_code=404, detail=f"Parish with id '{parish_id}' not found")
    villages = uga_locale.get_villages(parish_id)
    if not villages:
        raise HTTPException(status_code=404, detail=f"No villages found for parish id '{parish_id}'")
    return villages