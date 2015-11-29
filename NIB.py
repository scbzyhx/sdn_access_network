#! /usr/bin/python
import logging

from ryu.base import app_manager
from switch import OVSSwitch
from ryu.lib.ovs.vsctl import VSCtlQueue
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER,DEAD_DISPATCHER
from ryu.controller import ofp_event
from ryu.controller.dpset import EventPortAdd
from ryu import cfg
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib import ofctl_v1_3 as ofctl

import consts
'''
This document defines how to store network informationi base of each switch
'''

#LOG = logging.getLogger()


#LOG.setLevel(logging.DEBUG)
CTRL_PORT = "6622"
CONF = cfg.CONF
#CONF.register_opts([
#    cfg.IntOpt('ovsdb_timeout', default=2,
#                help='ovsdb_timeout value.')
#])
class NIB(app_manager.RyuApp):
    
    OFP_VERSION = [ofproto_v1_3.OFP_VERSION]
    def __init__(self,*args,**kwargs):
        super(NIB,self).__init__(args,kwargs)
        self.dps = {}
        self.waiters = {}
        self.datapaths = {}
        
        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)

    def addSwitch(self,datapathID,ovswitch):
        self.dps.setdefault(datapathID,None)
        self.dps[datapathID] = ovswitch

    def delSwitch(self,datapathID):
        if self.dps.has_key(datapathID):
            del self.dps[datapathID]
    #return None or OVSwitch
    def getSwitch(self,datapathID):
        return self.dps.get(datapathID)

    def start(self):
        super(NIB,self).start()
        self.logger.debug("start here ing")
        self.threads.append(hub.spawn(self.queue_stats_request))


    #@queues are a list of dict,
    #each dict contains two keys: "min-rate" and "max-rate", the value are strings too
    #queue["queue-id"] is the queue ID that stored
    #
    def addQueue(self,datapathID,port_no,queues_desc):
        """add queue to 
        """
        ovsswitch = self.dps[datapathID]
        return ovsswitch.setQueues(port_no,queues_desc) #return True or False
    

    def delQueue(self,datapathID,port_no,queueID):
        """
            delete a queue by ID
        """
        pass
    #datapath connected
    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER,DEAD_DISPATCHER])
    def dpStateEventHandler(self,ev):
        datapath = ev.datapath
        self.logger.debug("datpath type is %s",type(datapath))
#print dir(datapath)
#        print datapath.ofproto
#        print dir(datapath.ofproto)
        parser = datapath.ofproto_parser

        remoteIP = "tcp:"+datapath.socket.getpeername()[0] + ":" + CTRL_PORT
#self.logger.debug(dir(datapath))
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.dps:
                self.logger.debug("register datapath: %016x",datapath.id)
                self.dps[datapath.id] = OVSSwitch(CONF=CONF,datapath_id=datapath.id,ovsdb_addr=remoteIP)
                self.datapaths[datapath.id] = datapath

                #add a flow, make flow to routing table (table id is 1)
                inst = [parser.OFPInstructionGotoTable(consts.ROUTING_TABLE)]
                match = parser.OFPMatch()
                mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.POLICY_TABLE,priority=0,
                                    match=match, instructions=inst)
                datapath.send_msg(mod)
    

        elif ev.state == DEAD_DISPATCHER:
            if self.dps.has_key(datapath.id):
                del self.dps[datapath.id]
                self.logger.debug("unregister datapath:%016x",ev.datapath.id)
            else:
                self.logger.warn("unregister unconnected-datapath:%0x16x",ev.datapath.id if  ev.datapath.id is not None else -1)
    #
    @set_ev_cls(ofp_event.EventOFPQueueStatsReply,MAIN_DISPATCHER)
    def stats_handler(self,ev):
        stats_reply = ev.msg #an OFPQueueStatsReply object
        dpid = stats_reply.datapath.id
        xid = stats_reply.xid
        
        waiters = self.waiters.get(dpid,None)
        if waiters is None:
            return
        if waiters.has_key(xid):
            waiters[xid][1].append(stats_reply)
            waiters[xid][0].set()
        

    def queue_stats_request(self):
        self.logger.debug("queeu_stats_requests")
        self.logger.debug("print queue_stats")

        while True:
            hub.sleep(1)
            "ofctl.get_queue_stats()"
#self.logger.debug("ofctl start")
            for dp in self.dps.keys():
                stats = ofctl.get_queue_stats(self.datapaths[dp],self.waiters)[str(self.datapaths[dp].id)]
                sw = self.dps[dp]
                for st in stats:
                    sw.updateCounter(st["port_no"],st["queue_id"],st["duration_sec"],st["duration_nsec"],st["tx_bytes"],st["tx_packets"])
                    



