import json
import time
from collections import defaultdict, deque
from pathlib import Path

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import arp, ethernet, ether_types, icmp, ipv4, packet, tcp, udp
from ryu.ofproto import ofproto_v1_3


DEFAULT_POLICY = {
    "hosts": {
        "h1": {
            "mac": "00:00:00:00:00:01",
            "ip": "10.0.0.1",
            "role": "employee",
            "switch": 2,
            "port": 2,
        },
        "h2": {
            "mac": "00:00:00:00:00:02",
            "ip": "10.0.0.2",
            "role": "employee",
            "switch": 2,
            "port": 3,
        },
        "h3": {
            "mac": "00:00:00:00:00:03",
            "ip": "10.0.0.3",
            "role": "guest",
            "switch": 2,
            "port": 4,
        },
        "h4": {
            "mac": "00:00:00:00:00:04",
            "ip": "10.0.0.4",
            "role": "web",
            "switch": 3,
            "port": 2,
        },
        "h5": {
            "mac": "00:00:00:00:00:05",
            "ip": "10.0.0.5",
            "role": "database",
            "switch": 3,
            "port": 3,
        },
        "h6": {
            "mac": "00:00:00:00:00:06",
            "ip": "10.0.0.6",
            "role": "monitor",
            "switch": 3,
            "port": 4,
        },
    },
    "allowed_pairs": [
        ["h1", "h2"],
        ["h2", "h1"],
        ["h1", "h4"],
        ["h4", "h1"],
        ["h2", "h4"],
        ["h4", "h2"],
        ["h3", "h4"],
        ["h4", "h3"],
        ["h4", "h5"],
        ["h5", "h4"],
        ["h6", "h1"],
        ["h1", "h6"],
        ["h6", "h2"],
        ["h2", "h6"],
        ["h6", "h3"],
        ["h3", "h6"],
        ["h6", "h4"],
        ["h4", "h6"],
        ["h6", "h5"],
        ["h5", "h6"],
    ],
    "thresholds": {
        "packet_rate_window_seconds": 5,
        "packet_rate_limit": 80,
        "port_scan_window_seconds": 10,
        "port_scan_unique_ports": 12,
        "temporary_block_seconds": 30,
    },
}


