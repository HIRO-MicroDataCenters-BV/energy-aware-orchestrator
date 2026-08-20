"""
Prediction Service - forecasts future supply from historical real supply.

Dummy implementation: averages historical real available_watts per 6-hour
slot-of-day bucket (matching the scheduler's own slot boundaries), and uses
that as the prediction for any future slot in the same bucket. Callers only
depend on predict()'s input/output shape, so swapping this out for a real ML
model later only touches this file.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# 6-hour slot-of-day buckets, matching energy-aware-operator's scheduler
# (slot boundaries 0-6, 6-12, 12-18, 18-24).
SLOT_BUCKETS = {1: (0, 6), 2: (6, 12), 3: (12, 18), 4: (18, 24)}


def _bucket_of(dt: datetime) -> int:
    hour = dt.hour
    for bucket, (start, end) in SLOT_BUCKETS.items():
        if start <= hour < end:
            return bucket
    return 4


class PredictionService:
    """Predicts future supply slots from historical real supply data."""

    def predict(
        self,
        history: List[Dict[str, Any]],
        future_slots: List[Tuple[datetime, datetime]],
    ) -> List[Dict[str, Any]]:
        """
        Args:
            history: real supply rows, each with 'slot_start_time' (datetime)
                and 'available_watts' (float). Recomputed from whatever real
                data exists right now - not a frozen trained model, so
                predictions improve as more real data accumulates via
                polling rather than repeating a fixed pattern forever.
            future_slots: (slot_start_time, slot_end_time) pairs to predict
                for.

        Returns:
            One {'slot_start_time', 'slot_end_time', 'available_watts'} dict
            per future slot whose bucket has historical data. Slots whose
            bucket has no history at all are skipped, not guessed at.
        """
        bucket_values: Dict[int, List[float]] = defaultdict(list)
        for row in history:
            bucket = _bucket_of(row["slot_start_time"])
            bucket_values[bucket].append(row["available_watts"])

        predictions = []
        for slot_start, slot_end in future_slots:
            values = bucket_values.get(_bucket_of(slot_start))
            if not values:
                continue
            predictions.append({
                "slot_start_time": slot_start,
                "slot_end_time": slot_end,
                "available_watts": sum(values) / len(values),
            })

        logger.debug(f"Predicted {len(predictions)}/{len(future_slots)} future slot(s) from {len(history)} history row(s)")
        return predictions
