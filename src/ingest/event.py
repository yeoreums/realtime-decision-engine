from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Event:
    stream: str          # trade, orderbook, liquidation, ticker
    event_time: float    # event timestamp
    receive_time: float  # processing time
    payload: Dict[str, Any]
