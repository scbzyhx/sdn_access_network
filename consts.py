#! /usr/bin/python
from ryu.ofproto import ofproto_v1_3 as ofproto

ROUTING_PRIORITY = ofproto.OFP_DEFAULT_PRIORITY
POLICY_ROUTING = ofproto.OFP_DEFAULT_PRIORITY

#routing flow are put into the second talbe.the table id is 1
ROUTING_TABLE = 1
POLICY_TABLE = 0

DEFAULT_QUEUE = 0
PRIORITY_QUEUE = 1
HIGHEST_PRIORITY_QUEUE = 2

EF = 0x2e
PHB = 0x10 #010 000 : ip prededure, middle class priority
DEFAULT = 0x0

GW_DP = 4
KEY_PORT = 2


ROUTING_RULE_PRIORITY = 5
FEEDBACK_QUEUE_RULE_PRIORITY = 6
POLICY_RULE_PRIORITY = 10

