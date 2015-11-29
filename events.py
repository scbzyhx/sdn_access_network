#! /usr/bin/python

#self-defined event used to communicate between different components
#

from ryu.controller.event import EventBase as EventBase
#a request from client
#
#@req, an Request object,including all info of request
#@flow, indicate an flow, and OFPMatch object, but just some of its' field
#@action, undefined
class Req(EventBase):
    def __init__(self,src,req,flow,action):
        self.src = src #it is an object of RyuApp
        self.req = req
        self.flows = flow
        self.action = action

#
#@req is an object of Request
#@status, means sucess or failure
class Reply(EventBase):
    def __init__(self,req,status = "success"):
        self.req = req
        self.status = status
 

#
#just a wraper event of Req  between filtering and policy
#@req, an object of Req
class ReqWrapper(EventBase):
    def __init__(self,req):
        self.req = req

class ReqHost(EventBase):
    def __init__(self,mac,ip=None):
        self.mac = mac
        self.ip = ip


class MarkReversedEvent(EventBase):
    def __init__(self,ipv4_src,ipv4_dst,ip_proto=None,sport=None,dport=None):
        self.ipv4_src = ipv4_src
        self.ipv4_dst = ipv4_dst
        self.ip_proto = ip_proto
        self.sport = sport
        self.dport = dport

class FlowEvent(EventBase):
    def __init__(self,flows,dpid,ofport,qid,time):
        self.flows = flows
        self.time = time
        self.dpid = dpid
        self.ofport = ofport
        self.qid = qid
    def __str__(self):
        s = "%s|%d|%d|%d|%s" % (self.time,self.dpid,self.ofport,self.qid,self.flows)
        return s
    def __repr__(self):
        s = "%s|%d|%d|%d|%s" % (self.time,self.dpid,self.ofport,self.qid,self.flows)
        return s




class FlowRateEvent(EventBase):
    def __init__(self,dpid,ofport,qid,time,bw,rate):
        self.dpid = dpid
        self.ofport = ofport
        self.qid = qid
        self.time = time
        self.bw = bw
        self.rate = rate
    
    def __str__(self):
        s = "%s|%d|%d|%d|%f|%f" %(self.time,self.dpid,self.ofport,self.qid,self.bw,self.rate)
        return s
    def __repr__(self):
        s = "%s|%d|%d|%d|%f|%f" %(self.time,self.dpid,self.ofport,self.qid,self.bw,self.rate)
        return s


if __name__ == "__main__":
    pass
    import time
    flowe = FlowEvent([{"ipv4_src":"192.168.121.1","ipv4_dst":"192.168.131.1"}],1234,123,123,time.time())
    print flowe

    fr = FlowRateEvent(12354,123,123,time.time())
    print fr
