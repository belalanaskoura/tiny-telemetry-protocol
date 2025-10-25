import socket

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('127.0.0.1', 9999))


while True:
    data,addr = server.recvfrom(1024)
    print(data.decode())
    server.sendto("Hi".encode(),addr)