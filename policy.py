"""
author:yhx
email:scbzyhx@gmail.com

"""
import logging

from ryu.base.app_manager import RyuApp
from ryu.lib.handler import set_ev_cls
from ryu.controller.event import EventBase

from events import Req
from events import Reply


class InternalEvent(EeventBase):
    def __init__(self,*args,**kwargs):
        pass

class Policy(app_manager.RyuApp):
    
    _EVENTS = [Reply]
    def __init__(self,*args,**kwargs):
        super(Policy,self).__init__(*args,**kwargs)
        
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Ininitializing Policy")
        
        self.requestQ = [] #a request queue

    @set_ev_cls(Req)
    def requestHandler(self,ev):
        """
           request handler
        """
        #put it into queueQ
