from auxtastic.network.modem.modem import Modem
import time
s = time.time()
my_modem = Modem()
connection = True
with open("my_file.jpeg", "wb") as binary_file:
    print("start listening...")
    while connection:
        answer = my_modem.recv(1024)
        print('got incomming msg')
        if answer ==b'1':
            print("got fin")
            connection = False
            my_modem.send(b'1')
        else:
            binary_file.write(answer)
            my_modem.send(b'0')
            print("send ack")
e = time.time()
print(e-s)