# SPDX-License-Identifier: Apache-2.0
"""Existing native runner: tolerate exited-child EPERM, never a live denial."""

import subprocess, pytest
from esae import runner


def test_signal_denial_only_tolerated_after_confirmed_child_exit(monkeypatch):
    waits = []

    class Exited:
        pid = 999999

        def wait(self, timeout):
            waits.append(timeout)
            return 0

    def denied(*args):
        raise PermissionError("owned child exiting")

    monkeypatch.setattr(runner.os, "killpg", denied)
    runner._stop_owned_process(Exited())
    assert waits == [0.25]


def test_live_child_signal_denial_still_fails_closed(monkeypatch):
    class Live:
        pid = 999999

        def wait(self, timeout):
            raise subprocess.TimeoutExpired("owned live child", timeout)

    def denied(*args):
        raise PermissionError("denied")

    monkeypatch.setattr(runner.os, "killpg", denied)
    with pytest.raises(PermissionError, match="still-active"):
        runner._stop_owned_process(Live())
