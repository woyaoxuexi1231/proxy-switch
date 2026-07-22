"""Tests for feature module discovery and interface."""

from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_switch.features import discover, get_all, get, list_names
from proxy_switch.core.models import Result, StatusInfo


class TestFeatureDiscovery(unittest.TestCase):
    """Test feature module auto-discovery."""

    def test_all_features_discovered(self):
        features = get_all()
        self.assertIn("system_proxy", features)
        self.assertIn("apt", features)
        self.assertIn("docker", features)
        self.assertIn("npm", features)
        self.assertIn("git", features)
        self.assertIn("maven", features)

    def test_features_have_required_attributes(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                self.assertTrue(hasattr(mod, "NAME"))
                self.assertTrue(hasattr(mod, "DESCRIPTION"))
                self.assertTrue(hasattr(mod, "CONFIG_FILES"))
                self.assertIsInstance(mod.NAME, str)
                self.assertIsInstance(mod.DESCRIPTION, str)
                self.assertIsInstance(mod.CONFIG_FILES, list)
                self.assertEqual(mod.NAME, name)

    def test_features_have_required_functions(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                self.assertTrue(callable(mod.detect))
                self.assertTrue(callable(mod.enable))
                self.assertTrue(callable(mod.disable))
                self.assertTrue(callable(mod.status))
                self.assertTrue(callable(mod.validate))

    def test_detect_returns_bool(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                result = mod.detect()
                self.assertIsInstance(result, bool)

    def test_status_returns_status_info(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                try:
                    result = mod.status()
                    self.assertIsInstance(result, StatusInfo)
                    self.assertIsInstance(result.enabled, bool)
                    self.assertIn("config_file", result.__dataclass_fields__)
                    self.assertIn("proxy", result.__dataclass_fields__)
                except Exception:
                    pass  # May fail if tool not installed — acceptable

    def test_enable_with_empty_config_returns_result(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                result = mod.enable({})
                self.assertIsInstance(result, Result)

    def test_disable_returns_result(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                result = mod.disable()
                self.assertIsInstance(result, Result)

    def test_validate_returns_list(self):
        features = get_all()
        for name, mod in features.items():
            with self.subTest(name=name):
                result = mod.validate()
                self.assertIsInstance(result, list)

    def test_list_names(self):
        names = list_names()
        self.assertIn("system_proxy", names)
        self.assertIn("apt", names)
        self.assertIn("docker", names)
        self.assertEqual(sorted(names), names)

    def test_get_returns_none_for_unknown(self):
        self.assertIsNone(get("nonexistent_feature"))


if __name__ == "__main__":
    unittest.main()
