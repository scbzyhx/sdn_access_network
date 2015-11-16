#! /usr/bin/env python

from ofproto_v1_3_parser imoprt OFPMatch


class OFPMatch_Wrapper(object):
    """
        I do nothing, but add __hash__ and __eq__
    """
    FIELDS = ['ipv4_src','ipv4_dst','ip_proto','tcp_src','tcp_dst','ip_dscp']
    def __init__(self, ofpmatch):
        self.ofpmatch = ofpmatch

    def __hash__(self):

        """To store in dict or set.
           only, ipv4.src ipv4.dst,ip.type, tos, tcp.sport, tcp.dport
        """
        l = []
        for field in OFPMatch_Wrapper.FIELDS:
            val = self.ofpmatch.get(field)
            assert val is not None
            l.append(val)
        return hash(tuple(l))

    def __eq__(self,other):
        """
            only, ipv4.src ipv4.dst,ip.type, tos, tcp.sport, tcp.dport
        """
        for field in OFPMatch_Wrapper.FIELDS:
            val1 = self.ofpmatch.get(field)
            val2 = other.ofpmatch.get(field)

            assert val1 is not None
            assert val2 is not None

            if val1 != val2:
                return False

        return True



