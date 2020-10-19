#!/usr/bin/env python3

import socket
import sys
import time
import select
import packet

windowsize = 10
maxPacketSize = 512
recvBuffer = []
receiveBase = 0

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
    # print(receiveBase)
    # print(len(recvBuffer))
    recvd, cAddr = receiverSocket.recvfrom(maxPacketSize)
    #extract the data received
    type = packet.extractPacket(recvd)[0]
    if (type == 2): #EOT packet
        (type, length, seq) = packet.extractPacket(recvd)
        eotpkt = packet.makePacket(2,12,receiveBase)
        print("PKT SEND EOT 12 "+ str(receiveBase))
        # print(recvBuffer)
        break #Terminate
    elif (type == 0): #Data received
        (type, length, seq, data) = packet.extractPacket(recvd)
        print("PKT RECV DAT "+str(length)+" "+ str(seq))
        if seq >= receiveBase: #received in or bigger sequence, write and check buffer
            if seq <= receiveBase+windowsize:# only process packets in window
                if seq == receiveBase: #in sequence, write
                    # print("In Sequence")
                    outputfile.write(data)
                    receiveBase += 1
                else: # bigger than sequence, save to buffer
                    # print("Bigger Sequence")
                    if recvd not in recvBuffer: #only if it is not buffered before
                        recvBuffer.append(recvd)
                ackpkt = packet.makePacket(1,12,seq)
                receiverSocket.sendto(ackpkt,cAddr) #make and send ACK
                print("PKT SEND ACK 12 "+ str(seq))
                for pkt in recvBuffer:#check buffer if in order packet is available for delivery
                    (t,l,s,d) = packet.extractPacket(pkt)
                    if (s == receiveBase): #only write in orderly
                        # print("Buffer in sequence")
                        outputfile.write(d)
                        recvBuffer.remove(pkt)
                        receiveBase += 1
        else: #smaller than in sequence, just discard and resend ACK
            # print("Smaller Sequence")
            ackpkt = packet.makePacket(1,12,seq)
            receiverSocket.sendto(ackpkt,cAddr) #make and send ACK
            print("PKT SEND ACK 12 "+ str(seq))
#end while

while len(recvBuffer):# after EOT, write all data from buffer until no packet is left
    leng = len(recvBuffer)
    for pkt in recvBuffer:#check buffer if in order packet is available for delivery
        (t,l,s,d) = packet.extractPacket(pkt)
        if (s == receiveBase): #only write in orderly
            outputfile.write(d)
            recvBuffer.remove(pkt)
            receiveBase += 1
    if leng == len(recvBuffer):
        break

outputfile.close()
receiverSocket.close()
#close out file and terminate
