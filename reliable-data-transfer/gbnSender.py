#!/usr/bin/env python3

import socket
import sys
import time
import select
import signal
import packet

windowsize = 10
payloadSize = 500
packetsMade = 0
packetsSent = 0
bytesSent = 0
sendBase = 0
nextSeqNum = 0
lastack = -1
seqModulo = 256

#argument check
if (len(sys.argv) != 3):
    print("Usage: gbnSender <timeout> <filename>")
    sys.exit(0)
fileName = sys.argv[2]

if (sys.argv[1].isdigit()):
    print("Timeout is: " + sys.argv[1])
else:
    print("Invalid Timeout")
    sys.exit(1)
timeout = int(sys.argv[1])

#read port info from required file
portfile = open("channelInfo", "r")
(hostname, port) = portfile.readline().split()

#connect to socket
addr = (hostname, int(port))
try:
    BSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error:
    print("Cannot create socket. ")
    sys.exit(1)
print("Connecting to "+ hostname +" on Port:" + port)

#array of prepared packets within the window
packets = []

#open the file to send
try:
    tosend = open(fileName, "rb")
except Exception:
    print("File "+ fileName +" not found.")
    sys.exit(1)

#set timer
def alarmhandler(signum, frame):
    signal.alarm(int(timeout/1000))
    for p in packets[0:10]:
        BSocket.sendto(p,addr)
        (_, length, seq) = packet.extractPacket(p)[0:3]
        print("PKT SEND DAT " + str(length) +" "+ str(seq))

#prepare packets if file is available to fill the list
while 1:
    bytes = tosend.read(payloadSize)
    if not bytes:
        # no more bytes available in file
        tosend.close()
        break
    else:
        packets.append(packet.makePacket(0,12+len(bytes),packetsMade,bytes))
        packetsMade += 1

signal.signal(signal.SIGALRM, alarmhandler)

#read and send packets from list
while sendBase < packetsMade:
    if (nextSeqNum < sendBase + windowsize):
        for p in packets[0:10]:
            BSocket.sendto(p,addr)
            (type, length, seq, data) = packet.extractPacket(p)
            print("PKT SEND DAT " + str(length) +" "+ str(seq))
        if(sendBase == nextSeqNum):
            signal.alarm(int(timeout/1000))
            nextSeqNum += 1
        time.sleep(timeout/1000)
    # else:
    #     refusedata

    print("Syscall: select()")
    readable, writable, exceptional = select.select([BSocket],[BSocket],[BSocket],timeout/1000)

    if readable:
        for r in readable:
            while readable:
                recvdata = BSocket.recv(512)
                # print("recv")
                if not recvdata:
                    break
                (type, length, seq) = packet.extractPacket(recvdata)[0:3]
                if type == 1: #type is ACK
                    print("PKT RECV ACK 12 "+ str(seq))
                    if (seq > lastack): #only process non duplicate ACKs
                        for p in packets[0:10]: # remove already ACKed packets
                            (t,l,s) = packet.extractPacket(p)[0:3]
                            if (s <= sendBase):
                                packets.remove(p)
                        lastack = seq
                        sendBase = seq + 1
                    if sendBase == nextSeqNum:
                        signal.alarm(0) #restart timer for next in-flight packet
                        signal.alarm(int(timeout/1000))
                    else:
                        signal.alarm(int(timeout/1000)) #start timer
                readable, writable, exceptional = select.select([BSocket],[BSocket],[BSocket],timeout/1000)

#Make and send EOT packet and terminates
EOTpacket = packet.makePacket(2,12,packetsMade)
print("PKT SEND EOT 12 "+ str(packetsMade))
BSocket.sendto(EOTpacket,addr)
