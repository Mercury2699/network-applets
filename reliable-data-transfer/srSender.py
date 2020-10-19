#!/usr/bin/env python3

import socket
import sys
import time
import select
import signal
import packet

payloadSize = 500
windowsize = 10
packetsMade = 0
sendBase = 0
nextSeqNum = windowsize
inFlightPackets = [] # contains (seqNumber, TimerObject)
packets = [] #array of prepared packets within the window
acks = []

#argument check
if (len(sys.argv) != 3):
    print("Usage: srSender <timeout> <filename>")
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

#bind to socket
addr = (hostname, int(port))
try:
    BSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error:
    print("Cannot create socket. ")
    sys.exit(1)
print("Connecting to "+hostname+" on Port:" + port)

#open the file to send
try:
    tosend = open(fileName, "rb")
except Exception:
    print("File "+ fileName +" not found.")
    sys.exit(1)

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

for i in range(packetsMade):
    acks.append(False)

while 1:
    if (packets): # next available sequence in window, send packet
        for i in range(min(10-len(inFlightPackets), len(packets))):
            pack = packets.pop(0)
            BSocket.sendto(pack,addr)
            inFlightPackets.append(pack)
            (_, length, seq) = packet.extractPacket(pack)[0:3]
            print("PKT SEND DAT " + str(length) +" "+ str(seq))

    time.sleep(timeout/1000)
    print("Syscall: select()")
    readable, writable, exceptional = select.select([BSocket],[BSocket],[BSocket],timeout/1000)

    if readable:
        for r in readable:
            while readable:
                recvdata = BSocket.recv(512)
                if not recvdata:
                    break
                (type, length, seq) = packet.extractPacket(recvdata)[0:3]
                if type == 1: #type is ACK
                    print("PKT RECV ACK 12 "+ str(seq))
                    for p in inFlightPackets:
                        (t, l, s) = packet.extractPacket(p)[0:3]
                        if (s == seq):
                            inFlightPackets.remove(p)
                            break
                    acks[seq] = True
                readable, writable, exceptional = select.select([BSocket],[BSocket],[BSocket])
    else: #no readable from sockets
        for p in inFlightPackets: # resend timed out packets
            BSocket.sendto(p,addr)
            (_, length, seq) = packet.extractPacket(p)[0:3]
            print("PKT SEND DAT " + str(length) +" "+ str(seq))
        # time.sleep(timeout/1000)

    numNonAcked = 0
    for bol in acks:
        if bol == False:
            numNonAcked += 1
            break

    if numNonAcked == 0: # if all packets are acked, terminate
        break

#Make and send EOT packet and terminates
EOTpacket = packet.makePacket(2,12,packetsMade)
print("PKT SEND EOT 12 "+ str(packetsMade))
BSocket.sendto(EOTpacket,addr)
