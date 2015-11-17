import logging
import copy
from collections import deque

#from ofproto.ofproto_v1_3_parser import OFPInstructionGotoTable
from ryu.lib.ovs.bridge import OVSBridge
from ryu.lib.ovs import vsctl

from newvsctl import NewVSCtl
LOG = logging.getLogger(__name__)
#LOG.setLevel(logging.DEBUG)


#from high to lower
TOTAL_QUEUE =  18
QPOOL = [{"min-rate":"4000000","num":6},{"min-rate":"2000000","num":6},{"min-rate":"1000000","num":6}]

DP = 4

TIME = 30
alpha = 0.5

MAXLEN = 500
MAX_QOS_RATE = "50000000"
VIDEO_BANDWIDTH = 40000000
#deq is deque maxlen is MAXLEN
#each element is (sec,nsec,tx_bytes,tx_packets)
"""nanoseconds is ignored
"""
def cal_rate(deq):
    end = None
    end_bytes = None
    start = None
    start_bytes = None
    isIndexError = False
    if len(deq) < 2:
        return (None,None)
    while True:
        try:
            sec,nsec,tx_bytes,tx_packets = deq.pop()
        except IndexError:
            isIndexError = True
            break
        if end is None:
            end = sec
            end_bytes = tx_bytes
        else:
            start = sec
            start_bytes = tx_bytes
            if end - sec > TIME:
                break
    BYTE_TO_BIT = 8

    return (end-start,BYTE_TO_BIT * float(end_bytes-start_bytes)/float(end-start))



class OVSSwitch(OVSBridge):
    def __init__(self,CONF,datapath_id,ovsdb_addr,timeout=None,exception=None):
        super(OVSSwitch,self).__init__(CONF,datapath_id,ovsdb_addr,5,exception)
        if CONF.enable_debugger:
            LOG.setLevel(logging.DEBUG)
        self.init()
        self.vsctl = NewVSCtl(ovsdb_addr)
        #objects are VifPort object in self.ports
        self.ports = {} #contain all ports, in which port_no is key
        portList = self.get_external_ports()

        """
        store 
        """
        self.pqRate = {} #[port][queue-id] = deque(maxlen=500)
        
        for port in portList:
#        for x in range(1):
            """queues stored all queue number to avoid collisions
               lookup is faster in set than in list
            """
            self.ports[port.ofport] = port
            port.queues = set()
            self.pqRate.setdefault(port.ofport,{})
            

            #initialization
            #first clean
            self.del_qos(port.port_name)

            self.set_qos(port.port_name,"linux-htb",MAX_QOS_RATE)
            self._addDefaultQueue(port.port_name)
            if datapath_id == DP:
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
        port.video_bw = VIDEO_BANDWIDTH #total bandwidth
        port.queuePool = {} #[queue-id] = port_dict
        port.queuePool.setdefault("free",[]) #store free queues ,id
        port.queuePool.setdefault("busy",[]) #store busy queues ,id
        port.queueLevel = {} #[level] = {id:level,'config':{"min-rate":int,"max-rate":"","priority":prio,}}
        port.queueConfig = {} #queuconfig[queu_id] = bandwidth, is used when release queue
        port.used_bw = 0
        total = 0

        configs = copy.deepcopy(QPOOL)
        for i,config in enumerate(configs):
            port.queueLevel[i] = config #{min-rate,and number}
            total = total + config["num"]

        queue_config = [copy.copy({"min-rate":"1","max-rate":"10000000","priority":"2"}) for i in xrange(total)]
        self.setQueues(port.ofport,queue_config)
        for queue in queue_config:
            LOG.debug(queue)
            port.queuePool["free"].append(queue["queue-id"])

    """return quid,otherwise None
    """
    def getQueue(self,ofport):
        """get a queue id at this port
        """
        port = self.ports[ofport]
        LOG.debug("queuePool free = %s",port.queuePool["free"])

        for qid in port.queuePool["free"]:
            port.queuePool["free"].remove(qid)
            port.queuePool["busy"].append(qid)

            self.pqRate[ofport].setdefault(qid,deque(maxlen=MAXLEN))
            
            return qid
        return None

    "max badnwidth"
    def getMaxBW(self,ofport):
        port = self.ports[ofport]
        return int(port.queueLevel[0]['min-rate'])


    def getQueueWithBW(self,ofport,bw=None):
        port = self.ports[ofport]
        if bw is None:
            bw = int(port.queueLevel[0]['min-rate']) #maximum bandwidth
        "assuming that bw is just legal"
        if port.used_bw + bw <= port.video_bw:
            queue_id = self.getQueue(ofport)
            if queue_id is None:
                return None
            self.setQueueConfig(ofport,queue_id,bw)
            port.used_bw += bw
            port.queueConfig[queue_id] = bw
            return queue_id
        return None #failed to allocate

        
    
    def releaseQueue(self,ofport,queue_id):
        """relase a queue
        """
        port = self.ports[ofport]
