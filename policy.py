"""
author:yhx
email:scbzyhx@gmail.com

"""
import logging
from eventlet import semaphore 
import time

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller.event import EventBase
from ryu.lib import hub
from ryu.topology.api import get_link,get_all_link,get_switch,get_all_switch
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3_parser as ofproto
from ryu.lib.packet import ether_types as ether
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.lib.packet import in_proto as inet

from events import Req
from events import Reply
from events import ReqWrapper
from events import ReqHost #synchronized request



import consts

BW_FACTOR = 1000 #with kbps

def cmp_list(list1,list2):
    if len(list1) != len(list2):
        return False
    for el in list1:
        if el not in list2:
            return False
    return True

#knapsack problem fo myself by dynamic programming
#@items [(cost,value)]
#cap    int, capacity
#just 0-1 
def myknapsack(items,cap):
    """zero-one knapsack problem, items is lisst of (weight,value)
       cap is capacity
    """
    """
    arr = [0 for i in xrange(cap)]
    for item in xrange(len(items)):
        for j in reversed(xrange(cap)):
            if j - item[0] < 0: #wrong here
                continue
            if arr[j-item[1]] + item[0] > arr[j]: #max([i][j-item[0]] + item[0] > [i-1][j])
                arr[j] = arr[j-item[1]] + item[0]
    """
    CHOSEN = 1
    NOCHOSEN = 0

    ITEM_SIZE = len(items) + 1
    CAP_SIZE = cap + 1

    arr = [[0 for x in xrange (CAP_SIZE)] for i in xrange(ITEM_SIZE)]
    chosen = [[0 for x in xrange (CAP_SIZE)] for i in xrange(ITEM_SIZE)]
#print len(arr[0])
    for i in xrange(1,ITEM_SIZE):
        for j in xrange(1,CAP_SIZE):
            if j - items[i-1][0] < 0 :
                arr[i][j] = arr[i-1][j]
                chosen[i][j] = NOCHOSEN
            else:
                if arr[i-1][j] > arr[i-1][j-items[i-1][0]] + items[i-1][1] :
                     arr[i][j] = arr[i-1][j]
                     chosen[i][j] = NOCHOSEN
                else:
                     arr[i][j] = arr[i-1][j-items[i-1][0]]+items[i-1][1]
                     chosen[i][j] = CHOSEN
    chosen_items = []
    i = ITEM_SIZE - 1
    j = CAP_SIZE -1
    while True:
        if i < 0 or j < 0 :
            break
        if chosen[i][j] == CHOSEN:
            chosen_items.append(i-1) #i-1 is the item index
            j = j - items[i-1][0]
            i = i - 1
#print ("i=%d,j=%d"% (i,j) )
        else:
            "no chosen"
#            print ("i=%d,j=%d"% (i,j) )
            i = i - 1

    return chosen_items,arr[ITEM_SIZE-1][CAP_SIZE-1]
#arr[i][j] = max(arr[i-1][j],arr[i][j-items[i][0]] + items[i][1])
                


#TODO: algorithm here
#@request = {} , key is the index stands for item, value is bandwidth required 
#@avail is total available bandwidth
#@return is list of key, that is statisfied
def knapsack(requests,avail):
    reqs = map(lambda x:(x/BW_FACTOR,1),requests.values())
    return myknapsack(reqs,avail/BW_FACTOR) #return (list of satisfied request, )

if __name__ == "__main__":
    items = [(144,990),(487,436),(210,673),(567,58),(1056,897)]
    reqs = {1:2}
    print knapsack(reqs,10)

class Policy(app_manager.RyuApp):
    _EVENTS = [Reply,ReqHost]
    def __init__(self,*args,**kwargs):
        super(Policy,self).__init__(*args,**kwargs)
        
