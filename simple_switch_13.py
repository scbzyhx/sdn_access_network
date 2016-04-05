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
from ryu.lib.packet import udp, tcp

from events import MarkReversedEvent, Reply,Req
import consts
from flow_wrapper import Flow_Wrapper
VIDEO_PORT = 8081

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _EVENTS = [MarkReversedEvent,Req]
    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        self.dpset = app_manager.lookup_service_brick("dpset")
        self.flowDB = set()

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

        #For non-IPv4 flows
        
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        #priority 0 means lowest priority
        self.add_flow(datapath, 0, match, actions,None,0)
        
        #setup multiple level priority queues
        #1. LOWEST priority
        dscp_queue = {
                consts.EF : consts.HIGHEST_PRIORITY_QUEUE,
                consts.PHB: consts.PRIORITY_QUEUE,
                consts.DEFAULT: consts.DEFAULT_QUEUE
                }
        
        kwargs = {"eth_type":0x800} #dependicy in OpenFlow protocols, after 1.1 maybe
        
        for dscp, queue in dscp_queue.items():
            print "setup feedback queues"
            ##write setqueue action to action set and direct it to routing table
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_WRITE_ACTIONS,[parser.OFPActionSetQueue(queue)]),
                    parser.OFPInstructionGotoTable(consts.ROUTING_TABLE)] 
            
            kwargs['ip_dscp'] = dscp
            match = parser.OFPMatch(**kwargs)

            mod = parser.OFPFlowMod(datapath=datapath, table_id=consts.POLICY_TABLE,idle_timeout=0,priority=consts.FEEDBACK_QUEUE_RULE_PRIORITY,
                                       match=match, instructions=inst)
        
                
            datapath.send_msg(mod)



    def add_flow(self, datapath, priority, match, actions, buffer_id=None,idle_timeout=30,table_id=consts.ROUTING_TABLE):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.debug("add-flow %s",match)

        #inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
        #                                     actions)]
        #add it into action set
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_WRITE_ACTIONS,
                                             actions)]

        """add paramter table_id=consts.ROUTIN_TABLE to OFPFlowMod
        """
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,idle_timeout=idle_timeout,buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,idle_timeout=idle_timeout,priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(Reply)
    def _reply_handler(self,ev):
        self.logger.debug("reply arrived here: %s",ev)
        

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

        #self.logger.debug("packet in %s %s %s %s, %x", dpid, src, dst, in_port,eth.ethertype)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        kwargs = {'in_port':in_port,
                  'eth_dst':dst,
                  'eth_type':dl_type
                 }
        """action: Enqueue
        """
#        outqueue = parser.OFPActionSetQueue(consts.DEFAULT_QUEUE)
        priority = consts.ROUTING_RULE_PRIORITY
        for p in pkt.protocols:
            if type(p) == type(""):
                continue
           
            if p.protocol_name == "ipv4":
                """
                first, get the flow
                """
                kwargs['ip_proto'] = p.proto
                kwargs['ipv4_src'] = p.src
                kwargs['ipv4_dst'] = p.dst
                #match = parser.OFPMatch(in_port=in_port,eth_dst=dst,eth_type=dl_type,ip_proto=p.proto,ip_dscp=consts.EF,ipv4_src=p.src,ipv4_dst=p.dst)
                sport = None
                dport = None
                tpkt = None

                if p.proto == inet.IPPROTO_TCP:
                    tpkt = pkt.get_protocol(tcp.tcp)
                    kwargs['tcp_src'] = tpkt.src_port
                    kwargs['tcp_dst'] = tpkt.dst_port
                elif p.proto == inet.IPPROTO_UDP:
                    tpkt = pkt.get_protocol(udp.udp)
                    kwargs['udp_src'] = tpkt.src_port
                    kwargs['udp_dst'] = tpkt.dst_port
                if tpkt is not None:
                    sport = tpkt.src_port
                    dport = tpkt.dst_port
                    
                if  (p.tos >> 2 ) == consts.EF:
                    """
                    prepare exactly match
                    """
