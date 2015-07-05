#! /usr/bin/python

#self-defined event used to communicate between different components
#

from ryu.controller.event import EventBase as EventBase
from ryu.ofproto.ofproto_v1_3_parser import OFPMatch
#a request from client
#
#@req, an Request object,including all info of request
#@flow, indicate an flow, and OFPMatch object, but just some of its' field
#@action, undefined
class Req(EventBase):
    def __init__(self,req,flow,action):
        self.req = req
        self.flow = flow
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

if __name__ == "__main__":
    "test"
    print "test"

