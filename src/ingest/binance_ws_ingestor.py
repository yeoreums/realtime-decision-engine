import json
import time

from websocket import create_connection
from websocket._exceptions import WebSocketTimeoutException, WebSocketConnectionClosedException

from ingest.event import Event


class BinanceFuturesWSIngestor:
    def __init__(
        self,
        symbol: str = "btcusdt",
        base_url: str = "wss://fstream.binance.com",
        recv_timeout_sec: float = 5.0,
        streams: list[str] | None = None,
    ):
        self.symbol = symbol.lower()
        self.base_url = base_url.rstrip("/")
        self.recv_timeout_sec = recv_timeout_sec

        if streams is None:
            streams = [
                f"{self.symbol}@trade",
                f"{self.symbol}@depth@100ms",
                f"{self.symbol}@forceOrder",
                f"{self.symbol}@ticker",
            ]
        self.streams = streams

    def _url(self) -> str:
        joined = "/".join(self.streams)
        return f"{self.base_url}/stream?streams={joined}"

    @staticmethod
    def _map_stream(stream_name: str) -> str:
        s = stream_name.lower()
        if "@trade" in s:
            return "trade"
        if "@depth" in s:
            return "orderbook"
        if "@forceorder" in s:
            return "liquidation"
        if "@ticker" in s:
            return "ticker"
        return stream_name

    @staticmethod
    def _extract_event_time(data: dict) -> float:
        ts = data.get("T") or data.get("E")
        if ts is None:
            return time.time()
        try:
            ts_f = float(ts)
        except (TypeError, ValueError):
            return time.time()
        return ts_f / 1000.0 if ts_f > 1e12 else ts_f

    def stream(self):
        while True:
            ws = None
            try:
                ws = create_connection(self._url(), timeout=self.recv_timeout_sec)

                while True:
                    raw = ws.recv()
                    if not raw:
                        continue

                    msg = json.loads(raw)
                    stream_name = msg.get("stream", "")
                    data = msg.get("data", msg)

                    yield Event(
                        stream=self._map_stream(stream_name),
                        event_time=self._extract_event_time(data),
                        receive_time=time.time(),
                        payload=data,
                    )

            except (WebSocketTimeoutException, WebSocketConnectionClosedException):
                pass
            except Exception:
                pass
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass
                time.sleep(1.0)
