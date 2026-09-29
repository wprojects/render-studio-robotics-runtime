import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_server


class RuntimeTest(unittest.TestCase):
    def test_status_never_claims_isaac_support_on_macos(self):
        config = runtime_server.default_config()
        with patch("runtime_server.platform.system", return_value="Darwin"):
            status = runtime_server.status_payload(config)
        self.assertTrue(status["simulators"]["mujoco"]["supported"])
        self.assertFalse(status["simulators"]["isaac"]["supported"])

    def test_config_has_private_pairing_token(self):
        first = runtime_server.default_config()
        second = runtime_server.default_config()
        self.assertGreaterEqual(len(first["pairing_token"]), 24)
        self.assertNotEqual(first["pairing_token"], second["pairing_token"])

    def test_failed_tool_probe_is_not_available(self):
        completed = subprocess.CompletedProcess(["tool"], 1, stdout="", stderr="missing module")
        with patch("runtime_server.shutil.which", return_value="/usr/bin/tool"), patch("runtime_server.subprocess.run", return_value=completed):
            self.assertFalse(runtime_server.command_version("tool")["available"])


if __name__ == "__main__":
    unittest.main()
