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


import consts

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        if self.CONF.enable_debugger:
            self.logger.setLevel(logging.DEBUG)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        #priority 0 means lowest priority
        self.add_flow(datapath, 0, match, actions,None,0)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None,idle_timeout=30):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.debug("add-flow %s",match)

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        """add paramter table_id=consts.ROUTIN_TABLE to OFPFlowMod
        """
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.ROUTING_TABLE,idle_timeout=idle_timeout,buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.ROUTING_TABLE,idle_timeout=idle_timeout,priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src
        dl_type = eth.ethertype

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s, %x", dpid, src, dst, in_port,eth.ethertype)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        
        """action: Enqueue
        """
        outqueue = parser.OFPActionSetQueue(consts.DEFAULT_QUEUE)
        priority = 5
        dscp = 0
        for p in pkt.protocols:
#self.logger.debug(p)
            if type(p) == type(""):
                continue
            if p.protocol_name == "ipv4":
                if  (p.tos >> 2 ) == consts.EF:
                    self.logger.debug("p.tos eq 0x2e here")
                    outqueue = parser.OFPActionSetQueue(consts.PRIORITY_QUEUE)
                    priority = 10
                    dscp = p.tos >> 2
                    self.logger.debug(p)
                break

              
                
        #actions = [parser.OFPActionOutput(out_port)]
        #self.logger.debug(dir(parser))
        actions = [outqueue,parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.logger.debug(dl_type)
            if dl_type == ether.ETH_TYPE_IP: #ipv4
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst,eth_type=dl_type,ip_dscp=dscp)
            else:
                match = parser.OFPMatch(in_port=in_port,eth_dst=dst,eth_type=dl_type)
          
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, priority, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, priority, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
