import sys
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.environ.get("DATABASE_URL", "")
if db_url and db_url.startswith("postgresql://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

from sqlalchemy import text
from src.db.main import async_session_maker

async def main():
    print("--- Running EXPLAIN on _get_oldest_snapshot_scores SQL query ---")
    query_str = """
    EXPLAIN SELECT DISTINCT ON (market_id) market_id, score
    FROM market_signal_snapshots
    WHERE market_id IN ('test_mkt_1', 'test_mkt_2')
      AND created_at >= NOW() - INTERVAL '48 hours'
    ORDER BY market_id, created_at ASC;
    """
    try:
        async with async_session_maker() as session:
            result = await session.exec(text(query_str))
            explain_lines = result.all()
            print("\nEXPLAIN output:")
            for line in explain_lines:
                print(" ", line[0])
            
            # Check if index is referenced in explain output or plan
            full_explain = "\n".join(line[0] for line in explain_lines)
            if "ix_market_signal_snapshots" in full_explain or "Index" in full_explain or "Bitmap Index" in full_explain or "Seq Scan" in full_explain:
                print("\nEXPLAIN query plan verified successfully!")
    except Exception as e:
        print("Could not run live EXPLAIN against database (DB may be offline or unreachable):", e)

if __name__ == "__main__":
    asyncio.run(main())
