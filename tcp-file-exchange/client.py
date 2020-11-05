#!/usr/bin/env python3

import socket, sys, time

#argument check
if (len(sys.argv) != 4 and len(sys.argv) != 6 and len(sys.argv) != 7):
    print("Usage:")
    print("Terminate: client <host> <port> F")
    print("Download : client <host> <port> G<key> <file name> <recv size>")
    print("Upload   : client <host> <port> P<key> <file name> <send size> <wait time>")
    sys.exit(0)

#Save host and port
host = sys.argv[1]
port = sys.argv[2]

#initialize TCP socket
clientSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

#check port number is digit
if (sys.argv[2].isdigit()):
    port = int(port)
    if port > 65535 or port < 0:
        print("Port number is invalid.")
        sys.exit(0)
else:
    print("Port number must be all digit.")
    sys.exit(0)

#check control code and key
control = sys.argv[3]
if len(control) > 9:
    print("Key is too long")
    sys.exit(0)
elif len(control) < 9: # Pad control string with null
    for i in range(9 - len(control)):
        control += '\0'

#start actions depending on control codes
if control[:1] == 'F' and len(sys.argv) == 4:
    clientSocket.connect((host,port))
    clientSocket.send(control.encode())
    print("I asked the server to terminate.")
    clientSocket.close()
    sys.exit(0)
elif control[:1] == 'P' and len(sys.argv) == 7: #Uploader
    clientSocket.connect((host,port))
    clientSocket.send(control.encode())
    print("Uploader sent the control and key.")
    filename = sys.argv[4]
    size = int(sys.argv[5])
    wait = int(sys.argv[6])
    if (filename.isdigit()): # Virtual File Size
        VFS = int(filename)
        fullpacks = VFS // size
        lastpack = VFS % size
        for i in range(1,fullpacks):
            generateStr = (chr(ord('A')+i))*size
            clientSocket.send(generateStr.encode())
        generateStr = (chr(ord('z')))*lastpack
        clientSocket.send(generateStr.encode())
    else: # Actual filename string
        filetosend = open(filename, "rb")
        data = filetosend.read(size)
        while (data):
            clientSocket.send(data)
            data = filetosend.read(size)
        filetosend.close()
    # shutdown and close after sending 
    clientSocket.shutdown(socket.SHUT_WR)
    clientSocket.close()
elif control[:1] == 'G' and len(sys.argv) == 6: #Downloader
    clientSocket.connect((host,port))
    clientSocket.send(control.encode())
    print("Downloader sent the control and key.")
    filename = sys.argv[4]
    size = int(sys.argv[5])
    
    clientSocket.close()
else:
    print("Invalid Control code or missing arguments. ")
    sys.exit(0)
