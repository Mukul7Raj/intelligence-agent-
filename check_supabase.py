import os
from dotenv import load_dotenv
load_dotenv()
from app import db

print("=" * 60)
print("             SUPABASE DATABASE STATUS")
print("=" * 60)

stats = db.get_stats()
print(f"Total Processed in Supabase: {stats['total_processed']}")
print(f"Fit Matches:                 {stats['fit_count']}")
print(f"No-Fit Disqualified:         {stats['no_fit_count']}")
print(f"Synced to Google Sheet:      {stats['synced_count']}")
print("-" * 60)
print("Latest Records stored in Supabase Postgres:")
print("-" * 60)

results = db.get_latest_results(limit=10)
for r in results:
    verdict_tag = "FIT   " if r["fit"] else "NO-FIT"
    conf_pct = int(r["confidence"] * 100)
    print(f"[{verdict_tag}] {r['company_name']:<16} ({conf_pct}% conf) -> {r['website']}")
    print(f"   Reasoning: {r['reasoning'][:90]}...")
    print(f"   Question:  {r['follow_up_question'][:90]}...")
    print()

print("=" * 60)
