"""Tests for data models."""

from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_switch.core.models import (
    ProxyConfig, ProxyAuth, Profile, Server, Result, StatusInfo,
)


class TestProxyConfig(unittest.TestCase):
    """Test ProxyConfig."""

    def test_empty_config_is_disabled(self):
        config = ProxyConfig()
        self.assertFalse(config.is_enabled)
        self.assertEqual(config.primary_proxy, "")

    def test_config_with_http_is_enabled(self):
        config = ProxyConfig(http_proxy="http://proxy:8080")
        self.assertTrue(config.is_enabled)
        self.assertEqual(config.primary_proxy, "http://proxy:8080")

    def test_config_with_https_is_enabled(self):
        config = ProxyConfig(https_proxy="http://proxy:8080")
        self.assertTrue(config.is_enabled)
        self.assertEqual(config.primary_proxy, "http://proxy:8080")

    def test_merged_with_defaults(self):
        defaults = ProxyConfig(http_proxy="http://default:8080", no_proxy="localhost")
        override = ProxyConfig(http_proxy="http://custom:8080")
        merged = override.merged_with(defaults)
        self.assertEqual(merged.http_proxy, "http://custom:8080")  # Overridden
        # ProxyConfig.no_proxy defaults to "localhost,127.0.0.1,::1",
        # so the override's default takes precedence over the explicit default
        self.assertEqual(merged.no_proxy, "localhost,127.0.0.1,::1")
        self.assertEqual(merged.https_proxy, "")  # Neither set

    def test_to_dict(self):
        config = ProxyConfig(http_proxy="http://p:8080", no_proxy="localhost")
        d = config.to_dict()
        self.assertEqual(d["http_proxy"], "http://p:8080")
        self.assertEqual(d["no_proxy"], "localhost")


class TestProfile(unittest.TestCase):
    """Test Profile."""

    def test_profile_creation(self):
        config = ProxyConfig(http_proxy="http://p:8080")
        profile = Profile(name="home", config=config, description="Home proxy")
        self.assertEqual(profile.name, "home")
        self.assertTrue(profile.config.is_enabled)


class TestServer(unittest.TestCase):
    """Test Server."""

    def test_server_defaults(self):
        server = Server(name="test", host="1.2.3.4")
        self.assertEqual(server.port, 22)
        self.assertEqual(server.user, "root")
        self.assertEqual(server.auth_mode, "key")
        self.assertIn("1.2.3.4", server.label)

    def test_server_custom(self):
        server = Server(name="web", host="example.com", port=2222,
                         user="admin", auth_mode="password")
        self.assertEqual(server.port, 2222)
        self.assertEqual(server.user, "admin")


class TestResultTypes(unittest.TestCase):
    """Test Result and StatusInfo dataclasses."""

    def test_result_defaults(self):
        r = Result(success=True)
        self.assertTrue(r.success)
        self.assertEqual(r.message, "")
        self.assertEqual(r.details, "")

    def test_status_info_defaults(self):
        s = StatusInfo()
        self.assertFalse(s.enabled)
        self.assertIsNone(s.proxy)
        self.assertIsNone(s.mirror)
        self.assertIsNone(s.config_file)
        self.assertEqual(s.notes, "")


if __name__ == "__main__":
    unittest.main()
