import pytest
from app import judge


def test_judge_company_fallback_fit(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = judge.judge_company(
        company_name="Acme Corp",
        website="https://acme.com",
        signal_http="status=200, response_time=120ms, server='nginx'",
        signal_browser="title='Acme Corp - AI Automation' | snippet='Building smart enterprise agents.'"
    )
    assert "fit" in res
    assert "confidence" in res
    assert "follow_up_question" in res
    assert "reasoning" in res
    assert res["fit"] is True
    assert 0.0 <= res["confidence"] <= 1.0


def test_judge_company_fallback_nofit(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = judge.judge_company(
        company_name="Dead Site",
        website="https://dead-site-12345.com",
        signal_http="http_error='Connection timed out'",
        signal_browser="browser_error='Timeout 20000ms exceeded'"
    )
    assert res["fit"] is False
    assert res["confidence"] < 0.5
