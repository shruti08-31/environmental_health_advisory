from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PollutantData:
    """
    Stores pollutant measurements.
    Values are optional because an API may not provide
    every pollutant.
    """

    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    o3: Optional[float] = None


@dataclass
class AQIData:
    """
    Common AQI data structure used by later modules.
    """

    location: str
    aqi: Optional[float] = None

    pollutants: PollutantData = field(
        default_factory=PollutantData
    )

    timestamp: Optional[str] = None

    source: str = "WAQI"

    # These fields will be filled by later health-logic modules.
    severity: Optional[str] = None
    guidance: Optional[str] = None


@dataclass
class APIResponse:
    """
    Common wrapper for successful or failed module responses.
    """

    success: bool

    data: Optional[AQIData] = None

    message: str = ""

    error: Optional[str] = None