#!/usr/bin/env python3

import socket
import sys
import time
import select
import packet

maxPacketSize = 512
windowsize = 10
expectedSeq = 0

#check arguments
if (len(sys.argv) != 2):
    print("Usage: gbnReceiver <filename>")
    sys.exit(0)
fileName = sys.argv[1]

#bind to socket
rAddr = ('', 0)
receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiverSocket.bind(rAddr)
print("Syscall: Binded to port", receiverSocket.getsockname()[1])

#write port info to required file
rAddr = (socket.gethostname(), receiverSocket.getsockname()[1])
portfile = open("recvInfo", "w")
portfile.write(str(socket.gethostname())+" "+str(receiverSocket.getsockname()[1])+"\n")
portfile.close()

#prepare output file to write in
outputfile = open(fileName, "wb")

while True:
    #listen for data on socket for packet of size maximum 512
    # print("Trying to receive")
    recvd, cAddr = receiverSocket.recvfrom(maxPacketSize)
    #extract the data received
    type = packet.extractPacket(recvd)[0]
    if (type == 2): #EOT packet
        (type, length, seq) = packet.extractPacket(recvd)
        eotpkt = packet.makePacket(2,12,expectedSeq)
        print("PKT SEND EOT 12 "+ str(expectedSeq))
        break
    elif (type == 0): #Data received
        (type, length, seq, data) = packet.extractPacket(recvd)
        print("PKT RECV DAT "+str(length)+" "+ str(seq))
        if seq == expectedSeq: #check if it is in sequence
            outputfile.write(data)
            ackpkt = packet.makePacket(1,12,expectedSeq)
            receiverSocket.sendto(ackpkt,cAddr) #make and send ACK
            print("PKT SEND ACK 12 "+ str(expectedSeq))
            expectedSeq += 1
        else: #not expected sequence, resend last ACK
            if (expectedSeq - 1) > 0:
                ackpkt = packet.makePacket(1,12,expectedSeq-1)
                receiverSocket.sendto(ackpkt,cAddr) #make and send ACK
                print("PKT SEND ACK 12 "+ str(expectedSeq-1))
#end while

receiverSocket.close()
outputfile.close()
#close out and terminate
