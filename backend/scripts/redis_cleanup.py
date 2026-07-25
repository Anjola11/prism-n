import sys
import asyncio
import argparse
from sqlmodel import select
from src.db.main import async_session_maker
from src.db.redis import redis_client
from src.markets.models import TrackedMarket, UserTrackedEvent
from src.markets.live_state import AssetMappingLiveState

async def main():
    parser = argparse.ArgumentParser(description="Clean up orphaned/stale keys in Redis.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Apply 24-hour TTL to orphaned keys instead of dry-running."
    )
    args = parser.parse_args()

    live_mode = args.live
    print(f"Running Redis cleanup script. Mode: {'LIVE (Applying 24h TTL)' if live_mode else 'DRY-RUN'}")

    # 1. Fetch tracked events and markets from PostgreSQL database
    async with async_session_maker() as session:
        # Event IDs currently tracked (either user-tracked or system-tracked)
        tracked_event_ids_res = await session.exec(
            select(TrackedMarket.event_id).where(TrackedMarket.tracking_enabled == True)
        )
        tracked_event_ids = set(tracked_event_ids_res.all())

        user_tracked_event_ids_res = await session.exec(
            select(UserTrackedEvent.event_id).where(UserTrackedEvent.tracking_enabled == True)
        )
        tracked_event_ids.update(user_tracked_event_ids_res.all())

        # Market IDs currently tracked
        tracked_market_ids_res = await session.exec(
            select(TrackedMarket.market_id).where(TrackedMarket.tracking_enabled == True)
        )
        tracked_market_ids = set(tracked_market_ids_res.all())

    print(f"Loaded {len(tracked_event_ids)} tracked event IDs and {len(tracked_market_ids)} tracked market IDs from database.")

    # 2. Scan Redis keys
    # Keys we want to look at: prism:event:*, prism:market:*, prism:signal:*, prism:persistence:*, prism:subscription:*, prism:assetmap:*
    patterns = [
        "prism:event:*",
        "prism:market:*",
        "prism:signal:*",
        "prism:persistence:*",
        "prism:subscription:*",
        "prism:assetmap:*"
    ]

    orphaned_keys = []
    
    for pattern in patterns:
        cursor = 0
        keys_found = []
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=1000)
            keys_found.extend(keys)
            if cursor == 0:
                break
        
        print(f"Pattern '{pattern}': scanned {len(keys_found)} keys in Redis.")

        for key in keys_found:
            is_orphaned = False
            parts = key.split(":")
            
            # Pattern types and index analysis:
            # 1. prism:event:{source}:{currency}:{event_id} -> length 5, event_id at parts[4]
            # 2. prism:market:{source}:{currency}:{market_id} -> length 5, market_id at parts[4]
            # 3. prism:signal:{source}:{currency}:{market_id} -> length 5, market_id at parts[4]
            # 4. prism:persistence:{source}:{currency}:{market_id} -> length 5, market_id at parts[4]
            # 5. prism:subscription:{source}:{channel}:{event_id}[:{market_id}] -> length 5 or 6, event_id at parts[4]
            # 6. prism:assetmap:{source}:{asset_id} -> length 4, check asset binding mapping
            
            if key.startswith("prism:event:"):
                if len(parts) >= 5:
                    event_id = parts[4]
                    if event_id not in tracked_event_ids:
                        is_orphaned = True

            elif key.startswith("prism:market:") or key.startswith("prism:signal:") or key.startswith("prism:persistence:"):
                if len(parts) >= 5:
                    market_id = parts[4]
                    if market_id not in tracked_market_ids:
                        is_orphaned = True

            elif key.startswith("prism:subscription:"):
                if len(parts) >= 5:
                    event_id = parts[4]
                    if event_id not in tracked_event_ids:
                        is_orphaned = True

            elif key.startswith("prism:assetmap:"):
                # We need to retrieve the mapping payload to know the market_id
                payload = await redis_client.get(key)
                if payload:
                    try:
                        mapping = AssetMappingLiveState.model_validate_json(payload)
                        if mapping.market_id not in tracked_market_ids:
                            is_orphaned = True
                    except Exception:
                        # If invalid payload, mark it as orphaned so it gets cleanup TTL
                        is_orphaned = True
                else:
                    is_orphaned = True

            if is_orphaned:
                orphaned_keys.append(key)

    print(f"Total orphaned keys matched: {len(orphaned_keys)}")
    
    if orphaned_keys:
        sample_size = min(10, len(orphaned_keys))
        print(f"Sample of orphaned keys ({sample_size} of {len(orphaned_keys)}):")
        for key in orphaned_keys[:sample_size]:
            print(f" - {key}")

        if live_mode:
            print("Applying 24-hour TTL (86400 seconds) to all matched orphaned keys...")
            for idx, key in enumerate(orphaned_keys):
                await redis_client.expire(key, 86400)
                if (idx + 1) % 100 == 0:
                    print(f"Processed {idx + 1}/{len(orphaned_keys)} keys...")
            print("Finished applying TTLs.")
        else:
            print("Dry-run complete. No writes performed. Run with --live to apply TTLs.")
    else:
        print("No orphaned keys found.")

    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())
