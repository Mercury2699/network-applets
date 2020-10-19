#!/usr/bin/env python3

from socket import *
import sys
import signal

if (len(sys.argv) != 3):
    print("Usage: receiver <file name> <timeout (ms)>")
    sys.exit(0)

fileName = sys.argv[1]
timeout = int(sys.argv[2])

addr = ("0.0.0.0", 0)

receiverSocket = socket(AF_INET, SOCK_DGRAM)
receiverSocket.bind(addr)

print('listening on port:', receiverSocket.getsockname()[1])

portfile = open("port", "w")
portfile.write(str(receiverSocket.getsockname()[1])+"\n")
portfile.close()

outputfile = open(fileName, "wb")

numreceived = 0
bytesreceived = 0

data,addr = receiverSocket.recvfrom(16)
packetSize = int(data.decode('utf-8'))

def alarmhandler(signum, frame):
    print(f'{numreceived} {bytesreceived}')
    sys.exit(0)

signal.signal(signal.SIGALRM, alarmhandler)
signal.alarm(int(timeout/1000))

numreceived = 1
bytesreceived = 16

while True:
    data,addr = receiverSocket.recvfrom(packetSize)
    numreceived += 1
    bytesreceived += packetSize
    end = False
    try:
        text = data.decode()
        if (text == ""):
            end = True
    except UnicodeDecodeError:
        end = False
    if (end == True):
        break
    outputfile.write(data)
#end while
outputfile.close()

print(f'{numreceived} {bytesreceived}')

