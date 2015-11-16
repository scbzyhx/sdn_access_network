#! /usr/bin/env python

import subprocess
import simplejson
import logging
import time

from np import random 

import urllib
import urllib2
IP = '114.212.85.130'
PORT = '8080'
URL = '/request/bandwidth'
"""
request = {}
request['action'] = ('req_bw',2000000)
request['user'] = 'None'
request['flows'] = []

flows = request['flows']

flow={}
flow['src'] = '114.212.85.130' #ip
flow['dst'] = '192.168.111.52'
flow['proto'] = 'tcp' #or udp
#flow['src_port'] = 1234 #int
#flow['dst_port'] = 4321
flows.append(flow)


#req=urllib2.Request('http://'+IP+':'+PORT+URL,str(request))
#resp=urllib2.urlopen(req)
#print resp.read()

"""
requests = [{"action":("req_bw",0),"user":'None',"flows":[{"src":"119.81.143.2","dst":"192.168.111.52","proto":"tcp"}]},
            {"action":("req_bw",0),"user":'None',"flows":[{"src":"119.81.143.2","dst":"192.168.111.53","proto":"tcp"}]}
#            {"action":("req_bw",0),"user":'None',"flows":[{"src":"119.81.143.2","dst":"","proto":"tcp"}]}
           ]
files = ['h1.pcap','h2.pcap']

REPLAY_COMMAND = "tcpreplay" #interafce and filename
MAX_NUM =  len(files)
LAM = 30      #paramter for poisson distribution
#default handler
logging.basicConfig()
LOG = logging.getLogger(__name__)


def send_request(request):
    req=urllib2.Request('http://'+IP+':'+PORT+URL,str(request))
    resp = urllib2.urlopen(req)
    resp = simplejson.loads(resp.read())
#print type(resp)
    return (resp["result"],resp["details"])

def replay(intf,filename):
    args = REPLAY_COMMAND# %(intf,filename)
    
    p = subprocess.Popen(["tcpreplay","-i",intf,filename])
    return p

def waitAll(procs):
    exit_code = []#[0 for i in xrange(len(procs))]


    for i,p in enumerate(procs):
        exit_code.append(p.wait())
    return exit_code

def request_replay():
    assert len(requests) >= len(files)
    procs = []
    intervals = random.poisson(LAM,len(files))
    intervals[0] = 0 
    for idx in xrange(len(files)):
        "send requests, if success replay traffic"
        time.sleep(intervals[idx])
        result,details = send_request(requests[idx])
        
        if result == "ok" and details == "success":
            procs.append(replay("h1-eth0",files[idx]))
        else:
            LOG.warning("request failed")
            break
    return procs
        



if __name__ == "__main__":
#l = [replay("h1-eth0",filenames[i]) for i in xrange(MAX_NUM)]
#    print waitAll(l)
    results = waitAll(request_replay())
    for result in results:
        print result
