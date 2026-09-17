"""Peak memory retains platform units and fails visibly when unavailable."""
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pdf_extraction import platform_memory


@pytest.mark.parametrize("platform,raw", [("darwin", 7 * 1024 * 1024), ("linux", 7 * 1024)])
def test_unix_peak_units(platform, raw):
    resource = SimpleNamespace(RUSAGE_SELF=0, getrusage=lambda _: SimpleNamespace(ru_maxrss=raw))
    with patch.object(sys, "platform", platform), patch.dict(sys.modules, resource=resource):
        assert platform_memory.peak_rss_mb() == 7


def test_windows_peak_units():
    with patch.object(sys, "platform", "win32"), patch.object(platform_memory, "_windows_peak_rss", return_value=7 * 1024 * 1024):
        assert platform_memory.peak_rss_mb() == 7


def test_windows_query_failure_is_not_zero_memory():
    with patch.object(sys, "platform", "win32"), patch.object(platform_memory, "_windows_peak_rss", return_value=None):
        with pytest.raises(OSError, match="Cannot query process memory"):
            platform_memory.peak_rss_mb()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native process counters")
def test_native_windows_peak_is_positive():
    assert platform_memory.peak_rss_mb() > 0
