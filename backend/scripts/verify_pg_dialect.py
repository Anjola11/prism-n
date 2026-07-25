import sys
import os
os.environ["PYTHONPATH"] = "."

from sqlalchemy.dialects import postgresql
from sqlmodel import select
from datetime import datetime, timezone, timedelta
from src.markets.models import MarketSignalSnapshot

def main():
    print("--- Verifying PostgreSQL Dialect SQL Compilation ---")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    stmt = (
        select(
            MarketSignalSnapshot.market_id,
            MarketSignalSnapshot.score,
        )
        .distinct(MarketSignalSnapshot.market_id)
        .where(
            MarketSignalSnapshot.market_id.in_(["mkt_1", "mkt_2"]),
            MarketSignalSnapshot.created_at >= cutoff,
        )
        .order_by(
            MarketSignalSnapshot.market_id,
            MarketSignalSnapshot.created_at.asc(),
        )
    )
    
    compiled = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    print("\nCompiled PostgreSQL SQL Query:")
    print(compiled)
    assert "DISTINCT ON (market_signal_snapshots.market_id)" in compiled, "Missing DISTINCT ON!"
    assert "ORDER BY market_signal_snapshots.market_id, market_signal_snapshots.created_at ASC" in compiled, "Missing ORDER BY!"
    print("\nPostgreSQL DISTINCT ON query compilation verified successfully!")

if __name__ == "__main__":
    main()
