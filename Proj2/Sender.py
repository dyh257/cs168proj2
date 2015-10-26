import sys
import getopt

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):


    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.sackMode = sackMode
        self.debug = debug

    # Main sending loop.
    def start(self):
        isnCount = 0
        ackCount = isnCount+1
        inflight = 0
        seekCount = 0
        window = list()
        finAck = None
        finFound = False
        synsentcount = 1
        lastAck = None
        fastRetransmit = 1
        tempseqno = None
        # initiating connection
        synpacket = self.make_packet('syn', isnCount,None)
        isnCount+=1

        synreturn = None
        while(synreturn==None):
            self.send(synpacket)
            #print("Syn sent count: " + str(synsentcount))
            synreturn = self.receive(.5)
            if(synreturn!=None and not self.check_ack_packet(synreturn)):
                #print("Syn bad packet found")
                synreturn = None
            synsentcount +=1
        ackCount+=1
        #print("Connection created")
        #print("File opened")
        while(True):
            #sending
            while(inflight<7 and not finFound):
                tempDat = self.infile.read(1000)
                if(sys.getsizeof(tempDat)<1000):
                    finPacket = self.make_packet('fin', isnCount, tempDat)
                    window.append(finPacket)
                    self.send(finPacket)
                    finAck = isnCount+1
                    #print("Sending final packet " + str(isnCount) + " with final ack: " + str(finAck))

                    finFound = True
                else:
                    tempPacket = self.make_packet('dat', isnCount, tempDat)
                    window.append(tempPacket)
                    self.send(tempPacket)
                    #print("Sending packet " + str(isnCount))
                inflight+=1
                isnCount+=1
            #receiving
            #print("RECEIVING")
            rPacket = self.receive(.5)
            if(rPacket==None):
                #print("timeout")
                if(not self.sackMode):
                    for w in window:
                        self.send(w)
                else:
                    #SACKMODE
                    if(tempseqno == None):
                        for w in window:
                            self.send(w)
                    else:
                        for w in window:
                            temp2msg_type, temp2seqno, temp2data, temp2checksum = self.split_packet(w)
                            if (int(temp2seqno)-1) not in tempacks:
                                self.send(w)

                lastAck = None
                fastRetransmit=1
            else:
               if(self.check_ack_packet(rPacket)):                         
                    tempmsg_type, tempseqno, tempdata, tempchecksum = self.split_packet(rPacket)
                    if(self.sackMode):
                        tempack, tempacks = self.parseSack(tempseqno)
                        tempseqno = int(tempack)
                    else:
                        tempseqno = int(tempseqno)
                    if(finAck==tempseqno):
                        #print("FINISHED")
                        break
                    if(tempseqno>=ackCount):
                        #print("Packet received with ack: " + str(tempseqno))
                        diff = tempseqno-ackCount
                        inflight -= diff
                        if(inflight<0):
                            window=list()
                            inflight=0
                        else:
                            window = window[diff:]
                        ackCount = tempseqno+1
                        lastAck = tempseqno
                        fastRetransmit = 1
                    if(tempseqno==lastAck):
                        fastRetransmit += 1
                        if(fastRetransmit==4):
                            if(not self.sackMode):
                                for w in window:
                                    temp1msg_type, temp1seqno, temp1data, temp1checksum = self.split_packet(w)
                                    if(int(temp1seqno)==lastAck):
                                        self.send(w)
                            else:
                                #SACKMODE
                                for w in window:
                                    temp2msg_type, temp2seqno, temp2data, temp2checksum = self.split_packet(w)
                                    if (int(temp2seqno)-1) not in tempacks:
                                        self.send(w)

        self.infile.close()
        #print("Exited")



    def check_ack_packet(self, packet):
        msg_type, seqno, data, checksum = self.split_packet(packet)
        if(msg_type != 'ack' and not self.sackMode):
            return False
        elif(msg_type!='sack' and self.sackMode):
            return False
        elif(Checksum.validate_checksum(checksum)):
            return False
        else:
            return True

    def parseSack(self, seqno):
        ackCount = seqno[:seqno.index(';')]
        temp = seqno[seqno.index(';') + 1:]
        acks = temp.split()
        intacks = [int(x) for x in acks]
        return ackCount,intacks
        
'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest,port,filename,debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
