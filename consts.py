#! /usr/bin/python
from ryu.ofproto import ofproto_v1_3 as ofproto

ROUTING_PRIORITY = ofproto.OFP_DEFAULT_PRIORITY
POLICY_ROUTING = ofproto.OFP_DEFAULT_PRIORITY

#routing flow are put into the second talbe.the table id is 1
ROUTING_TABLE = 1
POLICY_TABLE = 0

DEFAULT_QUEUE = 1
PRIORITY_QUEUE = 0