#                    self.logger.debug("type of p is %s", type(p))
#                    self.logger.debug("p.tos eq 0x2e here")
#                    outqueue = parser.OFPActionSetQueue(consts.PRIORITY_QUEUE)
#
#                    priority = 10
#                    kwargs['ip_dscp'] = consts.EF
#                    #test
#                    #dscp  = consts.EF
#
#                    """
#                    set action to mark Reversed flow, ON GW_DP
#                    """
#                    self._handle_reversed_flow(datapath,p.src,p.dst,p.proto,sport,dport)

                elif self.is_video(**kwargs):
                    
                    """
                      send request
                      elif it is video flow, then send a request 
                    """
                        
                    flow ={"src":kwargs['ipv4_src'],"dst":kwargs['ipv4_dst']}
                    if sport is not None and dport is not None and (kwargs["ip_proto"] in (inet.IPPROTO_TCP,inet.IPPROTO_UDP)):
                        flow['src_port'] = VIDEO_PORT#sport
                        flow['dst_port'] = None#dport
                        flow['proto'] = 'tcp' if kwargs['ip_proto'] == inet.IPPROTO_TCP else 'udp'
                        self.logger.debug("sending request %s",flow)
                        flow_wrapper_object = Flow_Wrapper(ipv4_src=flow['src'],ipv4_dst=flow['dst'],ip_proto=flow['proto'],src_port=flow['src_port'],dst_port=flow['dst_port'])
                        if flow_wrapper_object not in self.flowDB:
                            self.flowDB.add(flow_wrapper_object)
                            self.send_event_to_observers(Req(self.name,None,[flow],('req_bw',0)))
                        #else do nothing

                    #else donothing

                break

        match = parser.OFPMatch(**kwargs)      
        actions = [parser.OFPActionOutput(out_port)] # queue is set by policy
        #actions = [outqueue,parser.OFPActionOutput(out_port)]
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.logger.debug(dl_type)
        #if dl_type == ether.ETH_TYPE_IP: #ipv4
        #            match = parser.OFPMatch(in_port=in_port, eth_dst=dst,eth_type=dl_type,ip_dscp=dscp)
        #            else:
        #            match = parser.OFPMatch(in_port=in_port,eth_dst=dst,eth_type=dl_type)
          
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

    def is_video(self,**kwargs):
        """
            More details
        """
        self.logger.debug("is_video,match= %s",kwargs)
        tcp_src = kwargs.get('tcp_src')
        if tcp_src is None:
            return False
        return True and tcp_src == VIDEO_PORT

    def _handle_reversed_flow(self,datapath,ipv4_src,ipv4_dst,ip_proto,sport,dport):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        
        #if in flow from gateway, then ignore reversed flow 
        if datapath.id == consts.GW_DP:
            return

        self.send_event_to_observers(MarkReversedEvent(ipv4_src,ipv4_dst,ip_proto,sport,dport))
        
        """
        #no dscp, because we are going to set it
        rmatch = OFPMatch(eth_src=match['eth_dst'],eth_dst=match['eth_src'],eth_type=match['eth_type'],ipv4_src=match['ipv4_dst'],ipv4_dst=['ipv4_src'])
        action_set_dscp = parser.OFPActionSetField(ip_dscp=consts.EF)
        inst_to_next_table = parser.OFPInstructionGotoTable(consts.POLICY_TABLE)

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             [action_set_dscp])]
        inst.append(inst_to_next_table)

        dp = self.dpset.get(consts.GW_DP)
        

        mod = parser.OFPFlowMod(datapath=dp, table_id=consts.POLICY_TABLE,idle_timeout=idle_timeout,priority=10,
                                    match=rmatch, instructions=inst)
        dp.send_msg(mod)
        """

