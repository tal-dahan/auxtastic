import ggwave
import pyaudio

import auxtastic.network.modem.config as config

# Encode Protocols (currently only FAST is supported)
# TX_NORMAL = 0
# TX_MEDIUM = 1
TX_FAST = 1

# Samples Rates
SAMPLE_RATE_FAST = 48000

# Defaults devices
DEFAULT_DEVICE_NAME = "default"


def get_device_by_name(interface, name: str = "", is_input: bool = False):
    if not name:
        return interface.get_default_input_device_info() if is_input else interface.get_default_output_device_info()

    all_devices = [interface.get_device_info_by_index(device_idx) for device_idx in range(interface.get_device_count())]
    try:
        device = next((device for device in all_devices if device['name'] == name))
        return device
    except StopIteration:
        raise ValueError(f"unknown device '{name}'")


class Modem:
    __TX_VOLUME = 100
    __FRAMES_PER_BUFFER = 1024
    __CHANNELS = 1

    def __init__(self):
        ggwave.disableLog()

        self.__interface = pyaudio.PyAudio()
        self.__input_device = get_device_by_name(self.__interface, config.INPUT_DEVICE_NAME, is_input=True)
        self.__input_stream = self.__interface.open(format=pyaudio.paFloat32,
                                                    channels=Modem.__CHANNELS,
                                                    rate=SAMPLE_RATE_FAST,
                                                    input=True,
                                                    input_device_index=self.__input_device.get("index"),
                                                    frames_per_buffer=Modem.__FRAMES_PER_BUFFER)
        self.__output_device = get_device_by_name(self.__interface, config.OUTPUT_DEVICE_NAME, is_input=False)
        self.__output_stream = self.__interface.open(format=pyaudio.paFloat32,
                                                     channels=Modem.__CHANNELS,
                                                     rate=SAMPLE_RATE_FAST,
                                                     output=True,
                                                     output_device_index=self.__output_device.get("index"),
                                                     frames_per_buffer=Modem.__FRAMES_PER_BUFFER)
        self.__convertor = ggwave.init()

    def __read_sync(self, buf_size) -> bytes:
        while True:
            raw_data = self.__input_stream.read(buf_size, exception_on_overflow=False)
            payload = ggwave.decode(self.__convertor, raw_data)

            if payload:
                return payload

    def recv(self, buf_size: int = 1024) -> bytes:
        try:
            data = self.__read_sync(buf_size)

            return data
        except Exception as e:
            raise e

    # tx_proto is currently not supported and only FAST is being used
    def send(self, data: bytes, tx_proto: int = TX_FAST) -> None:
        payload = ggwave.encode(Dummy(data), txProtocolId=TX_FAST, volume=Modem.__TX_VOLUME)
        self.__output_stream.write(payload, len(payload) // 4)


class Dummy:
    def __init__(self, data: bytes):
        self.data = data

    def encode(self):
        return self.data
