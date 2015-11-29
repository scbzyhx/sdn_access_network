"""
author:yhx
email:scbzyhx@gmail.com

"""
import logging
from eventlet import semaphore,Timeout 
import time

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3_parser as ofproto
from ryu.lib.packet import ether_types as ether
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.lib.packet import in_proto as inet

from events import Req
from events import Reply
from events import ReqWrapper
from events import ReqHost #synchronized request
from events import FlowRateEvent


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
    return myknapsack(reqs,int(avail/BW_FACTOR)) #return (list of satisfied request, )

if __name__ == "__main__":
    items = [(144,990),(487,436),(210,673),(567,58),(1056,897)]
    reqs = {1:2}
    print knapsack(reqs,10)

class Policy(app_manager.RyuApp):
    _EVENTS = [Reply,ReqHost,FlowRateEvent]
    def __init__(self,*args,**kwargs):
        super(Policy,self).__init__(*args,**kwargs)
        
        hdlr  = logging.StreamHandler()
        fmt_str = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        self.logger.addHandler(hdlr)
        self.logger.propagate = False

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

        count = 0

        while self.is_active:
            #do something
            semTmp = None
            #self.logger.debug("in reply thread")
            #speed up
            hub.sleep(0.01)

            with self.sem:
                semTmp = self.requestQ
                self.requestQ = []
            
            start = time.clock()

            DP = consts.GW_DP                        #4
            ofport = consts.KEY_PORT                 #2 #(s4 -eth2)
            sw = self.nib.getSwitch(DP)              #yhx,4 4 4 4 4 4 4 4
            if sw is None:
                self.logger.debug("gatway(dpid=4)have not been registered by now" )
                continue
            

            #self.logger.debug(req.flows)
            #hosttracker = app_manager.lookup_service_brick("HostTracker")
            #sw_mac_to_port = app_manager.lookup_service_brick("SimpleSwitch13")
            
            try:
                count = (count + 1)%1000
                if count == 0:
                    sw.adjustBW(ofport,self.func)


            except Timeout as t:
                self.logger.debug(t)
                self.logger.debug("timeout when ajustbw,I should stop it here,but I did not!")

            if len(semTmp) == 0:
                continue

            requests = {}
            
            for index, req in enumerate(semTmp):
                bw = req.action[1]
                if bw == 0:
                    bw = sw.getMaxBW(ofport) #maxrate
                requests[index] = bw #req.action[1]

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

                    state = False
                    
                    for flow in req.flows:
                        srcIP  = flow.get('src',None)
                        dstIP = flow.get('dst',None)
                        srcPort = flow.get('src_port',None) #option
                        dstPort = flow.get('dst_port',None) #option
                        ip_proto = flow.get('proto',None)
                        if srcIP is None or dstIP is None  or ip_proto is None or queue_id is None:
                            self.logger.debug("not an legal flow")
                            if state is False and queue_id is not None:
                                sw.releaseQueue(ofport,queue_id)
                            print srcIP," ",dstIP," hahha  ",req.src
                            if srcIP == "0.0.0.0":
                                print srcIP
                                self.send_event(req.src,Reply(req,"failure"))
                            break

                        kflow = {"eth_type":ether.ETH_TYPE_IP,
                                 "ipv4_src":srcIP,
                                 "ipv4_dst":dstIP
                                 #"ip_dscp":consts.PHB
                                 }

                        if ip_proto == 'tcp':
                            kflow["ip_proto"] = inet.IPPROTO_TCP
                            
                            
                            if srcPort is not None:
                                kflow["tcp_src"] = srcPort
                            if dstPort is not None:
                                kflow["tcp_dst"] = dstPort

                        elif ip_proto == 'udp':

                            kflow["ip_proto"] = inet.IPPROTO_UDP
                            if srcPort is not None:
                                kflow["udp_src"] = srcPort
                            if dstPort is not None:
                                kflow["udp_dst"] = dstPort

                        match = parser.OFPMatch(**kflow)

                        actions = [ parser.OFPActionSetQueue(queue_id),parser.OFPActionOutput(ofport)]
                        self.add_flow(datapath,10,match,actions)
                        state = True

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
     
    """add to table 0
    """
    def add_flow(self, datapath, priority, match, actions, buffer_id=None,idle_timeout=60):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser


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
        self.logger.debug("add-flow-policy haha:%s" % mod)
        datapath.send_msg(mod)

    def func(self,dpid,ofport,qid,time,bw,rate):
        self.send_event_to_observers(FlowRateEvent(dpid,ofport,qid,time,bw,rate))


