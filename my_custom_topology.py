from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo


class CustomTreeTopo(Topo):
    """Three-switch SDN topology with deterministic Zero Trust host identities."""

    def build(self):
        switch1 = self.addSwitch(
            "s1", dpid="0000000000000001", protocols="OpenFlow13"
        )
        switch2 = self.addSwitch(
            "s2", dpid="0000000000000002", protocols="OpenFlow13"
        )
        switch3 = self.addSwitch(
            "s3", dpid="0000000000000003", protocols="OpenFlow13"
        )

        hosts = {
            "h1": ("10.0.0.1/24", "00:00:00:00:00:01"),
            "h2": ("10.0.0.2/24", "00:00:00:00:00:02"),
            "h3": ("10.0.0.3/24", "00:00:00:00:00:03"),
            "h4": ("10.0.0.4/24", "00:00:00:00:00:04"),
            "h5": ("10.0.0.5/24", "00:00:00:00:00:05"),
            "h6": ("10.0.0.6/24", "00:00:00:00:00:06"),
        }

        host_nodes = {
            name: self.addHost(name, ip=ip_address, mac=mac_address)
            for name, (ip_address, mac_address) in hosts.items()
        }

        self.addLink(switch1, switch2, cls=TCLink, bw=100)
        self.addLink(switch1, switch3, cls=TCLink, bw=100)

        self.addLink(switch2, host_nodes["h1"], cls=TCLink, bw=50)
        self.addLink(switch2, host_nodes["h2"], cls=TCLink, bw=50)
        self.addLink(switch2, host_nodes["h3"], cls=TCLink, bw=50)
        self.addLink(switch3, host_nodes["h4"], cls=TCLink, bw=50)
        self.addLink(switch3, host_nodes["h5"], cls=TCLink, bw=50)
        self.addLink(switch3, host_nodes["h6"], cls=TCLink, bw=50)


topos = {"custom_tree_topo": CustomTreeTopo}


def run():
    topo = CustomTreeTopo()
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(
            name, ip="127.0.0.1", port=6653
        ),
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=False,
        build=True,
    )

    try:
        net.start()
        print("\nZero Trust SDN topology is running.")
        print("Use commands such as: h1 ping -c 3 h4, h3 ping -c 3 h5")
        CLI(net)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
