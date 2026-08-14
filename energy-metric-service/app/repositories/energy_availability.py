"""
Repository for energy availability data access operations.
"""

from typing import List, Optional
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.energy_availability import EnergyAvailability
import logging

logger = logging.getLogger(__name__)

class EnergyAvailabilityRepository:
    """Repository for managing energy availability data"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_all(
        self,
        provider_name: Optional[str] = None,
        location: Optional[str] = None,
        energy_source_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        forecast_date: Optional[date] = None,
        is_active: Optional[bool] = True,
        limit: int = 1000,
        order_by: str = "slot_start_time",
        order_direction: str = "desc"
    ) -> List[EnergyAvailability]:
        """
        Get energy availability records with optional filtering.
        
        Args:
            provider_name: Filter by energy provider name
            location: Filter by location
            energy_source_type: Filter by energy source type
            start_time: Filter records with slot_start_time >= this value
            end_time: Filter records with slot_end_time <= this value
            forecast_date: Filter by forecast date
            is_active: Filter by active status
            limit: Maximum number of records to return
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            List of EnergyAvailability records
        """
        try:
            query = select(EnergyAvailability)
            
            # Apply filters
            conditions = []
            
            if provider_name:
                conditions.append(EnergyAvailability.provider_name.ilike(f"%{provider_name}%"))
                
            if location:
                conditions.append(EnergyAvailability.location.ilike(f"%{location}%"))
                
            if energy_source_type:
                conditions.append(EnergyAvailability.energy_source_type.ilike(f"%{energy_source_type}%"))
                
            if start_time and end_time:
                # Include slots that overlap with the time range:
                # - Slot ends after or at start_time (to include currently active slots)
                # - Slot starts before or at end_time (to include future slots within range)
                conditions.append(EnergyAvailability.slot_end_time >= start_time)
                conditions.append(EnergyAvailability.slot_start_time <= end_time)
            elif start_time:
                # Only start_time specified: include slots that end at or after start_time
                conditions.append(EnergyAvailability.slot_end_time >= start_time)
            elif end_time:
                # Only end_time specified: include slots that start at or before end_time
                conditions.append(EnergyAvailability.slot_start_time <= end_time)
                
            if forecast_date:
                conditions.append(EnergyAvailability.forecast_date == forecast_date)
                
            if is_active is not None:
                conditions.append(EnergyAvailability.is_active == is_active)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply ordering
            order_field = getattr(EnergyAvailability, order_by, EnergyAvailability.slot_start_time)
            if order_direction.lower() == "asc":
                query = query.order_by(asc(order_field))
            else:
                query = query.order_by(desc(order_field))
            
            # Apply limit
            query = query.limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving energy availability records: {e}")
            raise

    async def get_by_id(self, availability_id: int) -> Optional[EnergyAvailability]:
        """Get energy availability record by ID"""
        try:
            query = select(EnergyAvailability).where(EnergyAvailability.id == availability_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving energy availability record by ID {availability_id}: {e}")
            raise

    async def get_current_availability(
        self,
        provider_name: Optional[str] = None,
        limit: int = 100,
        record_type: str = "supply"
    ) -> List[EnergyAvailability]:
        """
        Get current energy availability (records where current time falls within slot time range).

        Args:
            provider_name: Filter by provider name
            limit: Maximum number of records
            record_type: 'supply' (default) or 'demand'. Defaulting to 'supply' keeps this
                capacity-sufficiency query from ever summing demand rows in as if they were
                available capacity.

        Returns:
            List of current availability records
        """
        try:
            now = datetime.now(timezone.utc)

            query = select(EnergyAvailability).where(
                and_(
                    EnergyAvailability.slot_start_time <= now,
                    EnergyAvailability.slot_end_time >= now,
                    EnergyAvailability.is_active == True,
                    EnergyAvailability.record_type == record_type
                )
            )
            
            if provider_name:
                query = query.where(EnergyAvailability.provider_name.ilike(f"%{provider_name}%"))
            
            query = query.order_by(desc(EnergyAvailability.available_watts)).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving current energy availability: {e}")
            raise

    async def get_future_availability(
        self,
        hours_ahead: int = 24,
        provider_name: Optional[str] = None,
        limit: int = 100,
        record_type: str = "supply"
    ) -> List[EnergyAvailability]:
        """
        Get future energy availability within specified hours.

        Args:
            hours_ahead: Number of hours to look ahead
            provider_name: Filter by provider name
            limit: Maximum number of records
            record_type: 'supply' (default) or 'demand'. Defaulting to 'supply' keeps the
                operator's forecast fetch from ever being handed demand rows as if they were
                available capacity.

        Returns:
            List of future availability records
        """
        try:
            now = datetime.now(timezone.utc)
            future_time = now.replace(microsecond=0) + \
                         timedelta(hours=hours_ahead)

            query = select(EnergyAvailability).where(
                and_(
                    EnergyAvailability.slot_start_time >= now,
                    EnergyAvailability.slot_start_time <= future_time,
                    EnergyAvailability.is_active == True,
                    EnergyAvailability.record_type == record_type
                )
            )
            
            if provider_name:
                query = query.where(EnergyAvailability.provider_name.ilike(f"%{provider_name}%"))
            
            query = query.order_by(asc(EnergyAvailability.slot_start_time)).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving future energy availability: {e}")
            raise

    async def get_renewable_availability(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[EnergyAvailability]:
        """
        Get energy availability records filtered by renewable energy source types.
        
        Args:
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of records
            
        Returns:
            List of renewable energy availability records
        """
        try:
            # Filter by renewable energy source types
            renewable_types = ['solar', 'wind', 'hydro', 'renewable']
            query = select(EnergyAvailability).where(
                and_(
                    EnergyAvailability.energy_source_type.in_(renewable_types),
                    EnergyAvailability.is_active == True
                )
            )
            
            if start_time:
                query = query.where(EnergyAvailability.slot_start_time >= start_time)
                
            if end_time:
                query = query.where(EnergyAvailability.slot_end_time <= end_time)
            
            query = query.order_by(
                desc(EnergyAvailability.available_watts)
            ).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving renewable energy availability: {e}")
            raise

    async def get_summary_stats(self) -> dict:
        """Get summary statistics for energy availability data"""
        try:
            # This would need raw SQL for complex aggregations
            # For now, return basic counts
            total_query = select(EnergyAvailability).where(EnergyAvailability.is_active == True)
            total_result = await self.db.execute(total_query)
            total_records = len(total_result.scalars().all())
            
            return {
                "total_active_records": total_records,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error getting energy availability summary stats: {e}")
            raise

    async def create(self, availability_data: dict) -> EnergyAvailability:
        """Create new energy availability record"""
        try:
            availability = EnergyAvailability(**availability_data)
            self.db.add(availability)
            await self.db.commit()
            await self.db.refresh(availability)
            return availability
        except Exception as e:
            logger.error(f"Error creating energy availability record: {e}")
            await self.db.rollback()
            raise

    async def update(self, availability_id: int, update_data: dict) -> Optional[EnergyAvailability]:
        """Update energy availability record"""
        try:
            availability = await self.get_by_id(availability_id)
            if not availability:
                return None
                
            for key, value in update_data.items():
                if hasattr(availability, key):
                    setattr(availability, key, value)
            
            await self.db.commit()
            await self.db.refresh(availability)
            return availability
        except Exception as e:
            logger.error(f"Error updating energy availability record {availability_id}: {e}")
            await self.db.rollback()
            raise

    async def delete(self, availability_id: int) -> bool:
        """Delete energy availability record (soft delete by setting is_active=False)"""
        try:
            availability = await self.get_by_id(availability_id)
            if not availability:
                return False
                
            availability.is_active = False
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting energy availability record {availability_id}: {e}")
            await self.db.rollback()
            raise