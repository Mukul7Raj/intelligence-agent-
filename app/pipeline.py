import time
import logging
import threading
from app import sheets, enrich, judge, db

logger = logging.getLogger("pipeline")
_pipeline_lock = threading.Lock()


def run_pipeline(only_unprocessed: bool = False) -> dict:
    """
    Runs the full company intelligence pipeline:
    1. Source: Reads company targets from Google Sheet.
    2. Enrich: Pulls independent signals (HTTP, Playwright Browser, Domain).
    3. Judge: Uses Gemini LLM for structured verdict.
    4. Persist: Saves evidence & verdict into SQL database.
    5. Sync Back: Writes verdict back into Google Sheet.
    """
    if not _pipeline_lock.acquire(blocking=False):
        logger.warning("Pipeline run already in progress. Skipping duplicate execution.")
        return {
            "status": "already_running",
            "processed_count": 0,
            "results": []
        }

    start_time = time.time()
    logger.info(f"Pipeline run started (only_unprocessed={only_unprocessed})")

    try:
        companies = sheets.read_companies(only_unprocessed=only_unprocessed)
        results = []
        errors = []

        # If Google Sheet returned no rows (or not configured), check DB for unprocessed rows if any
        if not companies and not only_unprocessed:
            logger.info("No companies returned from Google Sheet. Pipeline completed.")

        for company in companies:
            c_name = company.get("company_name", "Unknown")
            c_url = company.get("website", "")
            row_num = company.get("row_number", 0)

            logger.info(f"Processing row {row_num}: '{c_name}' ({c_url})")

            try:
                # Step 2: Enrich signals
                signals = enrich.enrich_company(c_url)

                # Step 3: Judge with LLM
                verdict = judge.judge_company(
                    company_name=c_name,
                    website=c_url,
                    signal_http=signals.get("signal_http", ""),
                    signal_browser=signals.get("signal_browser", ""),
                    signal_domain=signals.get("signal_domain", "")
                )

                # Step 4: Persist to DB
                record = {
                    "row_number": row_num,
                    "company_name": c_name,
                    "website": c_url,
                    "signal_http": signals.get("signal_http"),
                    "signal_browser": signals.get("signal_browser"),
                    "signal_domain": signals.get("signal_domain"),
                    "fit": verdict.get("fit", False),
                    "confidence": verdict.get("confidence", 0.0),
                    "follow_up_question": verdict.get("follow_up_question", ""),
                    "reasoning": verdict.get("reasoning", ""),
                    "synced_to_sheet": False
                }

                db_id = db.save_result(record)
                record["id"] = db_id

                # Step 5: Sync back to Google Sheet
                synced = sheets.write_verdict(
                    row_number=row_num,
                    fit=record["fit"],
                    confidence=record["confidence"],
                    follow_up_question=record["follow_up_question"],
                    reasoning=record["reasoning"]
                )

                if synced:
                    db.save_result({"row_number": row_num, "synced_to_sheet": True})
                    record["synced_to_sheet"] = True

                results.append(record)
                logger.info(f"Completed '{c_name}': fit={record['fit']}, confidence={record['confidence']}")

            except Exception as e:
                err_msg = f"Failed to process '{c_name}': {type(e).__name__}: {str(e)}"
                logger.error(err_msg)
                errors.append({"company_name": c_name, "error": err_msg})

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Pipeline run completed in {elapsed}s. Processed {len(results)} companies.")

        return {
            "status": "completed",
            "duration_seconds": elapsed,
            "processed_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }

    finally:
        _pipeline_lock.release()

