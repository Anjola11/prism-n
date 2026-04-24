import { useEffect, useRef } from 'react';

interface UseInfiniteScrollSentinelParams {
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => Promise<unknown>;
  enabled?: boolean;
  rootMargin?: string;
  threshold?: number;
}

export function useInfiniteScrollSentinel({
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  enabled = true,
  rootMargin = '200px 0px',
  threshold = 0.1,
}: UseInfiniteScrollSentinelParams) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const target = sentinelRef.current;
    if (!enabled || !target || !hasNextPage) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
          void fetchNextPage();
        }
      },
      {
        rootMargin,
        threshold,
      },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [enabled, hasNextPage, isFetchingNextPage, fetchNextPage, rootMargin, threshold]);

  return sentinelRef;
}