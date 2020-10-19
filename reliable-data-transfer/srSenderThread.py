#!/usr/bin/env python3

import socket
import sys
import time
import threading
import packet

payloadSize = 500
windowsize = 10
fileCompleted = False
packetsMade = 0
sendBase = 0
nextSeqNum = windowsize
inFlightTimers = [] # contains (seqNumber, TimerObject)
acks = [] #contains Bool
lock = threading.Lock()
cv = threading.Condition(lock)
canSend = False

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

#array of prepared packets within the window
packets = []

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

def receiver():
    global acks
    global inFlightTimers
    global canSend
    global sendBase
    global nextSeqNum

    while 1:
        recvd, _ = BSocket.recvfrom(512) #keep listening from socket
        (t, _, s) = packet.extractPacket(recvd)[0:3]
        with lock:
            if (t == 1): #ACK
                print("PKT RECV ACK 12 "+ str(s))
                acks[s] = True # mark ACK as True for this packet
                for timer in inFlightTimers: #cancel the timer for ACKed packet
                    if timer[0] == s:
                        timer[1].cancel()
                        inFlightTimers.remove(timer)
                        break
                for i in range(len(acks)): #increase sendBase to next smallest unACKed
                    if acks[i] == False and i > sendBase:
                        sendBase = i
                        print("sendBase incremented: "+ str(sendBase))
                        nextSeqNum = min(sendBase+windowsize, packetsMade)
                        break
                # while (sendBase < len(acks) and acks[sendBase]):#increase sendBase to next smallest unACKed
                #     sendBase += 1
                #     print("sendBase incremented: "+ str(sendBase))
                #     canSend = True

def resendPacket(pack):
    BSocket.sendto(pack,addr)
    (_, length, seq) = packet.extractPacket(pack)[0:3]
    print("PKT SEND DAT " + str(length) +" "+ str(seq))
    print("Timer Expired")
    for timer in inFlightTimers: #restart the timer for required packet
        if timer[0] == seq:
            timer[1].cancel()
            newtimer = threading.Timer(timeout/1000, resendPacket, [p])
            newtimer.start()
            timer = (seq, newtimer)


receiverThread = threading.Thread(target=receiver)
receiverThread.start()

# sender portion in main thread
while sendBase < packetsMade - 1:
    with lock:
        print(sendBase)
        print(nextSeqNum)
        if (nextSeqNum <= sendBase+windowsize and nextSeqNum != packetsMade - 1): # next available sequence in window, send packet
            for p in packets[sendBase:nextSeqNum]:
                BSocket.sendto(p,addr)
                Timer = threading.Timer(timeout/1000, resendPacket, [p])
                Timer.start()
                (type, length, seq, data) = packet.extractPacket(p)
                inFlightTimers.append((seq,Timer))
                print("PKT SEND DAT " + str(length) +" "+ str(seq))
            nextSeqNum = sendBase+windowsize+1

        print("Syscall: CV WAIT")
        cv.wait(timeout/1000)

        for i in range(len(acks)): #increase sendBase to next smallest unACKed
            if acks[i] == False and i > sendBase:
                sendBase = i
                print("sendBase incremented: "+ str(sendBase))
                nextSeqNum = min(sendBase+windowsize, packetsMade)
                break

#Make and send EOT packet and terminates
EOTpacket = packet.makePacket(2,12,packetsMade)
print("PKT SEND EOT 12 "+ str(packetsMade))
BSocket.sendto(EOTpacket,addr)
receiverThread.join()
sys.exit()
