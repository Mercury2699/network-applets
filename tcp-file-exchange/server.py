#!/usr/bin/env python3

import socket, sys, select

newUploaders = [] # contains (socket, key)
newDownloaders = [] # contains (socket, key)
paired = [] # contains (up, down)
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

while 1:
    readable, writable, exceptional = select.select([serverSocket],[],[serverSocket])

    for r in readable:
        if r is serverSocket: # handle new connections
            connectionSocket, addr = serverSocket.accept()
            recvdControl = connectionSocket.recv(9)
            print(recvdControl)
            if (recvdControl[:1] == b'F'): # TERMINATOR
                print("I received termination request.")
                toTerminate = True
                connectionSocket.close()
            elif (recvdControl[:1] == b'G'): # New Downloader
                print("New Downloader")
                key = recvdControl[-8:]
                matched = False
                for u in newUploaders:
                    if u[1] == key:
                        paired.append((u[0],connectionSocket))
                        matched = True
                        print("Matched!")
                        break
                if not matched:
                    newDownloaders.append((connectionSocket,key))
            elif (recvdControl[:1] == b'P'): # New Uploader
                print("New Uploader")
                key = recvdControl[-8:]
                matched = False
                for d in newDownloaders:
                    if d[1] == key:
                        paired.append((connectionSocket,d[0]))
                        matched = True
                        print("Matched!")
                        break
                if not matched:
                    newUploaders.append((connectionSocket,key))
        else:
            data = r.recv(1024)
            print(data)