class ZeroTrustController(app_manager.RyuApp):
    """Ryu OpenFlow 1.3 controller with simple Zero Trust policy enforcement."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ZeroTrustController, self).__init__(*args, **kwargs)
        self.policy = self._load_policy()
        self.hosts = self.policy["hosts"]
        self.allowed_pairs = {tuple(pair) for pair in self.policy["allowed_pairs"]}
        self.thresholds = self.policy["thresholds"]

        self.mac_to_host = {
            details["mac"].lower(): name for name, details in self.hosts.items()
        }
        self.ip_to_host = {details["ip"]: name for name, details in self.hosts.items()}

        self.mac_to_port = defaultdict(dict)
        self.host_attachments = {
            name: (details.get("switch"), details.get("port"))
            for name, details in self.hosts.items()
            if "switch" in details and "port" in details
        }
        self.edge_ports = set(self.host_attachments.values())
        self.packet_times = defaultdict(deque)
        self.probed_ports = defaultdict(deque)
        self.blocked_until = {}

        self.logger.info("Loaded %s Zero Trust hosts and %s policy pairs",
                         len(self.hosts), len(self.allowed_pairs))

    def _load_policy(self):
        policy_path = Path(__file__).with_name("zero_trust_policy.json")
        if not policy_path.exists():
            return DEFAULT_POLICY

        with policy_path.open("r", encoding="utf-8") as policy_file:
            policy = json.load(policy_file)

        merged = DEFAULT_POLICY.copy()
        merged.update(policy)
        merged["thresholds"] = DEFAULT_POLICY["thresholds"].copy()
        merged["thresholds"].update(policy.get("thresholds", {}))
        return merged

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, priority=0, match=match, actions=actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None,
                 idle_timeout=30, hard_timeout=0):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        instructions = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        kwargs = {
            "datapath": datapath,
            "priority": priority,
            "match": match,
            "instructions": instructions,
            "idle_timeout": idle_timeout,
            "hard_timeout": hard_timeout,
        }
        if buffer_id is not None and buffer_id != ofproto.OFP_NO_BUFFER:
            kwargs["buffer_id"] = buffer_id
        datapath.send_msg(parser.OFPFlowMod(**kwargs))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        src_mac = eth.src.lower()
        dst_mac = eth.dst.lower()
        src_host = self.mac_to_host.get(src_mac)

        if src_host is None:
            self._deny(datapath, msg, "unknown-source-mac", src_mac, dst_mac)
            return

        if self._is_temporarily_blocked(src_host):
            self._deny(datapath, msg, "temporarily-blocked-host", src_mac, dst_mac)
            return

        if not self._valid_ingress_location(src_host, dpid, in_port):
            self._temporary_block(src_host, "unexpected-access-port")
            self._deny(datapath, msg, "unexpected-access-port", src_mac, dst_mac)
            return

        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        arp_pkt = pkt.get_protocol(arp.arp)

        if not self._validate_source_ip(src_host, ipv4_pkt, arp_pkt):
            self._temporary_block(src_host, "source-ip-spoofing")
            self._deny(datapath, msg, "source-ip-spoofing", src_mac, dst_mac)
            return

        self.mac_to_port[dpid][src_mac] = in_port

        if self._detect_attack(src_host, pkt):
            self._deny(datapath, msg, "attack-threshold-exceeded", src_mac, dst_mac)
            return

        if arp_pkt is not None:
            self._handle_arp(datapath, msg, eth, arp_pkt, src_host)
            return

        if ipv4_pkt is not None:
            self._handle_ipv4(datapath, msg, eth, ipv4_pkt, src_host)
            return

        self._deny(datapath, msg, "unsupported-ether-type", src_mac, dst_mac)

    def _handle_arp(self, datapath, msg, eth, arp_pkt, src_host):
        dst_host = self.ip_to_host.get(arp_pkt.dst_ip)
        if dst_host is not None and not self._policy_allows(src_host, dst_host):
            self._deny(datapath, msg, "arp-policy-deny", eth.src, eth.dst,
                       src_host, dst_host)
            return

        out_port = self._known_output_port(datapath.id, eth.dst.lower())
        if out_port is None:
            out_port = datapath.ofproto.OFPP_FLOOD
        self._packet_out(datapath, msg, out_port)

    def _handle_ipv4(self, datapath, msg, eth, ipv4_pkt, src_host):
        dst_host = self.ip_to_host.get(ipv4_pkt.dst)
        if dst_host is None:
            self._deny(datapath, msg, "unknown-destination-ip", eth.src, eth.dst)
            return

        if not self._policy_allows(src_host, dst_host):
            self._install_ipv4_drop(datapath, ipv4_pkt.src, ipv4_pkt.dst)
            self._deny(datapath, msg, "ipv4-policy-deny", eth.src, eth.dst,
                       src_host, dst_host)
            return

        out_port = self._known_output_port(datapath.id, eth.dst.lower())
        if out_port is None:
            self._packet_out(datapath, msg, datapath.ofproto.OFPP_FLOOD)
            return

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        match = datapath.ofproto_parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=ipv4_pkt.src,
            ipv4_dst=ipv4_pkt.dst,
        )
        self.add_flow(datapath, priority=20, match=match, actions=actions,
                      buffer_id=msg.buffer_id)
        if msg.buffer_id == datapath.ofproto.OFP_NO_BUFFER:
            self._packet_out(datapath, msg, out_port)

        self.logger.info("ALLOW %s(%s) -> %s(%s) via switch=%s port=%s",
                         src_host, ipv4_pkt.src, dst_host, ipv4_pkt.dst,
                         datapath.id, out_port)

    def _valid_ingress_location(self, host, dpid, in_port):
        expected = self.host_attachments.get(host)
        if expected is None:
            return True
        current = (dpid, in_port)
        if current == expected:
            return True
        return current not in self.edge_ports

    def _validate_source_ip(self, host, ipv4_pkt, arp_pkt):
        expected_ip = self.hosts[host]["ip"]
        if ipv4_pkt is not None and ipv4_pkt.src != expected_ip:
            return False
        if arp_pkt is not None and arp_pkt.src_ip != expected_ip:
            return False
        return True

    def _policy_allows(self, src_host, dst_host):
        return src_host == dst_host or (src_host, dst_host) in self.allowed_pairs

    def _detect_attack(self, host, pkt):
        now = time.time()
        rate_window = self.thresholds["packet_rate_window_seconds"]
        rate_limit = self.thresholds["packet_rate_limit"]

        self._append_window(self.packet_times[host], now, rate_window)
        if len(self.packet_times[host]) > rate_limit:
            self._temporary_block(host, "packet-rate-limit")
            return True

        l4_port = self._destination_port(pkt)
        if l4_port is None:
            return False

        scan_window = self.thresholds["port_scan_window_seconds"]
        unique_limit = self.thresholds["port_scan_unique_ports"]
        self._append_window(self.probed_ports[host], (now, l4_port), scan_window)
        unique_ports = {port for _, port in self.probed_ports[host]}
        if len(unique_ports) > unique_limit:
            self._temporary_block(host, "port-scan-threshold")
            return True
        return False

    def _append_window(self, window, item, seconds):
        now = item[0] if isinstance(item, tuple) else item
        window.append(item)
        while window:
            first = window[0][0] if isinstance(window[0], tuple) else window[0]
            if now - first <= seconds:
                break
            window.popleft()

    def _destination_port(self, pkt):
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        if tcp_pkt is not None:
            return tcp_pkt.dst_port
        udp_pkt = pkt.get_protocol(udp.udp)
        if udp_pkt is not None:
            return udp_pkt.dst_port
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        if icmp_pkt is not None:
            return 0
        return None

    def _temporary_block(self, host, reason):
        until = time.time() + self.thresholds["temporary_block_seconds"]
        self.blocked_until[host] = until
        self.logger.warning("TEMPORARY BLOCK host=%s reason=%s seconds=%s",
                            host, reason,
                            self.thresholds["temporary_block_seconds"])

    def _is_temporarily_blocked(self, host):
        until = self.blocked_until.get(host)
        if until is None:
            return False
        if time.time() >= until:
            del self.blocked_until[host]
            return False
        return True

    def _known_output_port(self, dpid, dst_mac):
        if dst_mac == "ff:ff:ff:ff:ff:ff":
            return None
        return self.mac_to_port[dpid].get(dst_mac)

    def _packet_out(self, datapath, msg, out_port):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        actions = [parser.OFPActionOutput(out_port)]
        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=msg.match["in_port"],
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    def _install_ipv4_drop(self, datapath, src_ip, dst_ip):
        match = datapath.ofproto_parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=src_ip,
            ipv4_dst=dst_ip,
        )
        self.add_flow(datapath, priority=100, match=match, actions=[],
                      idle_timeout=60)

    def _deny(self, datapath, msg, reason, src_mac, dst_mac,
              src_host=None, dst_host=None):
        self.logger.warning("DENY reason=%s src_mac=%s dst_mac=%s src_host=%s "
                            "dst_host=%s switch=%s in_port=%s",
                            reason, src_mac, dst_mac, src_host, dst_host,
                            datapath.id, msg.match["in_port"])
