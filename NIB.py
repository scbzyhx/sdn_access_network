#! /usr/bin/python
import logging

from ryu.base import app_manager
from switch import OVSSwitch
from ryu.lib.ovs.vsctl import VSCtlQueue
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER,DEAD_DISPATCHER
from ryu.controller import ofp_event
from ryu import cfg
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
    def __init__(self,*args,**kwargs):
        super(NIB,self).__init__(args,kwargs)
        self.dps = {}
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

    def addQueue(self,datapathID,port_no,vsctlqueue):
        """add queue to 
        """
        pass
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
        self.logger.debug(datapath.socket.getpeername()[0]) #IP address
        remoteIP = "tcp:"+datapath.socket.getpeername()[0] + ":" + CTRL_PORT
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.dps:
                self.logger.debug("register datapath: %016x",datapath.id)
                #TODO: what shoud CONF be, it is unspecified
                self.dps[datapath.id] = OVSSwitch(CONF=CONF,datapath_id=datapath.id,ovsdb_addr=remoteIP)
        elif ev.state == DEAD_DISPATCHER:
            if self.dps.has_key(datapath.id):
                del self.dps[datapath.id]
                self.logger.debug("unregister datapath:%016x",ev.datapath.id)
            else:
                self.logger.warn("unregister unconnected-datapath:%016x",ev.datapath.id)
