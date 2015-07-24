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
from events import ReqWrapper

class Filter(app_manager.RyuApp):
    
    _EVENTS = [Reply,ReqWrapper]
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self,*args,**kwargs):
        super(Filter,self).__init__(*args,**kwargs)
        self.name = self.__class__

        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("initializing check module")
#TODO       
    @handler.set_ev_cls(Req)
    def handler(self,ev):
        """
        if success, then send to policy modules
        if illeage, send deny reply
        """
        self.logger.debug("filtering handler")
        self.send_event_to_observers(ReqWrapper(ev))
        
    
