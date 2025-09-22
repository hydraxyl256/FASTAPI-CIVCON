from typing import List, Optional
import requests
from functools import lru_cache
from pydantic import BaseModel

class Location(BaseModel):
    id: str
    name: str

class UgandaLocaleComplete:
    def __init__(self):
        self.base_url = "https://raw.githubusercontent.com/paulgrammer/ug-locale/main"
        self.districts_data = []
        self.counties_data = []
        self.subcounties_data = []
        self.parishes_data = []
        self.villages_data = []
        self._load_data()

    def _load_data(self):
        try:
            print("Loading Uganda administrative data...")
            self.districts_data = requests.get(f"{self.base_url}/districts.json").json()
            self.counties_data = requests.get(f"{self.base_url}/counties.json").json()
            self.subcounties_data = requests.get(f"{self.base_url}/subcounties.json").json()
            self.parishes_data = requests.get(f"{self.base_url}/parishes.json").json()
            self.villages_data = requests.get(f"{self.base_url}/villages.json").json()
            print("All data loaded successfully!")
        except Exception as e:
            print(f"Error loading data: {e}")

    @lru_cache(maxsize=None)
    def get_districts(self) -> List[dict]:
        return [{"id": d["id"], "name": d["name"]} for d in self.districts_data]

    @lru_cache(maxsize=None)
    def get_counties(self, district_id: str) -> List[dict]:
        return [{"id": c["id"], "name": c["name"]} for c in self.counties_data if c["district"] == district_id]

    @lru_cache(maxsize=None)
    def get_sub_counties(self, county_id: str) -> List[dict]:
        return [{"id": sc["id"], "name": sc["name"]} for sc in self.subcounties_data if sc["county"] == county_id]

    @lru_cache(maxsize=None)
    def get_parishes(self, sub_county_id: str) -> List[dict]:
        return [{"id": p["id"], "name": p["name"]} for p in self.parishes_data if p["subcounty"] == sub_county_id]

    @lru_cache(maxsize=None)
    def get_villages(self, parish_id: str) -> List[dict]:
        return [{"id": v["id"], "name": v["name"]} for v in self.villages_data if v["parish"] == parish_id]

    def find_district_by_id(self, district_id: str) -> Optional[dict]:
        return next((d for d in self.districts_data if d["id"] == district_id), None)

    def find_county_by_id(self, county_id: str) -> Optional[dict]:
        return next((c for c in self.counties_data if c["id"] == county_id), None)

    def find_subcounty_by_id(self, subcounty_id: str) -> Optional[dict]:
        return next((sc for sc in self.subcounties_data if sc["id"] == subcounty_id), None)

    def find_parish_by_id(self, parish_id: str) -> Optional[dict]:
        return next((p for p in self.parishes_data if p["id"] == parish_id), None)

uga_locale = UgandaLocaleComplete()