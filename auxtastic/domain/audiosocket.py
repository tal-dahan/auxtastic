class AudioSocket:
    def recv(self, buf_size: int) -> bytes:
        pass

    def send(self, data: bytes) -> None:
        pass

    def listen(self) -> None:
        pass

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    def accept(self):
        pass
