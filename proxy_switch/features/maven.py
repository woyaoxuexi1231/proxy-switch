"""Maven proxy and mirror configuration via ~/.m2/settings.xml.

Manages proxy and mirror elements in settings.xml using XML parsing,
preserving any existing non-proxy/mirror content.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List

from ..core.models import Result, StatusInfo

NAME = "maven"
DESCRIPTION = "Maven build tool proxy and mirror"
CONFIG_FILES = ["~/.m2/settings.xml"]
SUPPORTS_MIRROR = True

SETTINGS = "~/.m2/settings.xml"
NS = "http://maven.apache.org/SETTINGS/1.0.0"


def _path() -> str:
    return os.path.expanduser(SETTINGS)


def _read_file(executor, path: str) -> str:
    if executor:
        r = executor.read(path)
        if r.returncode == 0:
            return r.stdout
        return ""
    try:
        with open(path) as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def _write_file(executor, path: str, content: str) -> bool:
    if executor:
        r = executor.write(path, content)
        return r.returncode == 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as f:
            f.write(content)
        return True
    except Exception:
        return False


def _parse_host_port(url: str) -> tuple:
    if not url:
        return ("", "")
    m = re.match(r'(https?|socks5?)://(.+)', url)
    if m:
        url = m.group(2)
    if ":" in url:
        host, port = url.split(":", 1)
        return (host, port.split("/")[0])
    return (url, "")


def _pretty(elem: ET.Element) -> str:
    rough = ET.tostring(elem, encoding="unicode")
    try:
        dom = minidom.parseString(rough.encode())
        return dom.toprettyxml(indent="  ")
    except Exception:
        return rough


def _make_settings_xml(host: str, port: str, non_proxy: str,
                       mirror_url: str = "", mirror_name: str = "") -> str:
    """Generate settings.xml with proxy and optional mirror."""
    mirror_block = ""
    if mirror_url:
        mirror_id = mirror_name or "proxy-switch-mirror"
        mirror_block = f"""  <mirrors>
    <mirror>
      <id>{mirror_id}</id>
      <url>{mirror_url}</url>
      <mirrorOf>central</mirrorOf>
    </mirror>
  </mirrors>
