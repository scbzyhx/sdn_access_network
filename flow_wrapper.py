#! /usr/bin/env python
class Flow_Wrapper(object):
    """
        I do nothing, but add __hash__ and __eq__
    """
    def __init__(self, **kwargs):
        self.ipv4_src = kwargs['ipv4_src']
        self.ipv4_dst = kwargs['ipv4_dst']
        self.ip_proto = kwargs['ip_proto']
        self.tp_src = kwargs['src_port']
        self.tp_dst = kwargs['dst_port']

    def __hash__(self):

        """To store in dict or set.
           only, ipv4.src ipv4.dst,ip.type, tos, tcp.sport, tcp.dport
        """
        return hash((self.ipv4_src,self.ipv4_dst,self.ip_proto,self.tp_src,self.tp_dst))

    def __eq__(self,other):
        """
            only, ipv4.src ipv4.dst,ip.type, tos, tcp.sport, tcp.dport
        """
        return (self.ipv4_src == other.ipv4_src and self.ipv4_dst == other.ipv4_dst and \
                self.ip_proto == other.ip_proto and self.tp_src == other.tp_src and \
                self.tp_dst == other.tp_dst)



