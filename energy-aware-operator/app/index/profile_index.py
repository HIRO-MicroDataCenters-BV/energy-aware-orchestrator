"""
AppProfileIndex — in-memory map from "<app_namespace>/<app_name>" to the
EnergyAwareOrchestration CR that targets that application.

Mirrors the controller-runtime ProfileByAppRefIndex field indexer pattern used
in the Go operator (RegisterProfileIndexes / profileByAppRefIndexFunc).

Key:   "<app_namespace>/<app_name>"
Value: EAO CR metadata + spec excerpt needed for scheduling decisions

Lifecycle:
- register()   called on CR create / update  (reconcile_handler)
- unregister() called on CR delete           (deletion_handler)
- lookup()     O(1) lookup given an app ref

The index is in-process only and is rebuilt automatically on operator restart
because Kopf replays all existing CRs through reconcile_handler at startup.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Index entry type alias for clarity
_Entry = Dict[str, Any]


class AppProfileIndex:
    """
    In-memory index mapping app refs to their EAO CR.

    Thread-safety: Kopf runs handlers in an asyncio event loop (single-threaded
    coroutine scheduler), so no locking is needed.
    """

    def __init__(self) -> None:
        self._index: Dict[str, _Entry] = {}

    def register(
        self,
        app_namespace: str,
        app_name: str,
        eao_name: str,
        eao_namespace: str,
        priority: str,
        energy_consumption: int,
        app_kind: str,
        app_api_version: str,
    ) -> None:
        """
        Add or overwrite the index entry for an app ref.

        Called from reconcile_handler after successful spec validation so the
        index always reflects the latest observed state of each EAO CR.
        """
        key = f"{app_namespace}/{app_name}"
        self._index[key] = {
            "eao_name": eao_name,
            "eao_namespace": eao_namespace,
            "priority": priority,
            "energy_consumption": energy_consumption,
            "app_kind": app_kind,
            "app_api_version": app_api_version,
        }
        logger.debug("AppProfileIndex: registered %s → %s/%s", key, eao_namespace, eao_name)

    def unregister(self, app_namespace: str, app_name: str) -> None:
        """
        Remove the index entry for an app ref.

        Called from deletion_handler when the EAO CR is deleted.
        Safe to call even if the key is absent (e.g. deleted before reconcile ran).
        """
        key = f"{app_namespace}/{app_name}"
        removed = self._index.pop(key, None)
        if removed:
            logger.debug("AppProfileIndex: unregistered %s", key)

    def lookup(self, app_namespace: str, app_name: str) -> Optional[_Entry]:
        """
        Return the EAO CR entry for a given app ref, or None if not tracked.

        Usage:
            entry = profile_index.lookup("default", "my-deployment")
            if entry:
                print(entry["priority"], entry["eao_name"])
        """
        return self._index.get(f"{app_namespace}/{app_name}")

    def all(self) -> Dict[str, _Entry]:
        """Return a snapshot of the full index (copy to avoid mutation)."""
        return dict(self._index)

    def __len__(self) -> int:
        return len(self._index)

    def __repr__(self) -> str:
        return f"AppProfileIndex({len(self._index)} entries)"


# Module-level singleton — one index per operator process.
_profile_index: Optional[AppProfileIndex] = None


def get_profile_index() -> AppProfileIndex:
    """Return the global AppProfileIndex singleton."""
    global _profile_index
    if _profile_index is None:
        _profile_index = AppProfileIndex()
    return _profile_index
