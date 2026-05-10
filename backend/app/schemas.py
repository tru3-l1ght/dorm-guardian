from datetime import datetime

from pydantic import BaseModel, Field


class SensorReadingCreate(BaseModel):
    device_id: str = Field(min_length=3, max_length=64)
    temperature_c: float = Field(ge=-10, le=60)
    humidity_percent: float = Field(ge=0, le=100)
    air_quality: float = Field(ge=0, le=5000)


class SensorReadingOut(BaseModel):
    id: int
    device_id: str
    temperature_c: float
    humidity_percent: float
    air_quality: float
    created_at: datetime

    class Config:
        from_attributes = True