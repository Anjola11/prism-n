import { Moon, SunMedium } from 'lucide-react';

import { useTheme } from '../../theme/ThemeProvider';

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === 'light';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`inline-flex items-center justify-center rounded-full border border-border bg-card text-text-secondary shadow-card transition-colors hover:border-border-bright hover:text-text-primary ${
        compact ? 'h-9 w-9' : 'h-10 gap-2 px-3'
      }`}
      aria-label={isLight ? 'Switch to dark theme' : 'Switch to light theme'}
      title={isLight ? 'Switch to dark theme' : 'Switch to light theme'}
    >
      {isLight ? <Moon size={compact ? 16 : 15} /> : <SunMedium size={compact ? 16 : 15} />}
      {!compact && (
        <span className="font-mono text-[10px] uppercase tracking-[0.18em]">
          {isLight ? 'Dark' : 'Light'}
        </span>
      )}
    </button>
  );
}
