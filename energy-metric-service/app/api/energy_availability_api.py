"""
API endpoints for Energy Availability management.

Provides complete CRUD operations and specialized queries for energy availability forecasts,
including renewable energy filtering, time-based queries, and summary statistics.
"""

from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.db.database import get_async_db
from app.repositories.energy_availability import EnergyAvailabilityRepository
from app.services.demand_resolution_service import resolve_demand_watts
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/energy-availability", tags=["Mock Energy Availability Service"])


# =============================================================================
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# =============================================================================

class EnergyAvailabilityCreate(BaseModel):
    """Schema for creating energy availability record"""
    provider_name: str = Field(..., description="Name of the energy provider", max_length=100)
    location: Optional[str] = Field(None, description="Geographic location of energy source", max_length=255)
    energy_source_type: Optional[str] = Field(None, description="Type of energy source (solar, wind, hydro, etc.)", max_length=50)
    slot_start_time: datetime = Field(..., description="Start time of availability slot")
    slot_end_time: datetime = Field(..., description="End time of availability slot")
    available_watts: float = Field(..., description="Available energy capacity in watts", gt=0)
    guaranteed_minimum_watts: Optional[float] = Field(None, description="Minimum guaranteed energy capacity", ge=0)
    potential_maximum_watts: Optional[float] = Field(None, description="Maximum potential energy capacity", ge=0)
    confidence_percentage: Optional[float] = Field(None, description="Confidence level of forecast (0-100)", ge=0, le=100)
    weather_dependency: bool = Field(False, description="Whether availability depends on weather conditions")
    forecast_date: date = Field(..., description="Date when this forecast was made")
    is_active: bool = Field(True, description="Whether this availability record is active")


class DemandReport(BaseModel):
    """
    Schema for reporting a workload's current energy demand.

    Written by energy-aware-operator once per EAO CR reconcile - one row per
    identifier, replacing whatever was reported for that CR last time.
    """
    identifier: str = Field(..., description="'<namespace>/<name>' of the EAO CR", max_length=100)
    slot_start_time: datetime = Field(..., description="Start of the CR's currently decided slot")
    slot_end_time: datetime = Field(..., description="End of the CR's currently decided slot")
    required_watts: float = Field(..., description="Fallback estimate in watts (spec.energyConsumption), used verbatim until real measurement/prediction is available", ge=0)
    application_name: Optional[str] = Field(
        None,
        max_length=100,
        description=(
            "spec.applicationRef.name - the Deployment this CR targets. "
            "Used to correlate with Kepler-measured pods (pod names are "
            "prefixed by their owning Deployment's name) for demand "
            "resolution. Omit to always use required_watts verbatim."
        ),
    )


class EnergyAvailabilityUpdate(BaseModel):
    """Schema for updating energy availability record"""
    provider_name: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    energy_source_type: Optional[str] = Field(None, max_length=50)
    slot_start_time: Optional[datetime] = None
    slot_end_time: Optional[datetime] = None
    available_watts: Optional[float] = Field(None, gt=0)
    guaranteed_minimum_watts: Optional[float] = Field(None, ge=0)
    potential_maximum_watts: Optional[float] = Field(None, ge=0)
    confidence_percentage: Optional[float] = Field(None, ge=0, le=100)
    weather_dependency: Optional[bool] = None
    forecast_date: Optional[date] = None
    is_active: Optional[bool] = None


# =============================================================================
# READ ENDPOINTS
# =============================================================================

