"""
Energy availability model for storing energy forecast and availability data.
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Date, func
from sqlalchemy.ext.declarative import declarative_base
from app.models.base_dict_mixin import BaseDictMixin

Base = declarative_base()

class EnergyAvailability(Base, BaseDictMixin):
    """
    Model for energy availability predictions and forecasts.
    
    Stores information about available energy capacity from different providers,
    including renewable sources, weather dependencies, and forecast confidence.
    """
    __tablename__ = 'energy_availability'

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String(100), nullable=False, doc="Name of the energy provider")
    location = Column(String(255), nullable=True, doc="Geographic location of energy source")
    energy_source_type = Column(String(50), nullable=True, doc="Type of energy source (renewable, fossil, nuclear, etc.)")
    
    # Time slots for energy availability
    slot_start_time = Column(DateTime(timezone=True), nullable=False, doc="Start time of availability slot")
    slot_end_time = Column(DateTime(timezone=True), nullable=False, doc="End time of availability slot")
    
    # Energy capacity metrics
    available_watts = Column(Numeric(15, 4), nullable=False, doc="Available energy capacity in watts")
    guaranteed_minimum_watts = Column(Numeric(15, 4), nullable=True, doc="Minimum guaranteed energy capacity")
    potential_maximum_watts = Column(Numeric(15, 4), nullable=True, doc="Maximum potential energy capacity")
    
    # Forecast metadata
    confidence_percentage = Column(Numeric(5, 2), nullable=True, doc="Confidence level of forecast (0-100)")
    weather_dependency = Column(Boolean, default=False, doc="Whether availability depends on weather conditions")
    forecast_date = Column(Date, nullable=False, doc="Date when this forecast was made")
    
    # Status
    is_active = Column(Boolean, default=True, doc="Whether this availability record is active")
    created_at = Column(DateTime(timezone=True), default=func.now(), doc="Record creation timestamp")

    def __repr__(self):
        return (f"<EnergyAvailability(id={self.id}, provider='{self.provider_name}', "
                f"available_watts={self.available_watts}, slot_start='{self.slot_start_time}')>")

    def to_dict(self):
        """Convert model to dictionary representation"""
        return {
            'id': self.id,
            'provider_name': self.provider_name,
            'location': self.location,
            'energy_source_type': self.energy_source_type,
            'slot_start_time': self.slot_start_time.isoformat() if self.slot_start_time else None,
            'slot_end_time': self.slot_end_time.isoformat() if self.slot_end_time else None,
            'available_watts': float(self.available_watts) if self.available_watts else None,
            'guaranteed_minimum_watts': float(self.guaranteed_minimum_watts) if self.guaranteed_minimum_watts else None,
            'potential_maximum_watts': float(self.potential_maximum_watts) if self.potential_maximum_watts else None,
            'confidence_percentage': float(self.confidence_percentage) if self.confidence_percentage else None,
            'weather_dependency': self.weather_dependency,
            'forecast_date': self.forecast_date.isoformat() if self.forecast_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }