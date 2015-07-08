import logging

#from ofproto.ofproto_v1_3_parser import OFPInstructionGotoTable
from ryu.lib.ovs.bridge import OVSBridge
from ryu.lib.ovs import vsctl

from newvsctl import NewVSCtl
LOG =logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class OVSSwitch(OVSBridge):
    def __init__(self,CONF,datapath_id,ovsdb_addr,timeout=None,exception=None):
        super(OVSSwitch,self).__init__(CONF,datapath_id,ovsdb_addr,5,exception)
        self.init()
        self.vsctl = NewVSCtl(ovsdb_addr)
        #objects are VifPort object in self.ports
        self.ports = {} #contain all ports, in which port_no is key
        portList = self.get_external_ports()
#        self.testDeletePort(self.br_name)
        
        for port in portList:
#        for x in range(1):
            """queues stored all queue number to avoid collisions
               lookup is faster in set than in list
            """
            self.ports[port.ofport] = port
            port.queues = set()
            

            #initialization
            #first clean
            self.del_qos(port.port_name)

            self.set_qos(port.port_name)
            self._addDefaultQueue(port.port_name)
#            self.delQueue(port.ofport,[0])
#            self.del_qos(port.port_name)
            #set default route at table_id:0, 
            
#            match = parser.OFPMatch()
#            OFInstructionGotoTable()
#            actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
#                                          ofproto.OFPCML_NO_BUFFER)]
            """
            LOG.debug(self.setQueues(port.ofport,\
                [{"max-rate":"10000","min-rate":"10","queue-id":6},{"max-rate":'1000',"queue-id":1}])\
                    )
            
            self.set_qos(port.port_name,"linux-htb",None,  \
             [{"max-rate":"10000","min-rate":"10","queue-id":6},{"max-rate":'1000',"queue-id":1}])
            self.delQueue(port.port_name,[6])
            """
    #port is VifPort object, 
    def _addDefaultQueue(self,portName):
        """
            add default queue, 0 
        """
        #TODO: more description about queue
        #And including priority
        queue_descs = [ {"queue-id":0,"min-rate":"1"},{"queue-id":1,"min-rate":"1"}]
        self._setQueues(portName,queue_descs)

    #ofport, is the number of openflow switch(int)
    #here, I addd queue-id to queue dict
    #queue-id is store in queues
    def setQueues(self,ofport,queues):
        port =  self.ports.get(ofport,None)
        if None == port:
            LOG.debug("no port_no:%d",ofport)
            return False

        startID = 2
        for queue in queues:
            
            #find a startID
            for startID in port.queues:
                startID += 1

            queue["queue-id"] = startID
            port.queues.add(startID)
            startID += 1
        
        return self._setQueues(port.port_name,queues)

        
        


    #@portName is an string, the name of port
    #@queues is an list, each element is an dict, in whcih three keys are contained,
    #maxt-rate, min-rate, queue-id. the vaules types are string, string, integer accordingly
    #priority seems to be not suppoted
    def _setQueues(self,portName,queues):
        """set Queue for portName
            maybe i shoud manage queue number myself
        """
        commandQueue = vsctl.VSCtlCommand(
                'set-queue',
                [portName,queues])
        self.run_command([commandQueue])
        if commandQueue.result:
            return commandQueue.result
        return None

    def getPort(self,portNo):
        return self.ports.get(portNo,None)

    def delQueue(self,ofport,queues):
        portName = self.ports[ofport].port_name
        self._delQueue(portName,queues)
    """queues is a list of integer
    """
    def _delQueue(self,portName,queues):
        cmd = vsctl.VSCtlCommand(
                'del-queue',
                [portName,queues])
        self.run_command([cmd])
        if cmd.result:
            return cmd.result
        return None
    def testDeletePort(self,br_name):
        cmd = vsctl.VSCtlCommand(
                'del-port',
                [br_name]
                )
        self.run_command([cmd])
        if cmd.result:
            return self.result
        return None
