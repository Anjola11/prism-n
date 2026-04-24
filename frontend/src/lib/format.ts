export function formatRelative(value: string | null): string {
  if (!value) return 'Not synced yet';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  const diffSeconds = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  return `${Math.floor(diffHours / 24)}d ago`;
}

export function formatCurrencyCompact(currency: string, amount: number | null | undefined): string {
  const value = amount ?? 0;
  const normalizedCurrency = currency.toUpperCase();

  if (Math.abs(value) >= 1_000_000_000) {
    return `${normalizedCurrency} ${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${normalizedCurrency} ${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${normalizedCurrency} ${(value / 1_000).toFixed(1)}K`;
  }
  if (Number.isInteger(value)) {
    return `${normalizedCurrency} ${value.toLocaleString()}`;
  }
  return `${normalizedCurrency} ${value.toFixed(2)}`;
}
