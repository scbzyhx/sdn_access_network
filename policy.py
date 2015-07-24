"""
author:yhx
email:scbzyhx@gmail.com

"""
import logging
from eventlet import semaphore 

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller.event import EventBase
from ryu.lib import hub
from ryu.topology.api import get_link,get_all_link,get_switch,get_all_switch
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3_parser as ofproto
from ryu.lib.packet import ether_types as ether
from ryu.controller.handler import MAIN_DISPATCHER

from events import Req
from events import Reply
from events import ReqWrapper
from events import ReqHost #synchronized request

import consts

class InternalEvent(EventBase):
    def __init__(self,*args,**kwargs):
        pass

def cmp_list(list1,list2):
    if len(list1) != len(list2):
        return False
    for el in list1:
        if el not in list2:
            return False
    return True

class Policy(app_manager.RyuApp):
    _EVENTS = [Reply,ReqHost]
    def __init__(self,*args,**kwargs):
        super(Policy,self).__init__(*args,**kwargs)
        
#        self.host_tracker = kwargs["host_tracker"]
        hdlr  = logging.StreamHandler()
        fmt_str = '[RT][%(levelname)s] IN [%(funcName)s]: %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        self.logger.addHandler(hdlr)
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
#self.logger.debug("hello world")
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
#self.send_event_to_observers(Reply(ev.req,"success"))
#TODO   
    def replyRequest(self):
        while self.is_active:
            #do something
            semTmp = None
#            self.logger.debug("in reply thread")
            #speed up
            if len(self.requestQ) != 0:

                with self.sem:
                    semTmp = self.requestQ
                    self.requestQ = []
                    hub.sleep(0.1)
            else:
                hub.sleep(0.1)
                continue
            for req in semTmp:
                #for each request
                self.logger.debug(req.action)
                self.logger.debug(req.flows)
                hosttracker = app_manager.lookup_service_brick("HostTracker")
                sw_mac_to_port = app_manager.lookup_service_brick("SimpleSwitch13")
                self.logger.debug(sw_mac_to_port.mac_to_port)
                DP = 4
                sw_mac_to_port = sw_mac_to_port.mac_to_port.get(DP,{}) #5 is datapath id 
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
                    sw = self.nib.getSwitch(DP)              #yhx,4 4 4 4 4 4 4 4
#queue_id = sw.getQueue(port_at_sw4)
                    bw = req.action[1] #min bandwidth
                    if bw == 0:#
                        queue_id = sw.getQueueWithBW(port_at_sw4)
                    else:
                        queue_id = sw.getQueueWithBW(port_at_sw4,bw)
                    
                    datapath = self.dpset.get(DP)
                    parser = datapath.ofproto_parser
                    match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP,ipv4_src=srcIP,ipv4_dst=dstIP,ip_dscp=consts.PHB)
                    actions = [ parser.OFPActionSetQueue(queue_id),parser.OFPActionOutput(port_at_sw4)]
#self.logger.debug(match.to_jsondict())
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
                    
                   

                          

                    #get path here
                    """
                    sw_list = get_all_switch(self)
                    switches = [switch.dp.ip for switch in switch_list]
                    self.logger.debug(switches)
                    links_list = get_all_link(self)
                    links = [(link.src.dpid,link.dst.dpid,{'port':link.src.port_no}) for link in links_list]
                    """


                self.send_event_to_observers(Reply(req))
                 
                """
                1. get flow
                2. find path
                3. get queues
                4. add-flow
                """
     
    """add to table 0
    """
    def add_flow(self, datapath, priority, match, actions, buffer_id=None,idle_timeout=10):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.debug("add-flow-policy %s",match)

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
        
#        self.logger.debug("add-flow-policy %s",mod)
        datapath.send_msg(mod)


            #self.send_event_to_observers(Reply())


