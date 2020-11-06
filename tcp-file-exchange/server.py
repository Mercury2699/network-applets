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
    readlist = [serverSocket]
    for p in paired:
        readlist.append(p[0])
    readable, _, exce = select.select(readlist,[],readlist)

    for r in readable:
        if r is serverSocket: # handle new connections
            connectionSocket, addr = serverSocket.accept()
            recvdControl = connectionSocket.recv(9)
            print(recvdControl)
            if (recvdControl[:1] == b'F'): # TERMINATOR
                print("I received termination request.")
                toTerminate = True
                connectionSocket.shutdown(socket.SHUT_RD)
                connectionSocket.close()
                if not paired and toTerminate:
                    for n in newDownloaders:
                        n[0].close()
                    for n in newUploaders:
                        n[0].close()
                sys.exit(0)
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
            corresponder = None
            print(len(data))
            for p in paired:
                if p[0] is r:
                    corresponder = p[1]
            if corresponder is None:
                print("ERROR: Received data from not matched pair!!!")
            while len(data) > 0:
                corresponder.send(data)
                data = r.recv(1024)
                print(len(data))
            print("Transfer finished, closing a pair of client. ")
            r.close()
            corresponder.close()
            for p in paired:
                if p[0] is r:
                    paired.remove(p)
                    break
            if not paired and toTerminate:
                for n in newDownloaders:
                    n[0].close()
                for n in newUploaders:
                    n[0].close()
                sys.exit(0)

            
            


