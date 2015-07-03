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
class Request(EventBase):
    def __init__(self,req,flow,action):
        self.req = req
        self.flow = flow
        self.action = action
if __name__ == "__main__":
    "test"
    print "test"

