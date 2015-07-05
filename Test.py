import logging

from ryu.base import app_manager
from ryu.controller import handler
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.ofproto import ofproto_v1_3
from ryu.controller import dpset
from ryu.controller import event

from events import Req as Req
import events

class TestEvent(event.EventBase):
    def __init__(self):
        pass
class Test(app_manager.RyuApp):
    
    _EVENTS=[events.Reply,TestEvent]
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self,*args,**kwargs):
        super(Test,self).__init__(*args,**kwargs)

        hdlr = logging.StreamHandler()
        fmt_str = '[RT][%(levelname)s] IN [%(filename)s.%(funcName)s]: %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Initializaing logging")

    @handler.set_ev_cls(Req)
    def _handler(self,ev):
        print "handler"
        self.send_event_to_observers(TestEvent())
        
    @handler.set_ev_cls(TestEvent)
    def testEventHandler(self,ev):
        self.logger.debug("hello I am in TestEvent")
