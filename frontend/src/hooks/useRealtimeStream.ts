import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface StreamUpdateMessage {
  type: 'market_update' | 'signal_update';
  event_id: string;
  market_id: string;
  source?: string;
  current_probability?: number;
  previous_probability?: number;
  total_liquidity?: number;

  score?: number;
  classification?: string;
  direction?: string;
  timestamp?: string;
}

export function useRealtimeStream() {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    let isSubscribed = true;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = import.meta.env.VITE_API_BASE_URL
        ? import.meta.env.VITE_API_BASE_URL.replace(/^http/, 'ws')
        : `${protocol}//${window.location.host}`;
      
      const wsUrl = `${host.replace(/\/$/, '')}/api/v1/ws/events`;

      try {
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onmessage = (event) => {
          if (!isSubscribed) return;
          try {
            const data: StreamUpdateMessage = JSON.parse(event.data);
            if (data.event_id) {
              queryClient.setQueriesData<any>({ queryKey: ['discovery-feed'] }, (oldData: any) => {
                if (!oldData || !oldData.pages) return oldData;
                return {
                  ...oldData,
                  pages: oldData.pages.map((page: any) => ({
                    ...page,
                    items: page.items.map((item: any) => {
                      if (item.event_id !== data.event_id) return item;
                      if (data.type === 'market_update' && data.current_probability !== undefined) {
                        return {
                          ...item,
                          last_updated: data.timestamp || item.last_updated,
                          total_liquidity: data.total_liquidity ?? item.total_liquidity,
                          highest_scoring_market: item.highest_scoring_market
                            ? {
                                ...item.highest_scoring_market,
                                current_probability: data.current_probability,
                              }
                            : item.highest_scoring_market,
                        };
                      }
                      if (data.type === 'signal_update' && data.score !== undefined) {
                        return {
                          ...item,
                          last_updated: data.timestamp || item.last_updated,
                          highest_scoring_market: item.highest_scoring_market
                            ? {
                                ...item.highest_scoring_market,
                                signal: {
                                  ...item.highest_scoring_market.signal,
                                  score: data.score,
                                  classification: data.classification || item.highest_scoring_market.signal.classification,
                                  direction: data.direction || item.highest_scoring_market.signal.direction,
                                },
                              }
                            : item.highest_scoring_market,
                        };
                      }
                      return item;
                    }),
                  })),
                };
              });

              queryClient.setQueriesData<any>({ queryKey: ['tracker-feed'] }, (oldData: any) => {

                if (!oldData || !oldData.pages) return oldData;
                return {
                  ...oldData,
                  pages: oldData.pages.map((page: any) => ({
                    ...page,
                    items: page.items.map((item: any) => {
                      if (item.event_id !== data.event_id) return item;
                      if (data.type === 'market_update' && data.current_probability !== undefined) {
                        return {
                          ...item,
                          last_updated: data.timestamp || item.last_updated,
                          total_liquidity: data.total_liquidity ?? item.total_liquidity,
                          highest_scoring_market: item.highest_scoring_market
                            ? {
                                ...item.highest_scoring_market,
                                current_probability: data.current_probability,
                              }
                            : item.highest_scoring_market,
                        };
                      }
                      if (data.type === 'signal_update' && data.score !== undefined) {
                        return {
                          ...item,
                          last_updated: data.timestamp || item.last_updated,
                          highest_scoring_market: item.highest_scoring_market
                            ? {
                                ...item.highest_scoring_market,
                                signal: {
                                  ...item.highest_scoring_market.signal,
                                  score: data.score,
                                  classification: data.classification || item.highest_scoring_market.signal.classification,
                                  direction: data.direction || item.highest_scoring_market.signal.direction,
                                },
                              }
                            : item.highest_scoring_market,
                        };
                      }
                      return item;
                    }),
                  })),
                };
              });
            }
          } catch {
            // Ignore parse errors
          }
        };

        ws.onclose = () => {
          if (isSubscribed) {
            reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        if (isSubscribed) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
        }
      }
    };

    connect();

    return () => {
      isSubscribed = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [queryClient]);
}
