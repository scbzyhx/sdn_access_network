#! /usr/bin/python

'''
This document defines how to store network informationi base of each switch
map[switch] = nib
nib = {
    "sw":OFSwitch,
    "ports" :
    {
        "desc":OFPort,
        "queues":[OFQueues]
    } 
}
OFQueues {priority,max-rate,min-rate,queue-len,}
'''
