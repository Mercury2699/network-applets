import struct

#Type: 0 Data, 1 ACK, 2 EOT
#Length: calculated by sender, [12...512]
#Seq: [0...255]
def makePacket(type, length, seq, data = b''):
    if (data == b''):
        packedData = struct.pack(">III",type,length,seq)
    else:    
        packedData = struct.pack(">III"+str(length-12)+"s",type,length,seq,data)
    return packedData
    
def extractPacket(packet):
    if (len(packet) <= 12):
        data = struct.unpack(">III",packet)
    else:
        data = struct.unpack(">III"+str(len(packet)-12)+"s",packet)
    return data
