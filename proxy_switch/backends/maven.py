"""Maven proxy backend.

Manages ~/.m2/settings.xml with XML parsing to preserve existing content.
"""

from typing import Dict, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import re

from .base import Backend


class MavenBackend(Backend):

    SETTINGS = "~/.m2/settings.xml"

    @staticmethod
    def name() -> str:
        return "maven"

    @staticmethod
    def description() -> str:
        return "Maven build tool proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v mvn").returncode == 0
        import shutil
        return shutil.which("mvn") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _path(self) -> str:
        return os.path.expanduser(self.SETTINGS)

    def _parse_host_port(self, url: str) -> tuple:
        """Extract host and port from a proxy URL."""
        if not url:
            return ("", "")
        # Strip protocol
        m = re.match(r'(https?|socks5?)://(.+)', url)
        if m:
            url = m.group(2)
        if ":" in url:
            host, port = url.split(":", 1)
            return (host, port.split("/")[0])  # Remove trailing path
        return (url, "")

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")
        no_proxy = proxy_config.get("no_proxy", "")

        # Determine which proxy to use (prefer https)
        proxy_url = https or http
        if not proxy_url:
            return {"success": False, "message": "No proxy URL provided", "details": ""}

        host, port = self._parse_host_port(proxy_url)
        if not port:
            port = "443" if https else "80"

        # Build nonProxyHosts
        non_proxy = no_proxy.replace(",", "|") if no_proxy else "localhost|127.0.0.1"

        if executor:
            # Must handle XML via temp file on remote
            import tempfile
            content = self._generate_xml(host, port, non_proxy, proxy_url)
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as tf:
                tf.write(content)
                tf.flush()
                temp_path = tf.name
            # Copy to remote
            r = executor.upload(temp_path, self._path())
            os.unlink(temp_path)
            return {"success": r.returncode == 0,
                    "message": "Maven proxy configured" if r.returncode == 0 else "Upload failed",
                    "details": r.stderr or ""}
        else:
            try:
                self._write_settings(host, port, non_proxy, proxy_url)
                return {"success": True, "message": "Maven proxy configured", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def disable(self, executor=None) -> Dict:
        if executor:
            # Read remote settings.xml, remove proxy, write back
            r = executor.read(self._path())
            if r.returncode != 0:
                return {"success": True, "message": "No Maven settings to disable", "details": ""}
            content = self._remove_proxy_from_xml(r.stdout)
            executor.write(self._path(), content)
            return {"success": True, "message": "Maven proxy disabled", "details": ""}
        else:
            try:
                path = self._path()
                if not os.path.exists(path):
                    return {"success": True, "message": "No Maven settings to disable", "details": ""}
                content = self._remove_proxy_from_xml(open(path).read())
                with open(path, "w") as f:
                    f.write(content)
                return {"success": True, "message": "Maven proxy disabled", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.read(self._path())
            if r.returncode != 0:
                return {"enabled": False, "proxy": None,
                        "config_file": self._path(), "notes": ""}
            content = r.stdout
        else:
            try:
                with open(self._path()) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = False
        proxy = None
        try:
            root = ET.fromstring(content)
            for proxy_elem in root.findall(".//proxy"):
                active = proxy_elem.findtext("active", "")
                if active == "true":
                    enabled = True
                    host = proxy_elem.findtext("host", "")
                    port = proxy_elem.findtext("port", "")
                    protocol = proxy_elem.findtext("protocol", "http")
                    if host:
                        proxy = f"{protocol}://{host}:{port}" if port else f"{protocol}://{host}"
                    break
        except ET.ParseError:
            pass

        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self._path(),
            "notes": "",
        }

    def _generate_xml(self, host: str, port: str, non_proxy: str, proxy_url: str) -> str:
        """Generate minimal settings.xml with proxy config."""
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              http://maven.apache.org/xsd/settings-1.0.0.xsd">
  <proxies>
    <proxy>
      <id>proxy-switch-http</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>{host}</host>
      <port>{port}</port>
      <nonProxyHosts>{non_proxy}</nonProxyHosts>
    </proxy>
  </proxies>
</settings>'''
        return xml

    def _write_settings(self, host: str, port: str, non_proxy: str, proxy_url: str) -> None:
        """Write settings.xml, preserving existing content if possible."""
        path = self._path()
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if os.path.exists(path):
            content = open(path).read()
            content = self._add_proxy_to_xml(content, host, port, non_proxy)
            with open(path, "w") as f:
                f.write(content)
        else:
            with open(path, "w") as f:
                f.write(self._generate_xml(host, port, non_proxy, proxy_url))

    def _add_proxy_to_xml(self, xml_content: str, host: str, port: str,
                          non_proxy: str) -> str:
        """Add proxy element to existing settings.xml."""
        try:
            root = ET.fromstring(xml_content)
            ns = {'ns': 'http://maven.apache.org/SETTINGS/1.0.0'}

            # Find or create proxies element
            proxies = root.find('ns:proxies', ns)
            if proxies is None:
                proxies = root.find('proxies')
            if proxies is None:
                proxies = ET.SubElement(root, 'proxies')

            # Remove existing proxy-switch proxies
            for proxy in list(proxies):
                id_elem = proxy.find('ns:id', ns) or proxy.find('id')
                if id_elem is not None and id_elem.text and 'proxy-switch' in id_elem.text:
                    proxies.remove(proxy)

            # Add new proxy
            proxy = ET.SubElement(proxies, 'proxy')
            ET.SubElement(proxy, 'id').text = 'proxy-switch-http'
            ET.SubElement(proxy, 'active').text = 'true'
            ET.SubElement(proxy, 'protocol').text = 'http'
            ET.SubElement(proxy, 'host').text = host
            ET.SubElement(proxy, 'port').text = port
            ET.SubElement(proxy, 'nonProxyHosts').text = non_proxy

            return self._pretty_xml(root)
        except ET.ParseError:
            # If XML is messed up, regenerate
            return self._generate_xml(host, port, non_proxy, "")

    def _remove_proxy_from_xml(self, xml_content: str) -> str:
        """Remove proxy-switch managed proxies from settings.xml."""
        try:
            root = ET.fromstring(xml_content)
            for proxy in list(root.findall(".//proxy")):
                id_elem = proxy.find("id")
                if id_elem is not None and id_elem.text and 'proxy-switch' in id_elem.text:
                    parent = root.find(".//proxies")
                    if parent is not None:
                        parent.remove(proxy)
            return self._pretty_xml(root)
        except ET.ParseError:
            return xml_content

    def _pretty_xml(self, elem) -> str:
        """Return pretty-printed XML string."""
        rough = ET.tostring(elem, encoding="unicode")
        try:
            dom = minidom.parseString(rough.encode())
            return dom.toprettyxml(indent="  ")
        except Exception:
            return rough
