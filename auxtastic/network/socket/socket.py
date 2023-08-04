from auxtastic.domain.audiosocket import AudioSocket
from auxtastic.network.socket.pcpsocket import PCPSocket

SOC_PCP = 1


def socket(soc_type: int = SOC_PCP, *args, **kwargs) -> AudioSocket:
    if soc_type == SOC_PCP:
        return PCPSocket(*args, **kwargs)
    else:
        raise TypeError()