@router.get("/", summary="Get all energy availability records")
async def get_energy_availability(
    provider_name: Optional[str] = Query(None, description="Filter by energy provider name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    energy_source_type: Optional[str] = Query(None, description="Filter by energy source type (solar, wind, etc.)"),
    hours_ahead: Optional[int] = Query(None, ge=1, le=168, description="Filter for slots starting within N hours"),
    is_active: bool = Query(True, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return (1-1000)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get energy availability forecasts with optional filtering.
    
    Returns information about available energy capacity from different providers,
    including renewable sources, weather dependencies, and forecast confidence.
    
    **Filters:**
    - `provider_name`: Partial match on provider name
    - `location`: Partial match on location
    - `energy_source_type`: Partial match on energy type (solar, wind, hydro, etc.)
    - `hours_ahead`: Get slots starting within the next N hours
    - `is_active`: Filter by active status (default: True)
    - `limit`: Maximum records to return (1-1000)
    """
    try:
        repository = EnergyAvailabilityRepository(db)

        # Calculate time filter if hours_ahead specified
        start_time = None
        end_time = None
        if hours_ahead:
            start_time = datetime.now().replace(tzinfo=None)
            end_time = (datetime.now() + timedelta(hours=hours_ahead)).replace(tzinfo=None)

        # Use ascending order when filtering by time range (chronological order)
        order_direction = "asc" if hours_ahead else "desc"

        availability_records = await repository.get_all(
            provider_name=provider_name,
            location=location,
            energy_source_type=energy_source_type,
            start_time=start_time,
            end_time=end_time,
            is_active=is_active,
            limit=limit,
            order_direction=order_direction
        )

        return {
            "status": "success",
            "filters": {
                "provider_name": provider_name,
                "location": location,
                "energy_source_type": energy_source_type,
                "hours_ahead": hours_ahead,
                "is_active": is_active,
                "limit": limit
            },
            "availability": [record.to_dict() for record in availability_records],
            "count": len(availability_records),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving energy availability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve energy availability: {str(e)}")


@router.get("/demand", summary="Get workload demand records (current and future)")
async def get_demand(
    identifier: Optional[str] = Query(None, description="Filter by '<namespace>/<name>' identifier"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get reported workload demand - both currently-active and future-scheduled
    slots. Each identifier has exactly one row for whatever slot it's
    currently decided to run in, which may itself be a future slot for
    Preferred/Optional workloads - so an unfiltered read already covers both
    current and future demand, not just "right now". Intended for external
    consumers (e.g. a grid operator) that need visibility into upcoming
    demand to plan supply ahead of time.

    Registered before /{availability_id} deliberately: that route matches
    any single path segment (including "demand") and is validated as an int
    only after matching, so if this were registered later, GET /demand
    would be caught by /{availability_id} first and fail with a 422 instead
    of ever reaching this handler.
    """
    try:
        repository = EnergyAvailabilityRepository(db)
        records = await repository.get_all(
            record_type="demand",
            provider_name=identifier,
            order_by="slot_start_time",
            order_direction="asc",
            limit=limit,
        )
        return {
            "status": "success",
            "filters": {"identifier": identifier, "limit": limit},
            "demand": [record.to_dict() for record in records],
            "count": len(records),
        }
    except Exception as e:
        logger.error(f"Error retrieving demand records: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve demand records: {str(e)}")


@router.get("/{availability_id}", summary="Get energy availability by ID")
async def get_energy_availability_by_id(
    availability_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a specific energy availability record by ID.
    
    Returns complete details of a single energy availability record.
    """
    try:
        repository = EnergyAvailabilityRepository(db)
        availability = await repository.get_by_id(availability_id)
        
        if not availability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Energy availability record with ID {availability_id} not found"
            )
        
        return {
            "status": "success",
            "availability": availability.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving energy availability by ID {availability_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve energy availability: {str(e)}")


@router.get("/current/active", summary="Get current active energy availability")
async def get_current_availability(
    provider_name: Optional[str] = Query(None, description="Filter by provider name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get current energy availability (slots active right now).
    
    Returns records where the current time falls within the slot time range (slot_start_time to slot_end_time).
    Results are ordered by available_watts (highest first).
    
    **Use case:** Find currently available energy sources for immediate deployment decisions.
    """
    try:
        repository = EnergyAvailabilityRepository(db)
        availability_records = await repository.get_current_availability(
            provider_name=provider_name,
            limit=limit
        )
        
        return {
            "status": "success",
            "query_time": datetime.utcnow().isoformat(),
            "filters": {
                "provider_name": provider_name,
                "limit": limit
            },
            "availability": [record.to_dict() for record in availability_records],
            "count": len(availability_records)
        }
    except Exception as e:
        logger.error(f"Error retrieving current energy availability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current energy availability: {str(e)}")


@router.get("/future/forecast", summary="Get future energy availability forecast")
async def get_future_availability(
    hours_ahead: int = Query(24, ge=1, le=168, description="Number of hours to look ahead (1-168)"),
    provider_name: Optional[str] = Query(None, description="Filter by provider name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get future energy availability within specified hours.
    
    Returns records for energy slots starting in the next N hours.
    Results are ordered chronologically by slot_start_time.
    
    **Use case:** Plan workload scheduling based on predicted energy availability.
    
    **Examples:**
    - `hours_ahead=24`: Get availability for the next 24 hours
    - `hours_ahead=168`: Get availability for the next week
    """
    try:
        repository = EnergyAvailabilityRepository(db)
        availability_records = await repository.get_future_availability(
            hours_ahead=hours_ahead,
            provider_name=provider_name,
            limit=limit
        )
        
        forecast_end_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        
        return {
            "status": "success",
            "forecast_window": {
                "start": datetime.utcnow().isoformat(),
                "end": forecast_end_time.isoformat(),
                "hours": hours_ahead
            },
            "filters": {
                "provider_name": provider_name,
                "limit": limit
            },
            "availability": [record.to_dict() for record in availability_records],
            "count": len(availability_records)
        }
    except Exception as e:
        logger.error(f"Error retrieving future energy availability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve future energy availability: {str(e)}")


@router.post("/demand", summary="Report a workload's current energy demand")
async def report_demand(
    demand: DemandReport,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create or replace the current demand record for a workload.

    One record per `identifier` - calling this again for the same
    identifier replaces its previous slot/wattage rather than accumulating
    a new row, since a workload only ever has one currently-decided slot.

    The stored wattage is resolved rather than used verbatim: measured
    Kepler wattage wins if available, an ML prediction from live
    utilization is used if measurement is momentarily missing, and
    `required_watts` is the fallback when neither exists yet (e.g. before
    the workload is deployed). See resolve_demand_watts().
    """
    try:
        namespace = demand.identifier.split("/", 1)[0]
        resolved_watts = await resolve_demand_watts(
            db=db,
            application_name=demand.application_name,
            namespace=namespace,
            fallback_watts=demand.required_watts,
        )

        repository = EnergyAvailabilityRepository(db)
        record = await repository.upsert_demand(
            identifier=demand.identifier,
            slot_start_time=demand.slot_start_time,
            slot_end_time=demand.slot_end_time,
            required_watts=resolved_watts,
            forecast_date=demand.slot_start_time.date(),
        )
        return {
            "status": "success",
            "demand": record.to_dict()
        }
    except Exception as e:
        logger.error(f"Error reporting demand for {demand.identifier}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to report demand: {str(e)}")


@router.delete("/demand/{identifier:path}", summary="Deactivate a workload's demand record")
async def delete_demand(
    identifier: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Deactivate the demand record for a workload (soft delete).

    `identifier` is '<namespace>/<name>' and may itself contain a slash,
    hence the `:path` converter.
    """
    try:
        repository = EnergyAvailabilityRepository(db)
        deleted = await repository.delete_demand(identifier)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"No demand record found for '{identifier}'")
        return {"status": "success", "identifier": identifier}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting demand for {identifier}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete demand: {str(e)}")