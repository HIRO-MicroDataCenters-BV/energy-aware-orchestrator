"""
Repository for energy availability data access operations.
"""

from typing import List, Optional
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import and_, desc, asc, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.energy_availability import EnergyAvailability
import logging

logger = logging.getLogger(__name__)


def _prefer_real_supply(rows: List[EnergyAvailability]) -> List[EnergyAvailability]:
    """Collapse real+predicted rows for the same slot down to one.

    Real and predicted supply can now coexist as independent rows for the
    same (provider_name, slot_start_time, slot_end_time) - by design, so
    grid polling and forecasting never fight over the same row. But a
    caller adding up "available capacity" must never see both, or it
    double-counts a slot that has both a real reading and a leftover
    prediction for it. Real always wins when both exist; predicted is only
    used to fill a genuine gap. Order of first occurrence is preserved.
    """
    best = {}
    for row in rows:
        key = (row.provider_name, row.slot_start_time, row.slot_end_time)
        existing = best.get(key)
        if existing is None or (existing.data_source != "real" and row.data_source == "real"):
            best[key] = row
    return list(best.values())


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
            return _prefer_real_supply(result.scalars().all())

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
            return _prefer_real_supply(result.scalars().all())
            
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

    async def upsert_demand(
        self,
        identifier: str,
        slot_start_time: datetime,
        slot_end_time: datetime,
        required_watts: float,
        forecast_date: date,
    ) -> EnergyAvailability:
        """
        Create or replace the single current demand row for a CR.

        `identifier` is '<namespace>/<name>' of the EAO CR, stored in
        provider_name. One demand row per identifier - a fresh call always
        replaces the previous one via the partial unique index on
        provider_name WHERE record_type = 'demand', matching how the
        operator only ever reports its single current decision per CR, not
        an accumulating history. A real upsert (single statement) rather
        than delete-then-insert, so an unchanged report costs one indexed
        write instead of two.
        """
        try:
            stmt = pg_insert(EnergyAvailability).values(
                provider_name=identifier,
                slot_start_time=slot_start_time,
                slot_end_time=slot_end_time,
                available_watts=required_watts,
                forecast_date=forecast_date,
                is_active=True,
                record_type="demand",
                data_source="real",
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["provider_name"],
                index_where=text("record_type = 'demand'"),
                set_={
                    "slot_start_time": stmt.excluded.slot_start_time,
                    "slot_end_time": stmt.excluded.slot_end_time,
                    "available_watts": stmt.excluded.available_watts,
                    "forecast_date": stmt.excluded.forecast_date,
                    "is_active": True,
                },
            )
            await self.db.execute(stmt)
            await self.db.commit()

            # populate_existing forces a fresh read of any already-loaded
            # instance for this row in the session's identity map. Without
            # it, a caller reusing this session across multiple upserts for
            # the same identifier would get back the pre-update object,
            # since the ON CONFLICT UPDATE above runs as a Core statement
            # and doesn't go through the ORM's usual expire-on-write path.
            result = await self.db.execute(
                select(EnergyAvailability)
                .where(
                    EnergyAvailability.provider_name == identifier,
                    EnergyAvailability.record_type == "demand",
                )
                .execution_options(populate_existing=True)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error upserting demand record for {identifier}: {e}")
            await self.db.rollback()
            raise

    async def upsert_supply(
        self,
        provider_name: str,
        slot_start_time: datetime,
        slot_end_time: datetime,
        available_watts: float,
        forecast_date: date,
        location: Optional[str] = None,
        energy_source_type: Optional[str] = None,
        confidence_percentage: Optional[float] = None,
    ) -> EnergyAvailability:
        """
        Create or replace a polled *real* supply slot for a provider.

        One row per (provider_name, slot_start_time, slot_end_time,
        data_source), matching the partial unique index on those columns
        WHERE record_type = 'supply'. data_source is fixed to 'real' here
        (see upsert_predicted_supply() for the predicted counterpart) so
        this can only ever conflict with - and update - a previous real row
        for the same slot, never a prediction. Repeated polls that return
        the same slot update it in place instead of accumulating duplicate
        rows, the same reasoning as upsert_demand() but keyed on the slot
        too since a single poll cycle can return many slots for the same
        provider.
        """
        try:
            stmt = pg_insert(EnergyAvailability).values(
                provider_name=provider_name,
                location=location,
                energy_source_type=energy_source_type,
                slot_start_time=slot_start_time,
                slot_end_time=slot_end_time,
                available_watts=available_watts,
                confidence_percentage=confidence_percentage,
                forecast_date=forecast_date,
                is_active=True,
                record_type="supply",
                data_source="real",
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["provider_name", "slot_start_time", "slot_end_time", "data_source"],
                index_where=text("record_type = 'supply'"),
                set_={
                    "location": stmt.excluded.location,
                    "energy_source_type": stmt.excluded.energy_source_type,
                    "available_watts": stmt.excluded.available_watts,
                    "confidence_percentage": stmt.excluded.confidence_percentage,
                    "forecast_date": stmt.excluded.forecast_date,
                    "is_active": True,
                },
            )
            await self.db.execute(stmt)
            await self.db.commit()

            result = await self.db.execute(
                select(EnergyAvailability)
                .where(
                    EnergyAvailability.provider_name == provider_name,
                    EnergyAvailability.slot_start_time == slot_start_time,
                    EnergyAvailability.slot_end_time == slot_end_time,
                    EnergyAvailability.record_type == "supply",
                    EnergyAvailability.data_source == "real",
                )
                .execution_options(populate_existing=True)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error upserting supply record for {provider_name}: {e}")
            await self.db.rollback()
            raise

    async def upsert_predicted_supply(
        self,
        provider_name: str,
        slot_start_time: datetime,
        slot_end_time: datetime,
        available_watts: float,
        forecast_date: date,
        location: Optional[str] = None,
        energy_source_type: Optional[str] = None,
        confidence_percentage: Optional[float] = None,
    ) -> EnergyAvailability:
        """
        Create or refresh a predicted supply slot for a provider.

        Same shape as upsert_supply(), but data_source is fixed to
        'predicted', so this can only ever conflict with - and update - a
        previous prediction for the same slot, never real data. Structurally
        independent from upsert_supply() thanks to data_source being part of
        the unique index: real and predicted rows for the same slot coexist
        rather than overwriting each other.
        """
        try:
            stmt = pg_insert(EnergyAvailability).values(
                provider_name=provider_name,
                location=location,
                energy_source_type=energy_source_type,
                slot_start_time=slot_start_time,
                slot_end_time=slot_end_time,
                available_watts=available_watts,
                confidence_percentage=confidence_percentage,
                forecast_date=forecast_date,
                is_active=True,
                record_type="supply",
                data_source="predicted",
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["provider_name", "slot_start_time", "slot_end_time", "data_source"],
                index_where=text("record_type = 'supply'"),
                set_={
                    "location": stmt.excluded.location,
                    "energy_source_type": stmt.excluded.energy_source_type,
                    "available_watts": stmt.excluded.available_watts,
                    "confidence_percentage": stmt.excluded.confidence_percentage,
                    "forecast_date": stmt.excluded.forecast_date,
                    "is_active": True,
                },
            )
            await self.db.execute(stmt)
            await self.db.commit()

            result = await self.db.execute(
                select(EnergyAvailability)
                .where(
                    EnergyAvailability.provider_name == provider_name,
                    EnergyAvailability.slot_start_time == slot_start_time,
                    EnergyAvailability.slot_end_time == slot_end_time,
                    EnergyAvailability.record_type == "supply",
                    EnergyAvailability.data_source == "predicted",
                )
                .execution_options(populate_existing=True)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error upserting predicted supply record for {provider_name}: {e}")
            await self.db.rollback()
            raise

    async def get_distinct_real_supply_providers(self) -> List[str]:
        """Providers with active real supply history, so the forecaster
        knows who it has enough data to predict for."""
        try:
            query = select(EnergyAvailability.provider_name).distinct().where(
                EnergyAvailability.record_type == "supply",
                EnergyAvailability.data_source == "real",
                EnergyAvailability.is_active == True,
            )
            result = await self.db.execute(query)
            return [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Error retrieving distinct real supply providers: {e}")
            raise

    async def get_supply_history(
        self,
        provider_name: str,
        lookback_days: int = 14,
    ) -> List[EnergyAvailability]:
        """Real supply history for a provider within the lookback window,
        for the predictor to learn from."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            query = select(EnergyAvailability).where(
                EnergyAvailability.provider_name == provider_name,
                EnergyAvailability.record_type == "supply",
                EnergyAvailability.data_source == "real",
                EnergyAvailability.is_active == True,
                EnergyAvailability.slot_start_time >= cutoff,
            ).order_by(asc(EnergyAvailability.slot_start_time))
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error retrieving supply history for {provider_name}: {e}")
            raise

    async def delete_demand(self, identifier: str) -> bool:
        """Deactivate the demand row for a CR (soft delete, matching delete()).

        Filters on is_active == True too, not just provider_name/record_type -
        an UPDATE ... SET is_active = False counts a row as affected even when
        it's already False, since Postgres matches on the WHERE clause alone.
        Without this, calling delete twice would report success both times
        instead of the second call correctly finding nothing left to delete.
        """
        try:
            stmt = (
                update(EnergyAvailability)
                .where(
                    EnergyAvailability.provider_name == identifier,
                    EnergyAvailability.record_type == "demand",
                    EnergyAvailability.is_active == True,
                )
                .values(is_active=False)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting demand record for {identifier}: {e}")
            await self.db.rollback()
            raise