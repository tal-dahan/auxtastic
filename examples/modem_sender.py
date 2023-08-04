from auxtastic.network.modem.modem import Modem

# Sender
modem = Modem()
buf_size = 140

with open("C:\\Users\\X\\Downloads\\WhatsApp Image 2022-04-21 at 12.29.50 PM.jpeg", 'rb') as file:
    file_fragment = file.read(buf_size)
    cur_frag = 1

    while file_fragment:
        print(f'sending {cur_frag}')
        modem.send(file_fragment)
        print(f'sent {cur_frag}')

        print(f'waiting for ack...')
        response = modem.recv(1024)
        if response == b'0':
            print(f'{cur_frag} ACK')

        file_fragment = file.read(buf_size)
        cur_frag += 1

modem.send(b'1')