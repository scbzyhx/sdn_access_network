#! /usr/bin/env python

import urllib
import urllib2
IP = '114.212.85.181'
PORT = '8080'
URL = '/request/bandwidth'

request = {}
request['action'] = ('req_bw',2000000)
request['user'] = 'None'
request['flows'] = []

flows = request['flows']

flow={}
flow['src'] = '114.212.85.130' #ip
flow['dst'] = '192.168.111.52'
flow['proto'] = 'tcp' #or udp
flow['src_port'] = 1234 #int
flow['dst_port'] = 4321
flows.append(flow)


req=urllib2.Request('http://'+IP+':'+PORT+URL,str(request))
#req=urllib2.Request('http://p.nj',urllib.urlencode({"action":"login","username":"mg1333068","password":"513701199009276512"}))
#req.add_header("Referer","http://p.nju.edu.cn/portal/portal_io.do")
resp=urllib2.urlopen(req)
print resp.read()
