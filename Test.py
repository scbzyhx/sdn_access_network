from ryu.base import app_manager
from ryu.controller import handler
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER,MAIN_DISPATCHER
from ryu.ofproto import ofproto_v1_3
from ryu.controller import dpset
from events import Request as Req
class Test(app_manager.RyuApp):
##   _CONTEXTS = {"RestRequestAPI":RestRequestAPI,
##                 "wsgi":WSGIApplication,
##                 "dpset":dpset.DPSet}
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self,*args,**kwargs):
        print "Test"
        print kwargs
        super(Test,self).__init__(*args,**kwargs)
#self.rest = kwargs["RestRequestAPI"]
#       print self.event_handler
#        print self.observers
        self.observe_event(Req)

    @handler.set_ev_cls(Req)
    def handler(self,ev):
        print "handler"
#   @handler.set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
#    def hehe(self,ev):
        print dir(ev)
    
