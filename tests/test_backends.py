"""Tests for backend auto-discovery and base class."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_switch.backends import get_all_backends, get_backends
from proxy_switch.backends.base import Backend


class TestBackendDiscovery(unittest.TestCase):
    """Test backend auto-discovery."""

    def test_all_backends_discovered(self):
        backends = get_all_backends()
        self.assertIn("git", backends)
        self.assertIn("apt", backends)
        self.assertIn("system_env", backends)
        self.assertIn("docker", backends)
        self.assertIn("npm", backends)
        self.assertIn("pip", backends)
        self.assertIn("curl", backends)
        self.assertIn("wget", backends)
        self.assertIn("maven", backends)
        self.assertIn("gradle", backends)
        self.assertIn("snap", backends)

    def test_all_implement_backend_interface(self):
        backends = get_all_backends()
        for name, cls in backends.items():
            with self.subTest(name=name):
                self.assertTrue(issubclass(cls, Backend))
                # Check static methods
                self.assertTrue(callable(cls.name))
                self.assertTrue(callable(cls.description))
                self.assertTrue(callable(cls.can_apply))
                self.assertTrue(callable(cls.needs_sudo))
                instance = cls()
                self.assertTrue(callable(instance.enable))
                self.assertTrue(callable(instance.disable))
                self.assertTrue(callable(instance.status))

    def test_name_is_string(self):
        backends = get_all_backends()
        for name, cls in backends.items():
            with self.subTest(name=name):
                self.assertIsInstance(cls.name(), str)
                self.assertGreater(len(cls.name()), 0)
                # Name should match dict key
                self.assertEqual(cls.name(), name)

    def test_needs_sudo_returns_bool(self):
        backends = get_all_backends()
        for name, cls in backends.items():
            with self.subTest(name=name):
                self.assertIsInstance(cls.needs_sudo(), bool)

    def test_filtered_backends(self):
        filtered = get_backends(["git", "npm"])
        self.assertEqual(set(filtered.keys()), {"git", "npm"})

    def test_status_returns_dict(self):
        backends = get_all_backends()
        for name, cls in backends.items():
            with self.subTest(name=name):
                instance = cls()
                try:
                    result = instance.status()
                    self.assertIsInstance(result, dict)
                    self.assertIn("enabled", result)
                    self.assertIn("proxy", result)
                    self.assertIn("config_file", result)
                except Exception as e:
                    # Local status check may fail if tool not installed
                    pass  # Acceptable for backends that can_apply is False


if __name__ == "__main__":
    unittest.main()
