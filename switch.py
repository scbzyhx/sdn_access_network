import logging
import copy

#from ofproto.ofproto_v1_3_parser import OFPInstructionGotoTable
from ryu.lib.ovs.bridge import OVSBridge
from ryu.lib.ovs import vsctl

from newvsctl import NewVSCtl
LOG =logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


#from high to lower
TOTAL_QUEUE =  18
QPOOL = [{"min-rate":"4000","num":6},{"min-rate":"2000","num":6},{"min-rate":"1000","num":6}]



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

            self.set_qos(port.port_name,"linux-htb","10000000")
            self._addDefaultQueue(port.port_name)
            self.setupPool(port)
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
    def setupPool(self,port):
        """set pools which defined in global POOL variable
        """
        port.queuePool = {} #[queue-id] = port_dict
        port.queuePool.setdefault("free",[]) #store free queues ,id
        port.queuePool.setdefault("busy",[]) #store busy queues ,id
        port.queueLevel = {} #[level] = {id:level,queues:[],config:{"min-rate":int,"max-rate":"","priority":prio,}}
        
        total = 0

        configs = copy.deepcopy(QPOOL)
        for i,config in enumerate(configs):
            port.queueLevel[i] = config #{min-rate,and number}
            total = total + config["num"]

        queue_config = [copy.copy({"min-rate":"1","max-rate":"1","priority":2}) for i in xrange(total)]
        self.setQueues(port.ofport,queue_config)
        for queue in queue_config:
            LOG.debug(queue)
            port.queuePool["free"].append(queue["queue-id"])

        
            


    #overrides to return state
    def run_command(self, commands):
        return self.vsctl.run_command(commands, self.timeout, self.exception)
    #port is VifPort object, 
    def _addDefaultQueue(self,portName):
        """
            add default queue, 0 
        """
        #TODO: more description about queue
        #And including priority
        queue_descs = [ {"queue-id":0,"min-rate":"10000"},{"queue-id":1,"min-rate":"1000"}]
        self._setQueues(portName,queue_descs)

    
    #ofport, is the number of openflow switch(int)
    #here, I addd queue-id to queue dict
    #queue-id is store in queues
    def setQueues(self,ofport,queues):
        port =  self.ports.get(ofport,None)
#        LOG.debug("before None == port")
        if None == port:
            LOG.debug("no port_no:%d",ofport)
            return False
#        LOG.debug("after None == port")

        queuesSet = set()
        startID = 2
        for queue in queues:
            
            #find a startID
            for startID in port.queues:
                startID += 1

            queue["queue-id"] = startID
            queuesSet.add(startID)
            #port.queues.add(startID)
            startID += 1
        #if successed, _setQueues return and command.result which is a list of Row object
        LOG.debug("[in setQueues]:queues Set before __setQueues: %s",port.queues)
        results = self._setQueues(port.port_name,queues)
        if results is not None:
            port.queues = port.queues.union(queuesSet)
            LOG.debug("[in setQueues]:queues Set after successful  __setQueues: %s",port.queues)
            return True
        else:
            return False

        
        


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
