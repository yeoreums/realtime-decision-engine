class Ingestor:
    def __init__(self, mode: str):
        self.mode = mode

    def stream(self):
        raise NotImplementedError
