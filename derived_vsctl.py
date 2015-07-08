
from ryu.lib.ovs import vsctl

class DerivedVSCtl(vsctl.VSCtl):
    def __init__(self,remote):
        super(DerivedVSCtl,self).__init__(remote)
#def _cmd_set_queue(self,ctxt,commands):
    def _cmd_set_queue(self, ctx, command):
        ctx.populate_cache()
        port_name = command.args[0]
        queues = command.args[1]
        vsctl_port = ctx.find_port(port_name, True)
        vsctl_qos = vsctl_port.qos
        exists_queues = vsctl_qos.queues
        exists_queues_id = []
        for exist_queue in exists_queues:
            exists_queues_id.append(exist_queue.queue_id)
        queue_id = 0
        results = []
        
        for queue in queues:

            #keep queue_id different
            for queue_id in exists_queues_id:
                queue_id += 1

            max_rate = queue.get('max-rate', None)
            min_rate = queue.get('min-rate', None)

            ovsrec_queue = ctx.set_queue(
                vsctl_qos, max_rate, min_rate, queue_id)

            results.append(ovsrec_queue)
            queue_id += 1

        command.result = results

