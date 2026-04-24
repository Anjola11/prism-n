import React, { useState } from 'react';
import { useNavigate, useRouterState } from '@tanstack/react-router';
import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';
import { Eye, EyeOff, AlertCircle, CheckCircle2 } from 'lucide-react';
import { authApi } from '../../lib/api/auth';

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const routerState = useRouterState();
  const search = routerState.location.search as any;
  const resetToken = search?.reset_token || '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const isValid = password.length >= 8 && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || !resetToken) {
      if (!resetToken) setError('Reset session expired. Please start over.');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      await authApi.resetPassword(resetToken, password);
      setIsSuccess(true);
      setTimeout(() => {
        navigate({ to: '/auth/login' });
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center px-4 relative overflow-hidden">
        <div className="w-full max-w-[420px] bg-navy-mid/80 backdrop-blur-xl border border-emerald-500/20 rounded-xl p-8 shadow-card relative z-10 text-center">
          <div className="flex justify-center mb-6">
            <CheckCircle2 size={48} className="text-emerald-500" />
          </div>
          <h2 className="text-2xl font-heading font-bold text-text-primary mb-2">Password Reset</h2>
          <p className="text-text-secondary font-body mb-8">Your password has been successfully updated. Redirecting to login...</p>
          <Button variant="ghost" onClick={() => navigate({ to: '/auth/login' })}>Go to Login Now</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background aesthetic */}
      <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-informed/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-[420px] bg-navy-mid/80 backdrop-blur-xl border border-border rounded-xl p-8 shadow-card relative z-10">
        <div className="flex justify-center mb-6">
          <PrismLogo size={32} />
        </div>
        <h2 className="text-2xl font-heading font-bold text-center text-text-primary mb-2">Create New Password</h2>
        <p className="text-text-secondary text-sm text-center mb-8 font-body">Choose a secure password for your account</p>
        
        {error && (
          <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded text-amber-500 text-xs flex items-center gap-2">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2 relative">
            <label className="font-mono text-xs text-text-secondary uppercase tracking-wider">New Password</label>
            <div className="relative">
              <input 
                type={showPassword ? 'text' : 'password'} 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-navy border border-border rounded-lg pl-4 pr-10 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
                required
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary">
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <label className="font-mono text-xs text-text-secondary uppercase tracking-wider">Confirm Password</label>
            <input 
              type="password" 
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              className="bg-navy border border-border rounded-lg px-4 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
              required
            />
          </div>

          {password && confirmPassword && password !== confirmPassword && (
            <p className="text-[10px] text-amber-500 font-mono">Passwords do not match</p>
          )}

          <Button type="submit" variant="primary" size="lg" className="mt-4" disabled={!isValid || isLoading}>
            {isLoading ? 'Updating...' : 'Reset Password'}
          </Button>
        </form>
      </div>
    </div>
  );
}
