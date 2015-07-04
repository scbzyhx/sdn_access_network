"""
@author:yhx
@email:scbzyhx@gmail.com
this module check the request
"""
import logging

from ryu.base import app_manager
from ryu.controller import handler
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.ofproto import ofproto_v1_3
from ryu.controller import dpset

from events import Req as Req
from events import Reply
class Check(app_manager.RyuApp):
    
    _EVENTS = [Reply]
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self,*args,**kwargs):
        super(Check,self).__init__(*args,**kwargs)

        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("initializing check module")
        
    @handler.set_ev_cls(Req)
    def handler(self,ev):
        """
        if success, then send to policy modules
        if illeage, send deny reply
        """
        self.send_event_to_observers(Reply(ev,"success"))
        
    