"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="{NS}"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="{NS}
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
{mirror_block}</settings>"""


def _add_proxy_to_xml(xml_content: str, host: str, port: str, non_proxy: str) -> str:
    """Add proxy-switch proxy to existing settings.xml, preserving other content."""
    try:
        root = ET.fromstring(xml_content)
        proxies = root.find(f"{{{NS}}}proxies") or root.find("proxies")
        if proxies is None:
            proxies = ET.SubElement(root, "proxies")

        for proxy in list(proxies):
            id_elem = proxy.find(f"{{{NS}}}id") or proxy.find("id")
            if id_elem is not None and id_elem.text and "proxy-switch" in id_elem.text:
                proxies.remove(proxy)

        proxy = ET.SubElement(proxies, "proxy")
        ET.SubElement(proxy, "id").text = "proxy-switch-http"
        ET.SubElement(proxy, "active").text = "true"
        ET.SubElement(proxy, "protocol").text = "http"
        ET.SubElement(proxy, "host").text = host
        ET.SubElement(proxy, "port").text = port
        ET.SubElement(proxy, "nonProxyHosts").text = non_proxy

        return _pretty(root)
    except ET.ParseError:
        return _make_settings_xml(host, port, non_proxy, "", "")


def _add_mirror_to_xml(xml_content: str, mirror_url: str, mirror_name: str = "") -> str:
    """Add a mirror entry to existing settings.xml XML string."""
    if not mirror_url:
        return xml_content
    try:
        root = ET.fromstring(xml_content)
        mirrors = root.find(f"{{{NS}}}mirrors") or root.find("mirrors")
        if mirrors is None:
            mirrors = ET.SubElement(root, "mirrors")

        for mir in list(mirrors):
            id_elem = mir.find(f"{{{NS}}}id") or mir.find("id")
            if id_elem is not None and id_elem.text and "proxy-switch" in id_elem.text:
                mirrors.remove(mir)

        mir = ET.SubElement(mirrors, "mirror")
        mid = mirror_name or "proxy-switch-mirror"
        ET.SubElement(mir, "id").text = mid
        ET.SubElement(mir, "url").text = mirror_url
        ET.SubElement(mir, "mirrorOf").text = "central"

        return _pretty(root)
    except ET.ParseError:
        return xml_content


def _remove_proxy_from_xml(xml_content: str) -> str:
    """Remove proxy-switch managed proxy and mirror elements."""
    try:
        root = ET.fromstring(xml_content)
        for proxy in list(root.findall(".//proxy")):
            id_elem = proxy.find("id")
            if id_elem is not None and id_elem.text and "proxy-switch" in id_elem.text:
                parent = root.find(".//proxies")
                if parent is not None:
                    parent.remove(proxy)
        for mir in list(root.findall(".//mirror")):
            id_elem = mir.find("id")
            if id_elem is not None and id_elem.text and "proxy-switch" in id_elem.text:
                parent = root.find(".//mirrors")
                if parent is not None:
                    parent.remove(mir)
        return _pretty(root)
    except ET.ParseError:
        return xml_content


def detect(executor=None) -> bool:
    if executor:
        return executor.run("command -v mvn").returncode == 0
    import shutil
    return shutil.which("mvn") is not None


def enable(proxy_config: Dict[str, str], executor=None) -> Result:
    """Configure Maven proxy and optional mirror in settings.xml."""
    http = proxy_config.get("http_proxy", "")
    https = proxy_config.get("https_proxy", "")
    mirror_url = proxy_config.get("mirror", "")

    proxy_url = https or http
    if not proxy_url and not mirror_url:
        return Result(success=False, message="No proxy URL or mirror URL provided")

    host, port = ("", "")
    non_proxy = "localhost|127.0.0.1"
    if proxy_url:
        host, port = _parse_host_port(proxy_url)
        if not port:
            port = "443" if https else "80"
        non_proxy = proxy_config.get("no_proxy", "").replace(",", "|") or "localhost|127.0.0.1"

    # Read existing settings
    existing = _read_file(executor, _path())

    if existing:
        # Add proxy to existing content
        if proxy_url:
            existing = _add_proxy_to_xml(existing, host, port, non_proxy)
        if mirror_url:
            existing = _add_mirror_to_xml(existing, mirror_url)
        ok = _write_file(executor, _path(), existing)
    else:
        content = _make_settings_xml(host, port, non_proxy, mirror_url)
        ok = _write_file(executor, _path(), content)

    if not ok:
        return Result(success=False, message="Failed to write settings.xml")
    return Result(success=True, message="Maven proxy configured")


def disable(executor=None) -> Result:
    """Remove proxy-switch managed proxy and mirror from settings.xml."""
    existing = _read_file(executor, _path())
    if not existing:
        return Result(success=True, message="No Maven settings to disable")

    updated = _remove_proxy_from_xml(existing)
    if updated == existing:
        return Result(success=True, message="No proxy-switch settings found")
    _write_file(executor, _path(), updated)
    return Result(success=True, message="Maven proxy disabled")


def status(executor=None) -> StatusInfo:
    """Check Maven proxy and mirror status."""
    content = _read_file(executor, _path())

    enabled = False
    proxy = None
    mirror = None

    try:
        root = ET.fromstring(content) if content else None
    except ET.ParseError:
        return StatusInfo(config_file=_path())

    if root is not None:
        for proxy_elem in root.findall(".//proxy"):
            active = proxy_elem.findtext(f"{{{NS}}}active") or proxy_elem.findtext("active", "")
            if active == "true":
                enabled = True
                host = proxy_elem.findtext(f"{{{NS}}}host") or proxy_elem.findtext("host", "")
                port = proxy_elem.findtext(f"{{{NS}}}port") or proxy_elem.findtext("port", "")
                protocol = proxy_elem.findtext(f"{{{NS}}}protocol") or proxy_elem.findtext("protocol", "http")
                if host:
                    proxy = f"{protocol}://{host}:{port}" if port else f"{protocol}://{host}"
                break

        for mir_elem in root.findall(".//mirror"):
            mid = mir_elem.findtext(f"{{{NS}}}id") or mir_elem.findtext("id", "")
            if "proxy-switch" in mid:
                mirror = mir_elem.findtext(f"{{{NS}}}url") or mir_elem.findtext("url", "")
                break

    return StatusInfo(
        enabled=enabled,
        proxy=proxy,
        mirror=mirror,
        config_file=_path(),
    )


def validate(executor=None) -> List[str]:
    issues = []
    if not detect(executor):
        issues.append("Maven (mvn) is not installed on this system")
    return issues
