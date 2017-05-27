#!/usr/bin/python3

import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = (input("Local IP: "), int(input("Local port: ")))
print("Connecting to " + server_address[0] + " port " + str(server_address[1]))
sock.connect(server_address)

try:
    while True:
        message = input("Message: ")
        sock.sendall(message.encode('utf-8'))
        print('Sent.')
        try:
            data = sock.recv(4096)
            if data:
                print("Received: " + data.decode('utf-8')) 
        except:
            sock.close()
except KeyboardInterrupt:
    sock.shutdown()
    sock.close()
