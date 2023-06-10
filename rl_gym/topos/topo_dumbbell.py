from rl_gym.topos.topo_base import BaseTopo
import rl_gym.rl_evaluator.rl_utils as rl_utils
import logging
log = logging.getLogger(__name__)

DEFAULT_CONF = {
    "num_hosts": 6,   # Host number in topology
    "traffic_files": ["incast_2", "incast_4", "incast_8", "incast_16",
                      "incast_32", "incast_64", "incast_128", "incast_256",
                      "incast_512", "incast_1024"],
}


class DumbbellTopo(BaseTopo):
    '''
     Dumbbell Topology with 3-by-3 hosts
    '''
    def __init__(self, conf={}):
        self.conf = DEFAULT_CONF
        self.conf.update(conf)
        BaseTopo.__init__(self, self.conf)
        self.name = "dumbbell"

        # Topo initialization
        self.switch_w = None
        self.switch_e = None
        self.hosts_w = []
        self.hosts_e = []

    # Build entire nodes for topo
    def build_nodes(self):
        self._build_switches()
        self._build_hosts(self.conf["num_hosts"])

    # Build switches/routers
    def _build_switches(self):
        # Define two swtiches s1, s2 in Dumbbell Topo
        sw_w_name = self.switch_id + "s1"
        sw_e_name = self.switch_id + "s2"
        self.switch_w = self.addSwitch(name=sw_w_name)
        self.switch_e = self.addSwitch(name=sw_e_name)

    # Build hosts
    def _build_hosts(self, num):
        """
            Averagely create hosts.
        """
        for i in range(num):
            name = "h" + str(i)
            c_class = i / 510
            d_class = i % 510
            if (i % 2) == 1:
                ip = "10.1.%d.%d" % (c_class, (d_class + 1) / 2)
                host = self.addHost(name=name, cpu=1.0 / num, ip=ip)
                self.hosts_w.append(host)
            else:
                ip = "10.2.%d.%d" % (c_class, (d_class + 2) / 2)
                host = self.addHost(name=name, cpu=1.0 / num, ip=ip)
                self.hosts_e.append(host)
            log.info("Host %s IP %s" % (host, ip))
            self.host_ips[host] = ip

        self.host_list = self.hosts_w + self.hosts_e

    # Build links
    def build_links(self):
        """
                Add links between switch and hosts.
        """
        self.addLink(self.switch_w, self.switch_e)
        for host in self.hosts_w:
            self.addLink(self.switch_w, host)
        for host in self.hosts_e:
            self.addLink(self.switch_e, host)

    def _install_proactive(self):
        """
                Install proactive flow entries for the switch.
        """
        protocols = ["ip", "arp"]
        for prot in protocols:
            # West Switch
            ovs_flow_cmd = "ovs-ofctl add-flow %s " % self.switch_w
            ovs_flow_cmd += "-O OpenFlow13 "
            for index, host in enumerate(self.hosts_w):
                port = index + 2
                host_ip = self.host_ips[host]
                cmd = ovs_flow_cmd
                cmd += "table=0,idle_timeout=0,"
                cmd += "hard_timeout=0,priority=10,"
                cmd += "%s," % prot
                cmd += "nw_dst=%s," % host_ip
                cmd += "actions=output:%d" % port
                rl_utils.exec_process(cmd)
            cmd = ovs_flow_cmd
            cmd += "table=0,idle_timeout=0,hard_timeout=0,priority=10,"
            cmd += "%s," % prot
            cmd += "nw_dst=10.2.0.0/16,actions=output:1"
            rl_utils.exec_process(cmd)

            # East Switch
            ovs_flow_cmd = "ovs-ofctl add-flow %s " % self.switch_e
            ovs_flow_cmd += "-O OpenFlow13 "
            for index, host in enumerate(self.hosts_e):
                port = index + 2
                host_ip = self.host_ips[host]
                cmd = ovs_flow_cmd
                cmd += "table=0,idle_timeout=0,"
                cmd += "hard_timeout=0,priority=10,"
                cmd += "%s," % prot
                cmd += "nw_dst=%s," % host_ip
                cmd += "actions=output:%d" % port
                rl_utils.exec_process(cmd)
            cmd = ovs_flow_cmd
            cmd += "table=0,idle_timeout=0,hard_timeout=0,priority=10,"
            cmd += "%s," % prot
            cmd += "nw_dst=10.1.0.0/16,actions=output:1"
            rl_utils.exec_process(cmd)

    def _config_topo(self):
        # Set hosts IP addresses.
        self._install_proactive()
