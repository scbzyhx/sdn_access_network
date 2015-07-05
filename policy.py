"""
author:yhx
email:scbzyhx@gmail.com

"""
import logging
from eventlet import semaphore 

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller.event import EventBase

from events import Req
from events import Reply
from events import ReqWrapper

class InternalEvent(EventBase):
    def __init__(self,*args,**kwargs):
        pass

class Policy(app_manager.RyuApp):
    
    _EVENTS = [Reply]
    def __init__(self,*args,**kwargs):
        super(Policy,self).__init__(*args,**kwargs)
        
       
        hdlr  = logging.StreamHandler()
        fmt_str = '[RT][%(levelname)s] IN [%(funcName)s]: %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Ininitializing Policy")
        
        self.requestQ = [] #a request queue
        self.sem = semaphore.Semaphore(1)

#TODO
    @set_ev_cls(ReqWrapper)
    def requestHandler(self,ev):
        """
           request handler
        """
        #put it into queueQ
        self.logger.debug("ReqWrapper %s",type(ev))
        self.send_event_to_observers(Reply(ev.req,"success"))
#TODO   
    def replyRequest(self):
        while True:
            #do something
            semTmp = None
            with self.sem:
                semTmp = self.requestQ
                self.requestQ = []
            
            """
            Now really reply to requests
            """
            #need to sleep?


