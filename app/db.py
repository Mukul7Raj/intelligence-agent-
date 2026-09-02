import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, or_
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None
_current_db_url = None


def get_engine():
    global _engine, _SessionLocal, _current_db_url
    db_url = os.getenv("DATABASE_URL", "sqlite:///./company_intelligence.db")
    if _engine is None or _current_db_url != db_url:
        if db_url.startswith("sqlite"):
            _engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(db_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine)
        _current_db_url = db_url
    return _engine


def reset_engine():
    """Reset the engine and session factory. Call this in tests to force a fresh DB connection."""
    global _engine, _SessionLocal, _current_db_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _current_db_url = None


def get_session():
    global _SessionLocal
    get_engine()  # ensure engine + _SessionLocal are initialised
    return _SessionLocal()


class CompanyResult(Base):
    __tablename__ = "company_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    row_number = Column(Integer, index=True)   # which sheet row this maps to
    company_name = Column(String, index=True)
    website = Column(String)

    # signals (enrich step)
    signal_http = Column(Text, nullable=True)       # status code, length, headers
    signal_browser = Column(Text, nullable=True)    # page title, body text via Playwright
    signal_domain = Column(Text, nullable=True)     # domain/meta signal

    # judgment (LLM step)
    fit = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    follow_up_question = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)

    synced_to_sheet = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


def save_result(data: dict) -> int:
    session = get_session()
    try:
        # Check if record already exists for this row_number or company_name
        existing = session.query(CompanyResult).filter(
            or_(
                CompanyResult.row_number == data.get("row_number"),
                CompanyResult.company_name == data.get("company_name")
            )
        ).first()

        if existing:
            for key, val in data.items():
                if hasattr(existing, key) and val is not None:
                    setattr(existing, key, val)
            existing.updated_at = datetime.utcnow()
            session.commit()
            return existing.id
        else:
            record = CompanyResult(**data)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.id
    finally:
        session.close()


def get_latest_results(limit: int = 50, fit_filter: bool = None, search: str = None):
    session = get_session()
    try:
        query = session.query(CompanyResult)
        if fit_filter is not None:
            query = query.filter(CompanyResult.fit == fit_filter)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    CompanyResult.company_name.ilike(search_pattern),
                    CompanyResult.website.ilike(search_pattern),
                    CompanyResult.reasoning.ilike(search_pattern)
                )
            )

        rows = query.order_by(CompanyResult.updated_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "row_number": r.row_number,
                "company_name": r.company_name,
                "website": r.website,
                "signal_http": r.signal_http,
                "signal_browser": r.signal_browser,
                "signal_domain": r.signal_domain,
                "fit": r.fit,
                "confidence": r.confidence,
                "follow_up_question": r.follow_up_question,
                "reasoning": r.reasoning,
                "synced_to_sheet": r.synced_to_sheet,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_result_by_id(result_id: int):
    session = get_session()
    try:
        r = session.query(CompanyResult).filter(CompanyResult.id == result_id).first()
        if not r:
            return None
        return {
            "id": r.id,
            "row_number": r.row_number,
            "company_name": r.company_name,
            "website": r.website,
            "signal_http": r.signal_http,
            "signal_browser": r.signal_browser,
            "signal_domain": r.signal_domain,
            "fit": r.fit,
            "confidence": r.confidence,
            "follow_up_question": r.follow_up_question,
            "reasoning": r.reasoning,
            "synced_to_sheet": r.synced_to_sheet,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    finally:
        session.close()


def get_processed_row_numbers():
    session = get_session()
    try:
        rows = session.query(CompanyResult.row_number).all()
        return set(r[0] for r in rows if r[0] is not None)
    finally:
        session.close()


def get_stats():
    session = get_session()
    try:
        total = session.query(CompanyResult).count()
        fits = session.query(CompanyResult).filter(CompanyResult.fit == True).count()
        no_fits = session.query(CompanyResult).filter(CompanyResult.fit == False).count()
        synced = session.query(CompanyResult).filter(CompanyResult.synced_to_sheet == True).count()
        return {
            "total_processed": total,
            "fit_count": fits,
            "no_fit_count": no_fits,
            "synced_count": synced
        }
    finally:
        session.close()


