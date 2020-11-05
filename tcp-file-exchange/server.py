#!/usr/bin/env python3

import socket, sys, select

newUploaders = []
newDownloaders = []
paired = []
toTerminate = False

if (len(sys.argv) != 1):
    print("Usage: server does not accept any command line argument")
    sys.exit(0)

#Initiate TCP
addr = ("0.0.0.0", 0)
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind(addr)
serverSocket.listen(6)
print('listening on port:', serverSocket.getsockname()[1])

#write port info to file
portfile = open("port", "w")
portfile.write(str(serverSocket.getsockname()[1])+"\n")
portfile.close()

# while 1:
    # readable, writable, exceptional = select.select([serverSocket],[],[serverSocket])

connectionSocket, addr = serverSocket.accept()

recvdControl = connectionSocket.recv(1024)

print(len(recvdControl))
print(recvdControl)

if (recvdControl[:1] == b'F'):
    print("I received termination request.")
    sys.exit(0)

