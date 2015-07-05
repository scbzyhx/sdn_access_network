
import logging

from ryu.lib.ovs.bridge import OVSBridge

LOG =logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

class OVSSwitch(OVSBridge):
    def __init__(self,CONF,datapath_id,ovsdb_addr,timeout=None,exception=None):
        super(OVSSwitch,self).__init__(CONF,datapath_id,ovsdb_addr,timeout,exception)
#self.logger = logging.getLogger(__name__)
#        self.logger.setLevel(logging.DEBUG)
        self.init()
        #objects are VifPort object in self.ports
        self.ports = {} #contain all ports, in which port_no is key
        portList = self.get_external_ports()
        for port in portList:
            self.ports[port.ofport] = port
            #TODO: maybe shoud a default queue
#TODO: I should add the default queue into each ports
            LOG.debug(port)
            self.set_qos(port.port_name)
        LOG.debug(self.ports)

    
