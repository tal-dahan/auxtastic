import logging

from auxtastic.network.socket import socket


logging.basicConfig(format="[%(name)s] [%(levelname)s] >> %(message)s", level=logging.DEBUG)
soc = socket.socket(soc_type=socket.SOC_PCP, verbose=True)

soc.connect()
soc.send(b"hi")
soc.close()

print("bye")

