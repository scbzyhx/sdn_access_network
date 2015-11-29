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

from events import FlowRateEvent,FlowEvent

class LOG_INFO(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(LOG_INFO, self).__init__(*args, **kwargs)
        self.rate_logger = open("rate.log",'wr')
        self.flow_logger = open("flow.log",'wr')

        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)

    @set_ev_cls(FlowRateEvent)
    def flowrate_handler(self, ev):
        self.rate_logger.write("%s\n" % ev)
        self.rate_logger.flush()

    @set_ev_cls(FlowEvent)
    def flowevent_handler(self,ev):
        self.flow_logger.write("%s\n" % ev)
        self.flow_logger.flush()
    def __del__(self):
        if self.rate_logger is not None:
            self.rate_logger.close()
        if self.flow_logger is not None:
            self.flow_logger.close()
