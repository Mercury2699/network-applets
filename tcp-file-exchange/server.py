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
    # put serversocket into read list
    readlist = [serverSocket]
    # put already paired uploaders into read list
    for p in paired:
        readlist.append(p[0])
    #syscall select
    readable, _, exce = select.select(readlist,[],readlist)

    for r in readable:
        if r is serverSocket: # handle new connections
            connectionSocket, addr = serverSocket.accept()
            recvdControl = connectionSocket.recv(9)
            print(recvdControl)
            if (recvdControl[:1] == b'F'): # TERMINATOR
                print("I received termination request.")
                toTerminate = True
                # close own TCP socket to avoid new client
                connectionSocket.shutdown(socket.SHUT_RD)
                connectionSocket.close()
                #close unpaired clients
                for n in newDownloaders:
                    n[0].close()
                for n in newUploaders:
                    n[0].close()
                #if no more activity, server can exit
                if not paired and toTerminate:
                    sys.exit(0)
            elif (recvdControl[:1] == b'G'): # New Downloader
                print("New Downloader")
                key = recvdControl[-8:]
                matched = False
                #check existing P clients for key match
                for u in newUploaders:
                    if u[1] == key:
                        paired.append((u[0],connectionSocket))
                        matched = True
                        print("Matched!")
                        newUploaders.remove(u) #remove matched from unmatched list
                        break
                if not matched:
                    newDownloaders.append((connectionSocket,key))
            elif (recvdControl[:1] == b'P'): # New Uploader
                print("New Uploader")
                key = recvdControl[-8:]
                matched = False
                #check existing G clients for key match
                for d in newDownloaders:
                    if d[1] == key:
                        paired.append((connectionSocket,d[0]))
                        matched = True
                        print("Matched!")
                        newDownloaders.remove(d) #remove matched from unmatched list
                        break
                if not matched:
                    newUploaders.append((connectionSocket,key))
            # print(f"Now we have {len(paired)} pairs of clients.")
            # print(f"Now I have {len(newUploaders)} unmatched Ups.")
            # print(f"Now I have {len(newDownloaders)} unmatched Downs.")
        else:
            data = r.recv(4096)
            corresponder = None
            # print(len(data))
            for p in paired:
                if p[0] is r:
                    corresponder = p[1]
            if corresponder is None:
                print("ERROR: Received data from not matched pair!!!")
                r.close()
            if len(data) > 0:
                corresponder.send(data)
            else: 
                print("Transfer finished, closing a pair of client. ")
                r.close()
                corresponder.send(b'') # send an empty message to unblock uploader
                corresponder.close() # so that it could terminate
                for p in paired: #remove them from paired client list after closing
                    if p[0] is r:
                        paired.remove(p)
                        break
            # print(f"Now we have {len(paired)} pairs of clients.")
            # print(f"Now I have {len(newUploaders)} unmatched Ups.")
            # print(f"Now I have {len(newDownloaders)} unmatched Downs.")
            #check for termination if only no paired clients exists
            if not paired and toTerminate:
                for n in newDownloaders:
                    n[0].close()
                for n in newUploaders:
                    n[0].close()
                sys.exit(0)
