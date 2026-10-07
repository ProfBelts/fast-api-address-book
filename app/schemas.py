"""Pydantic models: input validation and response shapes."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]


class AddressIn(BaseModel):
    """Request body for creating or replacing an address."""

    model_config = ConfigDict(str_strip_whitespace=True)

    address: str = Field(min_length=1, max_length=500, examples=["Manila City Hall, Manila"])
    latitude: Latitude = Field(examples=[14.5896])
    longitude: Longitude = Field(examples=[120.9816])


class Address(AddressIn):
    id: int


class NearbyAddress(Address):
    distance_km: float


class NearbyQuery(BaseModel):
    """Query parameters for the distance search."""

    latitude: Latitude
    longitude: Longitude
    radius_km: float = Field(gt=0, allow_inf_nan=False, description="Search radius in km")
