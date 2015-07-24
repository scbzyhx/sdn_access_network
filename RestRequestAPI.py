# Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
import numbers
import socket
import struct
import ast

import json
from webob import Response

from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import WSGIApplication,route
from ryu.base import app_manager
from ryu.controller import dpset
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.exception import OFPUnknownVersion
from ryu.exception import RyuException
from ryu.lib import dpid as dpid_lib
from ryu.lib import hub
from ryu.lib import mac as mac_lib
from ryu.lib import addrconv
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_2
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.controller.dpset import DPSet

from events import Req
from Test import Test
import events
from filtering  import Filter
from policy import Policy
from NIB import NIB
from simple_switch_13 import SimpleSwitch13
from host_tracker import HostTracker
# =============================
#          REST API
# =============================
#
#  Note: specify switch and vlan group, as follows.
#   {switch_id} : 'all' or switchID
#   {vlan_id}   : 'all' or vlanID
#


UINT16_MAX = 0xffff
UINT32_MAX = 0xffffffff
UINT64_MAX = 0xffffffffffffffff

#ETHERNET = ethernet.ethernet.__name__
#VLAN = vlan.vlan.__name__
#IPV4 = ipv4.ipv4.__name__
#ARP = arp.arp.__name__
#ICMP = icmp.icmp.__name__
#TCP = tcp.tcp.__name__
#UDP = udp.udp.__name__

MAX_SUSPENDPACKETS = 50  # Threshold of the packet suspends thread count.

REST_RESULT = 'reult'
REST_DETAILS = 'default'
REST_OK = 'ok'
REST_NG = 'not ok'
REST_ALL = 'failure'


SWITCHID_PATTERN = dpid_lib.DPID_PATTERN + r'|all'
VLANID_PATTERN = r'[0-9]{1,4}|all'


REQ_TIMEOUT = 5


class NotFoundError(RyuException):
    message = 'Router SW is not connected. : switch_id=%(switch_id)s'


class CommandFailure(RyuException):
    pass

class RestRequestAPI(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,
                    ofproto_v1_2.OFP_VERSION,
                    ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'dpset': dpset.DPSet,
                 'wsgi': WSGIApplication,
#                 'test': Test,
                 'filter':Filter,
                 'policy':Policy,
                 'nib':NIB,
                 'dpset':DPSet,
                 'simpleswitch13':SimpleSwitch13,
                 'host_tracker':HostTracker
#'check':Check
                }
    _EVENTS = [Req]

    def __init__(self, *args, **kwargs):
        super(RestRequestAPI, self).__init__(*args, **kwargs)
        RequestController.set_logger(self.logger)
        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)
#DEBUG
        self.logger.setLevel(logging.DEBUG)
        print kwargs
#
        wsgi = kwargs['wsgi']
        self.requests = {}
        self.data = {'reqs': self.requests,"RyuApp" : self}

        mapper = wsgi.mapper
        wsgi.registory['RequestController'] = self.data
        
        path = '/request/bandwidth'
        mapper.connect(None,path,controller=RequestController,
                       requirement=None,
                       action='req_bw',
                       conditions=dict(method=['POST']))
#TODO
    @set_ev_cls(events.Reply)
    def RespHandler(self,ev):
        self.logger.debug("GOT reply")
        ev.req.evt.set()
    def sendEvent(self,req):
        """
            send request to check module or policy module 
        """
        self.logger.debug("sendEvent")
        self.send_event_to_observers(req)




# REST command template
def rest_command(func):
    def _rest_command(*args, **kwargs):
        try:
            msg = func(*args, **kwargs)
            return Response(content_type='application/json',
                            body=json.dumps(msg))

        except SyntaxError as e:
            status = 400
            details = e.msg
        except (ValueError, NameError) as e:
            status = 400
            details = e.message

        except NotFoundError as msg:
            status = 404
            details = str(msg)

        msg = {REST_RESULT: REST_NG,
               REST_DETAILS: details}
        return Response(status=status, body=json.dumps(msg))

    return _rest_command

class RequestController(ControllerBase):
    _LOGGER = None
    def __init__(self,req,link,data,**config):
        super(RequestController,self).__init__(req,link,data,**config)
        print(data)
        self.reqs = data['reqs'] #store all requests
        self.app = data['RyuApp'] #RyuApp for sending event
        
    @classmethod
    def set_logger(cls,logger):
        cls._LOGGER = logger
        cls._LOGGER.propagate = False
        hdlr = logging.StreamHandler()
        #fmt_str = '[RT][%(levelname)s] Request=%(sw_id)s: %(message)s'
        fmt_str = '[RT][%(levelname)s] Request: %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        cls._LOGGER.addHandler(hdlr)
#@route("request","/request/bandwidth",methods=["POST"])
    @rest_command
    def req_bw(self,req,**_kwargs):
        """1. add something to self.reqs in addtion to and hub.Event()
           2. self.app.SendEvent
           3. event.wait() 
        """
        self.reqs[req.client_addr] = _kwargs
        for realreq in req.POST.keys():
            reqdict = ast.literal_eval(realreq)
            tmpReq = Req(req,reqdict['flows'],reqdict["action"])
            evt = hub.Event()
            tmpReq.evt = evt
            self.app.sendEvent(tmpReq)
            if evt.wait(REQ_TIMEOUT) == True:
                self._LOGGER.info("Request SUCCESS")
                return {REST_RESULT:REST_OK,REST_DETAILS:"request sucess!"}
            else:
                self._LOGGER.info("Request TIMEOUT")
                return {REST_RESULT:REST_NG,REST_DETAILS:'timeout'}


