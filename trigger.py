# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License

import logging

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from events import  Reply,Req
from threading import Timer
import time

TIME_INTERVAL = 2
class Trigger(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _EVENTS = [Req]
    def __init__(self, *args, **kwargs):
        super(Trigger, self).__init__(*args, **kwargs)
        self.t = Timer(TIME_INTERVAL,self.trigger)

        self.logger.propagate = False
        hdlr = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
        hdlr.setFormatter(fmt)
        self.logger.addHandler(hdlr)
        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)

        #self.t.start()


    @set_ev_cls(Reply)
    def _reply_handler(self,ev):
        self.logger.info("reply arrived here(%s): %s",self.name,ev)
        
    def trigger(self):
        while True:
            self.logger.info("triggered")
            flow = {"src":"0.0.0.0"}
            req = Req(self.name,None,[flow],('req_bw',0))
            #req.src = self.__class__.__name__

            self.send_event_to_observers(req)
            time.sleep(TIME_INTERVAL)