#if queue_id in port.queuePool["busy"]:
        bw = port.queueConfig[queue_id]
        LOG.info("before release")     
        LOG.info(port.used_bw)
        LOG.info(port.queuePool["free"])
        LOG.info(port.queuePool["busy"])

        port.used_bw -= float(bw) #release bandwidth
        port.queuePool["free"].append(queue_id)
        port.queuePool["busy"].remove(queue_id)
        del self.pqRate[ofport][queue_id]  #remove monitoring
        LOG.info("after release")
        LOG.info(port.used_bw)
        LOG.info(port.queuePool["free"])
        LOG.info(port.queuePool["busy"])

    def getAvailBW(self,ofport):
        port = self.ports.get(ofport,None)
        if port is None:
            return 0
        return (port.video_bw - port.used_bw)
#TODO : MORE WORK HERE
    def getNextBW(self,ofport,rate):
        port = self.ports[ofport]
        for level,config in reversed(port.queueLevel.items()):
            if config["min-rate"] > rate:
                return config["min-rate"]




    """adjust the speed of all busy queues at this port
    """
    def adjustBW(self,ofport):
        port = self.ports[ofport]
        for qid,bw in port.queueConfig.items(): #all occupied queues
            duration,rate = self.getRate(ofport,qid)
            if rate is None:
                LOG.debug("rate is None, I don't know why")
                return
            LOG.info("duration = %s, rate = %d, alloc_bandwidth=%s",duration,rate,bw)
            if duration >= TIME and rate < alpha*float(bw):
                new_bw = self.getNextBW(ofport,rate)
                
                LOG.info("new bw = %s",new_bw)
                assert int(new_bw) <= int(bw)

                
                "assuming that all config is set correctly"
                self.setQueueConfig(ofport,qid,str(new_bw))
                #update bandwidth
                port.queueConfig[qid] = str(new_bw)
                port.used_bw = port.used_bw - int(bw) + int(new_bw)  #adjust available bandwidth
            else:
                 pass
                 #don't adjust

        return port.video_bw - port.used_bw
    #update counter
    def updateCounter(self,ofport,queue_id,sec,nsec,tx_bytes,tx_packets=None):
        queues = self.pqRate[ofport]
#LOG.debug("ofport=%d,queue-id=%d,sec=%d,nsec=%d,tx_bytes=%d",ofport,queue_id,sec,nsec,tx_bytes)
        if queue_id not in queues.keys():
#LOG.debug("not recorded")
            return
        queues[queue_id].append((sec,nsec,tx_bytes,tx_packets))
        LOG.debug("queue_id=%d,desc=%d",queue_id,tx_bytes)

    def getRate(self,ofport,queue_id):
        try:
            q = copy.copy(self.pqRate[ofport][queue_id])
            """calculate speed here
            """
            deq = copy.copy(q)
            return cal_rate(deq)

        except KeyError:
            return (None,None)

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
        queue_descs = [ {"queue-id":0,"min-rate":"1","max-rate":MAX_QOS_RATE,"priority":"0"},{"queue-id":1,"max-rate":MAX_QOS_RATE,"min-rate":"1000000","priority":"100"}]
        self._setQueues(portName,queue_descs)
        for ofport,port in self.ports.items():
            if port.port_name == portName:
                 self._setQueueConfig(ofport,queue_descs)
                 break

    
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
    ###
    #queue_id is None means new queue,otherwise just modify a queue
    #return queue_id
    def setQueueConfig(self,ofport,queue_id=None, min_rate=MAX_QOS_RATE,max_rate=None,priority=2):
        """interface for 
        """
        
        config = {"min-rate":str(min_rate),"priority":str(priority)}
        if max_rate is not None:
            config["max-rate"] = str(max_rate)

        if queue_id is None:
            "pick an queue from pool and set"
            self.setQueues(ofport,config)
            return config["queue-id"]
        else:
            config["queue-id"] = queue_id
        self._setQueueConfig(ofport,[config])
        return queue_id

    def _setQueueConfig(self,ofport,queues):
        """set queue configuration
        """
        LOG.debug("dpid = %d, port = %d, setQueueConfig:%s",self.datapath_id,ofport,queues)
        for queue in queues:
            queue["port_name"] = self.ports[ofport].port_name
        cmd = vsctl.VSCtlCommand(
                'set-queue-config',
                [queues])
        self.run_command([cmd])

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
