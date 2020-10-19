#!/usr/bin/env python3

from socket import *
import sys

VFS = False

if (len(sys.argv) != 5):
    print("Usage: sender <host> <port> <payload size> <filename or virtualsize>")
    sys.exit(0)

if (sys.argv[4].isnumeric()):
    VFS = True
    virtualSize = int(sys.argv[4])
else:
    fileName = sys.argv[4]

serverName = sys.argv[1]
serverPort = int(sys.argv[2])
payloadSize = int(sys.argv[3])

addr = (serverName, serverPort)

try:
    serverSocket = socket(AF_INET, SOCK_DGRAM)
except error:
    print("Cannot create socket. ")
    sys.exit(1)

firstmsg = sys.argv[3]
serverSocket.sendto(firstmsg.encode('utf-8'),addr)

packetsSent = 1
bytesSent = 16

if (VFS == False):
    tosend = open(fileName, "rb")
    data = tosend.read(payloadSize)
    while (data):
        serverSocket.sendto(data,addr)
        packetsSent += 1
        bytesSent += payloadSize
        data = tosend.read(payloadSize)
    tosend.close()
else:
    if (virtualSize == 0):
        while (True):
            serverSocket.sendto(firstmsg.encode('utf-8'),addr)
    else:
        fullpacks = virtualSize // payloadSize
        lastpack = virtualSize % payloadSize
        for i in range(1,fullpacks):
            generateString = (chr(ord('A')+packetsSent))*payloadSize
            serverSocket.sendto(generateString.encode('utf-8'),addr)
            packetsSent += 1
            bytesSent += payloadSize
        generateString = (chr(ord('A')+packetsSent))*lastpack
        serverSocket.sendto(generateString.encode('utf-8'),addr)
        packetsSent += 1
        bytesSent += payloadSize

lastmessage = ""
serverSocket.sendto(lastmessage.encode('utf-8'),addr)
serverSocket.close()

packetsSent += 1
bytesSent += payloadSize

print(f'{packetsSent} {bytesSent}')
