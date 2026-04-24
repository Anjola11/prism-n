import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';

import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';
import { adminApi } from '../../lib/api/admin';

const adminBasePath = import.meta.env.VITE_ADMIN_ROUTE_PREFIX || '/control-room';

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isValid = formData.email.includes('@') && formData.password.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;

    setIsLoading(true);
    setError('');
    try {
      await adminApi.login(formData.email, formData.password);
      navigate({ to: adminBasePath });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        setError(detail);
      } else {
        setError('Invalid admin email or password.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-void px-4">
      <div className="pointer-events-none absolute top-1/4 left-1/4 h-96 w-96 rounded-full bg-prism-blue/5 blur-[120px]" />
      <div className="pointer-events-none absolute right-1/4 bottom-1/4 h-96 w-96 rounded-full bg-informed/5 blur-[120px]" />

      <div className="relative z-10 w-full max-w-[420px] rounded-xl border border-border bg-navy-mid/80 p-8 shadow-card backdrop-blur-xl">
        <div className="mb-6 flex justify-center">
          <PrismLogo size={32} />
        </div>
        <h2 className="mb-2 text-center font-heading text-2xl font-bold text-text-primary">Admin Access</h2>
        <p className="mb-8 text-center text-sm font-body text-text-secondary">
          Restricted operations console for Prism administrators.
        </p>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-500">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="font-mono text-xs uppercase tracking-wider text-text-secondary">Admin Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="ops@prism.com"
              className="rounded-lg border border-border bg-navy px-4 py-2.5 font-mono text-sm text-text-primary transition-colors focus:border-prism-blue focus:outline-none"
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="font-mono text-xs uppercase tracking-wider text-text-secondary">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => setFormData((prev) => ({ ...prev, password: e.target.value }))}
                placeholder="********"
                className="w-full rounded-lg border border-border bg-navy py-2.5 pl-4 pr-10 font-mono text-sm text-text-primary transition-colors focus:border-prism-blue focus:outline-none"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute top-1/2 right-3 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <Button type="submit" variant="primary" size="lg" className="mt-4" disabled={!isValid || isLoading}>
            {isLoading ? 'Authenticating...' : 'Enter Admin Console'}
          </Button>
        </form>
      </div>
    </div>
  );
}
