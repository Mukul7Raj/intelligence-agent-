import os
import pytest
from app import db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db.reset_engine()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_company.db"
    db.init_db()
    yield
    db.reset_engine()


def test_db_save_and_retrieve():
    record = {
        "row_number": 2,
        "company_name": "Test Co",
        "website": "https://test.co",
        "signal_http": "status=200",
        "signal_browser": "title='Test Co'",
        "signal_domain": "domain='test.co'",
        "fit": True,
        "confidence": 0.9,
        "follow_up_question": "What is your stack?",
        "reasoning": "Fits all criteria."
    }
    rec_id = db.save_result(record)
    assert rec_id is not None

    latest = db.get_latest_results(limit=10)
    assert len(latest) == 1
    assert latest[0]["company_name"] == "Test Co"
    assert latest[0]["fit"] is True

    stats = db.get_stats()
    assert stats["total_processed"] == 1
    assert stats["fit_count"] == 1
    assert stats["no_fit_count"] == 0


def test_db_search_and_filter():
    db.save_result({
        "row_number": 2,
        "company_name": "Alpha Corp",
        "website": "https://alpha.com",
        "fit": True,
        "confidence": 0.95
    })
    db.save_result({
        "row_number": 3,
        "company_name": "Beta LLC",
        "website": "https://beta.com",
        "fit": False,
        "confidence": 0.20
    })

    fits_only = db.get_latest_results(fit_filter=True)
    assert len(fits_only) == 1
    assert fits_only[0]["company_name"] == "Alpha Corp"

    search_res = db.get_latest_results(search="Beta")
    assert len(search_res) == 1
    assert search_res[0]["company_name"] == "Beta LLC"
