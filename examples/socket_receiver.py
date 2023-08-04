from auxtastic.network.socket import socket
import logging

logging.basicConfig(format="[%(name)s] [%(levelname)s] >> %(message)s", level=logging.DEBUG)
soc = socket.socket(soc_type=socket.SOC_PCP, verbose=True)

soc.listen()
soc.accept()
data = soc.recv(1024)

print(f'got: {data}')
