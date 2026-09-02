import pytest
from app import enrich


def test_format_url():
    assert enrich.format_url("example.com") == "https://example.com"
    assert enrich.format_url("http://example.com") == "http://example.com"
    assert enrich.format_url("  https://google.com  ") == "https://google.com"
    assert enrich.format_url("") == ""


def test_get_domain_signal():
    signal = enrich.get_domain_signal("https://lh2.ai")
    assert "domain='lh2.ai'" in signal
    assert "protocol='https'" in signal
    assert "secure_https=True" in signal


def test_get_http_signal_invalid():
    signal = enrich.get_http_signal("")
    assert "skipped" in signal