#        self.host_tracker = kwargs["host_tracker"]
        hdlr  = logging.StreamHandler()
        fmt_str = '[RT][%(levelname)s] IN [%(funcName)s]: %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        self.logger.addHandler(hdlr)
        
        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)


        self.nib = app_manager.lookup_service_brick("NIB")
        self.dpset = app_manager.lookup_service_brick("dpset")

        self.matches = {} #stored josndict
        self.queueref = {} #[port][queue]
        
        self.requestQ = [] #a request queue
        self.sem = semaphore.Semaphore(1) #TO protect self.requestQ
    #overrides to do start two threads
    def start(self):
        super(Policy,self).start()
        #self.threads.append(hub.spawn(self._event_loop))
        self.threads.append(hub.spawn(self.replyRequest))
    
    @set_ev_cls(ofp_event.EventOFPFlowRemoved,MAIN_DISPATCHER)
    def flow_removed_handler(self,ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        msg_oxm = msg.match.to_jsondict()["OFPMatch"]["oxm_fields"]
        dicts = self.matches.get(datapath.id,{})
        for k,value in dicts.items():
            koxm = k.to_jsondict()["OFPMatch"]["oxm_fields"]
            if cmp_list(koxm,msg_oxm):
                """
                    do something,relase queue
                """
                port,queue_id = self.matches[datapath.id][k]
                del self.matches[datapath.id][k]
                
                #must be
                with self.queueref[datapath.id][port][queue_id][1]:
                    #do
                    self.queueref[datapath.id][port][queue_id][0] -= 1
                    if self.queueref[datapath.id][port][queue_id][0] < 1:
                        "release queue for datapath,and port"
                        sw = self.nib.getSwitch(datapath.id)
                        sw.releaseQueue(port,queue_id)

#TODO
    @set_ev_cls(ReqWrapper)
    def requestHandler(self,ev):
        """
           request handler
        """
        #put it into queueQ
        self.logger.debug("ReqWrapper %s",type(ev))

        with self.sem:
            self.requestQ.append(ev.req)
#TODO   
    def replyRequest(self):
        while self.is_active:
            #do something
            semTmp = None
            #self.logger.debug("in reply thread")
            #speed up
            hub.sleep(0.01)
            if len(self.requestQ) != 0:

                with self.sem:
                    semTmp = self.requestQ
                    self.requestQ = []
            else:
                continue
            start = time.clock()

            DP = consts.GW_DP                        #4
            ofport = consts.KEY_PORT                 #2 #(s4 -eth2)
            sw = self.nib.getSwitch(DP)              #yhx,4 4 4 4 4 4 4 4
            

            #self.logger.debug(req.flows)
            hosttracker = app_manager.lookup_service_brick("HostTracker")
            sw_mac_to_port = app_manager.lookup_service_brick("SimpleSwitch13")
            
            
            sw.adjustBW(ofport)
            requests = {}
            
            for index, req in enumerate(semTmp):
                bw = req.action[1]
                if bw == 0:
                    bw = sw.getMaxBW(ofport) #maxrate
                requests[index] = req.action[1]
            
            avail = sw.getAvailBW(ofport)
            self.logger.debug("available bandwidth:%d",avail)
            knapsack_set,total_bw = knapsack(requests,avail) 
            self.logger.debug("knapsack_set = %s",knapsack_set)
            for ind,req in enumerate(semTmp):
     
                if ind not in knapsack_set:
                    self.send_event(req.src,Reply(req,"failure"))
                    continue
                else:
                    bw = req.action[1] #min bandwidth

                    if bw == 0:#
                        queue_id = sw.getQueueWithBW(ofport)
                    else:
                        queue_id = sw.getQueueWithBW(ofport,bw)

                    datapath = self.dpset.get(DP)
                    parser = datapath.ofproto_parser
                    
                    for flow in req.flows:
                        srcIP  = flow.get('src',None)
                        dstIP = flow.get('dst',None)
                        srcPort = flow.get('src_port',None) #option
                        dstPort = flow.get('dst_port',None) #option
                        ip_proto = flow.get('proto',None)
                        if srcIP is None or dstIP is None  or ip_proto is None or queue_id is None:
                            self.logger.info("faileure srcIP=%s,dstIP=%s,ip_proto=%s,queue_id=%d"%(srcIP,dstIP,ip_proto,queue_id))
                            self.send_event(req.src,Reply(req,"failure"))
                            break

                        if ip_proto == 'tcp':
                            match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP,ipv4_src=srcIP,ipv4_dst=dstIP,ip_proto=inet.IPPROTO_TCP,ip_dscp=consts.PHB)
                            if srcPort is not None:
                                match.set_tcp_src(srcPort)
                            if dstPort is not None:
                                match.set_tcp_dst(dstPort)
                        else:
                            match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP,ipv4_src=srcIP,ipv4_dst=dstIP,ip_proto=inet.IPPROTO_UDP,ip_dscp=consts.PHB)
                            if srcPort is not None:
                                match.set_udp_src(srcPort)
                            if dstPort is not None:
                                match.set_udp_dst(dstPort)


                        actions = [ parser.OFPActionSetQueue(queue_id),parser.OFPActionOutput(ofport)]
                        self.add_flow(datapath,10,match,actions)

                        "update badnwdith"
                        dicts = self.matches.get(datapath.id,{})
                        dicts[match] = (ofport,queue_id)
                        self.matches[datapath.id] = dicts
                    

                        port = self.queueref.get(datapath.id,{})
                        self.queueref[datapath.id] = port
                    
                        queue = port.get(ofport,{})
                        queue.setdefault(queue_id,[0,semaphore.Semaphore(1)])
                        with queue[queue_id][1]:
                            queue[queue_id][0] += 1
                            port[ofport] = queue
                    else: #break would nerver come here
                        self.logger.debug("Time used:%f",time.clock()-start)
                        self.logger.debug("sending replies")
                        self.send_event(req.src,Reply(req,"success"))


                
            """    
            for req in semTmp:
                #for each request
                self.logger.debug(req.action)
                self.logger.debug(req.flows)

                self.logger.debug(sw_mac_to_port.mac_to_port)
                DP = 4
                sw_mac_to_port = sw_mac_to_port.mac_to_port.get(DP,{}) #5 is datapath id

                sw = self.nib.getSwitch(DP)              #yhx,4 4 4 4 4 4 4 4



                for flow in req.flows:
                    srcIP  = flow['src']
                    src = hosttracker.hosts.get(srcIP,None)
                    if src is None:
                        self.logger.debug("src is not found")
                        break
                    srcdp = src["dpid"]
                    srcport = src['port']
                    srcmac = src['mac']
                    dstIP = flow['dst']
                    dst = hosttracker.hosts.get(dstIP,None)
                    if dst is None:
                        self.logger.debug("dst is not found")
                        break
                    dstdp = dst['dpid']
                    dstport = dst['port']
                    dstmac = dst['mac']

                    port_at_sw4 = sw_mac_to_port.get(dstmac,None)

                    if port_at_sw4 is None:
                        "Nothging"
                        break
                    self.logger.debug("the port to dst is at %d",port_at_sw4)
                    
                    bw = req.action[1] #min bandwidth
                    if bw == 0:#
                        queue_id = sw.getQueueWithBW(port_at_sw4)
                    else:
                        queue_id = sw.getQueueWithBW(port_at_sw4,bw)
                    
                    datapath = self.dpset.get(DP)
                    parser = datapath.ofproto_parser
                    match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP,ipv4_src=srcIP,ipv4_dst=dstIP,ip_dscp=consts.PHB)
                    actions = [ parser.OFPActionSetQueue(queue_id),parser.OFPActionOutput(port_at_sw4)]
                    self.add_flow(datapath,10,match,actions)
                    dicts = self.matches.get(datapath.id,{})
                    dicts[match] = (port_at_sw4,queue_id)
                    self.matches[datapath.id] = dicts
                    
                    port = self.queueref.get(datapath.id,{})
                    self.queueref[datapath.id] = port
                    
                    queue = port.get(port_at_sw4,{})
                    queue.setdefault(queue_id,[0,semaphore.Semaphore(1)])
                    with queue[queue_id][1]:
                        queue[queue_id][0] += 1
                        port[port_at_sw4] = queue
                    
            """   

                          

                    #get path here
            """
                    sw_list = get_all_switch(self)
                    switches = [switch.dp.ip for switch in switch_list]
                    self.logger.debug(switches)
                    links_list = get_all_link(self)
                    links = [(link.src.dpid,link.dst.dpid,{'port':link.src.port_no}) for link in links_list]
            """


#                self.send_event_to_observers(Reply(req))
                 
            """
                1. get flow
                2. find path
                3. get queues
                4. add-flow
            """
     
    """add to table 0
    """
    def add_flow(self, datapath, priority, match, actions, buffer_id=None,idle_timeout=60):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info("add-flow-policy %s",match)

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        """add paramter table_id=consts.ROUTIN_TABLE to OFPFlowMod
        """
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.POLICY_TABLE,idle_timeout=idle_timeout,buffer_id=buffer_id,
                                    priority=priority, match=match,flags=ofproto.OFPFF_SEND_FLOW_REM,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.POLICY_TABLE,idle_timeout=idle_timeout,priority=priority,
                                    match=match,flags=ofproto.OFPFF_SEND_FLOW_REM, instructions=inst)
        self.logger.debug("add-flow-policy %s",mod)
        datapath.send_msg(mod)


            #self.send_event_to_observers(Reply())

