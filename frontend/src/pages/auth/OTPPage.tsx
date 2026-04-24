import React, { useState } from 'react';
import { useNavigate, useRouterState } from '@tanstack/react-router';
import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';
import { AlertCircle } from 'lucide-react';
import { authApi } from '../../lib/api/auth';

export function OTPPage() {
  const navigate = useNavigate();
  const routerState = useRouterState();
  const search = routerState.location.search as any;
  const email = search?.email || 'user@example.com';
  const uid = search?.uid || '';
  const type = search?.type || 'signup';
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [notice, setNotice] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length === 6) {
      setIsLoading(true);
      setError('');
      setNotice('');
      try {
        if (!uid) {
          throw new Error('Session missing. Please try again.');
        }
        const result = await authApi.verifyOTP(uid, otp, type as 'signup' | 'forgotpassword');
        
        if (type === 'forgotpassword') {
          navigate({ 
            to: '/auth/reset-password', 
            search: { reset_token: result.reset_token } 
          });
        } else {
          navigate({ to: '/app' });
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Invalid OTP or verification failed.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleResend = async () => {
    if (!email) {
      setError('Session missing. Please try again.');
      return;
    }

    setIsResending(true);
    setError('');
    setNotice('');
    try {
      await authApi.resendOTP(email, type as 'signup' | 'forgotpassword');
      setNotice('A new OTP has been sent to your email.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend OTP.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background aesthetic */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-prism-blue/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-informed/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md bg-navy-mid/80 backdrop-blur-xl border border-border rounded-xl p-8 shadow-card relative z-10">
        <div className="flex justify-center mb-8">
          <PrismLogo size={36} />
        </div>
        <h2 className="text-2xl font-heading font-bold text-center mb-2">Verify Email</h2>
        <p className="text-text-secondary text-sm text-center mb-8">We sent a 6-digit code to <span className="text-text-primary font-mono">{email}</span></p>
        
        {error && (
          <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded text-amber-500 text-xs flex items-center gap-2">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        {notice && (
          <div className="mb-4 p-3 bg-emerald-400/10 border border-emerald-400/20 rounded text-emerald-400 text-xs">
            {notice}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block font-body text-sm text-text-secondary mb-2 text-center">Enter Code</label>
            <input 
              type="text" 
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              className="w-full bg-navy border border-border rounded-lg px-4 py-3 text-text-primary text-center font-mono text-2xl tracking-[0.5em] focus:outline-none focus:border-border-bright"
              placeholder="000000"
              required
            />
          </div>
          <Button type="submit" variant="primary" size="lg" className="mt-2" disabled={otp.length !== 6 || isLoading}>
            {isLoading ? 'Verifying...' : 'Verify Code'}
          </Button>
          <Button type="button" variant="ghost" size="sm" className="mt-1" onClick={handleResend} disabled={isResending}>
            {isResending ? 'Resending...' : 'Resend OTP'}
          </Button>
          <Button type="button" variant="ghost" size="sm" className="mt-2" onClick={() => navigate({ to: '/auth/signup' })}>Back to Signup</Button>
        </form>
      </div>
    </div>
  );
}
