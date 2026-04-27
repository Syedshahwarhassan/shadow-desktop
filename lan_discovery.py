import socket
import threading
import time
from zeroconf import IPVersion, ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener

class ShadowDiscovery(ServiceListener):
    def __init__(self):
        self.peers = {} # name -> (address, port)
        
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if name in self.peers:
            del self.peers[name]

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            if addresses:
                self.peers[name] = (addresses[0], info.port)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

class LANDiscovery:
    def __init__(self, device_name: str, port: int = 8765):
        self.device_name = device_name
        self.port = port
        self.type = "_shadow._tcp.local."
        self.zc = Zeroconf(ip_version=IPVersion.V4Only)
        self.listener = ShadowDiscovery()
        self.browser = None
        self.info = None

    def start(self):
        # Advertise
        local_ip = self._get_local_ip()
        self.info = ServiceInfo(
            self.type,
            f"{self.device_name}.{self.type}",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={"version": "1.0"},
            server=f"{self.device_name}.local.",
        )
        self.zc.register_service(self.info)
        
        # Discover
        self.browser = ServiceBrowser(self.zc, self.type, self.listener)

    def stop(self):
        if self.browser:
            self.browser.cancel()
        if self.info:
            self.zc.unregister_service(self.info)
        self.zc.close()

    def get_lan_peers(self) -> list:
        return list(self.listener.peers.values())

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

# Singleton instance helper
lan_discovery = None
