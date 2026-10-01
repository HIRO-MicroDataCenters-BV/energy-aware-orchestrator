"""
Common interface for grid supply sources.

Any source of live/near-live grid supply data - the HTTP grid API, a Modbus
PDU (or cluster), or a future third kind of source - implements this so
GridPollingScheduler can poll one or many of them interchangeably and store
whatever they return through the same EnergyAvailabilityRepository.upsert_supply
path.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GridSourceClient(ABC):
    """
    A pollable source of grid supply slots.

    Implementations are best-effort like the original GridAPIClient:
    failures are logged and swallowed, returning None, rather than raising -
    a bad poll cycle from one source should never crash the scheduler or
    stop other configured sources from being polled.
    """

    @abstractmethod
    async def fetch_grid_capacity(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch current/future supply slots from this source.

        Returns a list of dicts shaped like:
        {"slot_start_time": iso datetime str, "slot_end_time": iso datetime str,
         "available_watts": float, "provider_name": Optional[str],
         "location": Optional[str], "energy_source_type": Optional[str],
         "confidence_percentage": Optional[float]}

        This is the same envelope GridPollingScheduler._store_slots() already
        expects, so any implementation can be dropped in without scheduler
        changes.

        Returns None if this source is unavailable or returned nothing usable.
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Release any held resources (sockets, HTTP clients). No-op by default."""
        return None
