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
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types as ether
from ryu.lib.packet import in_proto as inet

from events import MarkReversedEvent
import consts

class GW_Mark(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(GW_Mark, self).__init__(*args, **kwargs)
        self.dpset = app_manager.lookup_service_brick("dpset")

        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)

    @set_ev_cls(MarkReversedEvent)
    def _handle_reversed_flow(self,ev):
        self.logger.debug("_handle_reversed_flow in %s",self.__class__)
        
        datapath = self.dpset.get(consts.GW_DP)
        if datapath is None:
            return 

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        fflow = {
                    'eth_type':ether.ETH_TYPE_IP,
                    'ipv4_src':ev.ipv4_dst,
                    'ipv4_dst':ev.ipv4_src,
                    'ip_proto':ev.ip_proto
                }
        #no dscp, because we are going to set it
        if ev.sport is not None and ev.dport is not None:
            if ev.ip_proto == inet.IPPROTO_TCP:
                fflow['tcp_src'] = ev.dport
                fflow['tcp_dst'] = ev.sport
            elif ev.ip_proto == inet.IPPROTO_UDP:
                fflow['udp_src'] = ev.dport
                fflow['udp_dst'] = ev.sport
            "else do nothing"
        rmatch = parser.OFPMatch(**fflow)

        action_set_dscp = parser.OFPActionSetField(ip_dscp=consts.EF)
        inst_to_next_table = parser.OFPInstructionGotoTable(consts.ROUTING_TABLE)

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             [action_set_dscp])]
        inst.append(inst_to_next_table)

        
          
        mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.POLICY_TABLE,idle_timeout=20,priority=10,
                                    match=rmatch, instructions=inst)
        
        self.logger.debug("mark flow command = %s",mod)
        datapath.send_msg(mod)
