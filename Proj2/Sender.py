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
        #variables
        isn = 0
        timeout = .5
        window = list()
        lastAck = None
        lastAckCount = 1
        expectedAck = isn+1

        #Initiation
        synpacket = self.make_packet('syn', isn, None)
        isn += 1
        connectionMade = False
        while(not connectionMade):
            self.send(synpacket)
            synreturn = self.receive(timeout)
            if(synreturn!=None and self.check_ack_packet(synreturn)):
                connectionMade=True
        expectedAck+=1
        #ack match for connection ack?
        #send initial 7 packets
        for i in range(7):
            data=self.infile.read(1000)
            if(data==''):
                break
            if(sys.getsizeof(data)<1000):
                #finpacket
                packet = self.make_packet('fin',isn,data)
                finAck = isn+1
                window.append(packet)
            else:
                #normalpacket
                packet = self.make_packet('dat',isn,data)
                window.append(packet)
            isn+=1
            self.send(packet)

        #receiving
        #checking if first packet isn't final packet
        ackList = list()
        while(True):
            received = self.receive(timeout)
            if(received==None):
                if(self.sackMode):
                    self.handleSack(window,ackList)
                else:
                    for w in window:
                        self.send(w)
                lastAck = None
                lastAckCount = 0
            elif(self.check_ack_packet(received)):
                #Packet received
                msg_type, seqno, data, checksum = self.split_packet(received)
                if(self.sackMode):
                    ack, ackList = self.parseSack(seqno)
                    currAck = int(ack)
                else:
                    currAck = int(seqno)

                #finAck
                if(currAck==finAck):
                    break

                #fasttransmit
                if(lastAck==currAck):
                    lastAckCount+=1
                    if(lastAckCount==4):
                        if(self.sackMode):
                            self.handleSack(window,ackList)
                        else:
                            for w in window:
                                self.send(w)
                else:
                    #window shift
                    if(currAck>=expectedAck):
                        diff = currAck-expectedAck+1
                        expectedAck = currAck+1
                        window = window[diff-1:]
                        for i in range(diff):
                            data=self.infile.read(1000)
                            if(data==''):
                                break
                            if(sys.getsizeof(data)<1000):
                                #finpacket
                                packet = self.make_packet('fin',isn,data)
                                finAck = isn+1
                                window.append(packet)
                            else:
                                #normalpacket
                                packet = self.make_packet('dat',isn,data)
                                window.append(packet)
                            isn+=1
                            self.send(packet)
                    lastAckCount=1
                    lastAck = currAck
        #print("Exited")



    def handleSack(self, window, ackList):
        for w in window:
            msg_type, seqno, data, checksum = self.split_packet(w)
            if (int(seqno)-1) not in ackList:
                self.send(w)

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
