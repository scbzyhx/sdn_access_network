import logging

from ryu.lib.ovs.vsctl import VSCtl,VSCtlContext,VSCtlQueue
from ryu.lib.ovs import vswitch_idl

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

def overrides(interface_class):
    def overrider(method):
        assert(method.__name__ in dir(interface_class))
        return method
    return overrider

class NewVSCtl(VSCtl):
    def __init__(self,remote):
        super(NewVSCtl,self).__init__(remote)

    @overrides(VSCtl)
    def _cmd_set_queue(self,ctx,command):
        """I override set queue function to just add queue, 
           instead clearing and set again
        """
#TODO: priority support
        ctx.populate_cache()
        port_name = command.args[0]
        queues = command.args[1]
        vsctl_port = ctx.find_port(port_name, True)
        vsctl_qos = vsctl_port.qos
        #get queue_id from queues dict
        results = []
        for queue in queues:
            max_rate = queue.get('max-rate', None)
            min_rate = queue.get('min-rate', None)
            queue_id = queue.get('queue-id',0)  ##remember to set queue-id
            ovsrec_queue = ctx.set_queue(
                vsctl_qos, max_rate, min_rate, queue_id)
            results.append(ovsrec_queue)
        command.result = results

    #TODO: really remove qos from database, and all of its queues
    @overrides(VSCtl)
    def _del_qos(self, ctx, port_name):
        assert port_name is not None
    
        ctx.populate_cache()
        vsctl_port = ctx.find_port(port_name, True)
        vsctl_qos = vsctl_port.qos         
        ctx.del_qos(vsctl_qos)

        ovsrec_qos = vsctl_qos.qos_cfg[0] #Row
#ovsrec_qos.delete()
#        self._notify_change(ovsrec_qos)
        for k,queue in vsctl_qos.qos_cfg[0].queues.items():
#ovsrec_queue = ovsrec_qos.queues[queue]
             queue.delete()
             self._notify_change(queue)
#LOG.debug("list queue %s",queue)
             """VSCtlContext._column_delete(ovsrec_qos, \
                                        vswitch_idl.OVSREC_QOS_COL_QUEUES,\
                                        queue)"""
        """             value = getattr(ovsrec_qos,vswitch_idl.OVSREC_QOS_COL_QUEUES)
             for k,v in value.items():
                 if v == queue:
                     del value[k]
                     setattr(ovsrec_qos,vswitch_idl.OVSREC_QOS_COL_QUEUES,value)
                     LOG.debug("queue.delete %s ",queue.delete())
            vsctl_qos.queues = None
        """

        ovsrec_qos.delete()
        self._notify_change(ovsrec_qos)

    #override _run_command to add del-queue
    @overrides(VSCtl)
    def _run_command(self, commands):
        """
        :type commands: list of VSCtlCommand
        """
        all_commands = {
            # Open vSwitch commands.
            'init': (None, self._cmd_init),
            'show': (self._pre_cmd_show, self._cmd_show),

            # Bridge commands.
            'add-br': (self._pre_add_br, self._cmd_add_br),
            'del-br': (self._pre_get_info, self._cmd_del_br),
            'list-br': (self._pre_get_info, self._cmd_list_br),

            # Port. commands
            'list-ports': (self._pre_get_info, self._cmd_list_ports),
            'add-port': (self._pre_cmd_add_port, self._cmd_add_port),
            'del-port': (self._pre_get_info, self._cmd_del_port),
            # 'add-bond':
            # 'port-to-br':

            # Interface commands.
            'list-ifaces': (self._pre_get_info, self._cmd_list_ifaces),
            # 'iface-to-br':

            # Controller commands.
            'get-controller': (self._pre_controller, self._cmd_get_controller),
            'del-controller': (self._pre_controller, self._cmd_del_controller),
            'set-controller': (self._pre_controller, self._cmd_set_controller),
            # 'get-fail-mode':
            # 'del-fail-mode':
            # 'set-fail-mode':

            # Manager commands.
            # 'get-manager':
            # 'del-manager':
            # 'set-manager':

            # Switch commands.
            # 'emer-reset':

            # Database commands.
            # 'comment':
            'get': (self._pre_cmd_get, self._cmd_get),
            # 'list':
            'find': (self._pre_cmd_find, self._cmd_find),
            'set': (self._pre_cmd_set, self._cmd_set),
            # 'add':
            'clear': (self._pre_cmd_clear, self._cmd_clear),
            # 'create':
            # 'destroy':
            # 'wait-until':

            'set-qos': (self._pre_cmd_set_qos, self._cmd_set_qos),
            'set-queue': (self._pre_cmd_set_queue, self._cmd_set_queue),
            'del-queue': (self._pre_cmd_del_queue,self._cmd_del_queue),
            'del-qos': (self._pre_get_info, self._cmd_del_qos),
            # for quantum_adapter
            'list-ifaces-verbose': (self._pre_cmd_list_ifaces_verbose,
                                    self._cmd_list_ifaces_verbose),
        }

        for command in commands:
            funcs = all_commands[command.command]
            command._prerequisite, command._run = funcs
        self._do_main(commands)
     
    #command include: port_name, and queue-id
    #port name to find qos.find queue form qos.queues whcich including id
    def _pre_cmd_del_queue(self,ctx,command):
        """pre delete queues
        """
        self._pre_get_info(ctx, command)
        schema_helper = self.schema_helper
        schema_helper.register_columns(
            vswitch_idl.OVSREC_TABLE_QUEUE,
            [vswitch_idl.OVSREC_QUEUE_COL_DSCP,
             vswitch_idl.OVSREC_QUEUE_COL_EXTERNAL_IDS,
             vswitch_idl.OVSREC_QUEUE_COL_OTHER_CONFIG])
    def _cmd_del_queue(self,ctx,command):
        """delete queue here
        """
        port_name = command.args[0]
        queue_ids = command.args[1] #list
        self._del_queue(ctx,port_name,queue_ids)

    def _get_queues(self,ovsrec_qos,queue_ids):
        ovsrec_queues = []
        for k,v in ovsrec_qos.queues.items():
            if k in queue_ids:
                ovsrec_queues.append(v)
        return ovsrec_queues
   
    """It is import, Transction check the _txn_rows, We can check this by commit method of Transaction
       But for table that is not root(I do not know what does root mean),whether it is delete is depends to ovsdb-server itself

    """
    def _notify_change(self,ovsrec_row):
        self.txn._txn_rows[ovsrec_row.uuid] = ovsrec_row
    def _del_queue(self,ctx,port_name,queue_ids):
        assert port_name is not None
        
        ctx.populate_cache()
        vsctl_port = ctx.find_port(port_name, True)
        vsctl_qos = vsctl_port.qos
        
#ovsrec_port = vsctl_port.port_cfg
        ovsrec_qos = vsctl_qos.qos_cfg[0]

        ovsrec_queues = self._get_queues(ovsrec_qos,queue_ids)
        
        value = getattr(ovsrec_qos,vswitch_idl.OVSREC_QOS_COL_QUEUES)
        for k,v in value.items():
            if v in ovsrec_queues:
                del value[k]
                tmp  = v.delete()
                self._notify_change(v)
                LOG.debug("delete queue %s",v)
                LOG.debug("after delete _change: %s",dir(v))
                LOG.debug("after delete _change: %s",v._changes)
                LOG.debug("queue.delete, But I don't know if it is OK. action's return: %s ",tmp)
        
        setattr(ovsrec_qos,vswitch_idl.OVSREC_QOS_COL_QUEUES,value)
        LOG.debug("in _del_queue, I have removed queue from qos")


