import csv
import time
from ingest.event import Event

class CSVIngestor:
    def __init__(self, file_path: str, stream_name: str):
        self.file_path = file_path
        self.stream_name = stream_name

    def stream(self):
        with open(self.file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Event(
                    stream=self.stream_name,
                    event_time=float(row.get("timestamp", time.time())),
                    receive_time=time.time(),
                    payload=row
                )
