import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import { authApi } from '../../lib/api/auth';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const isValid = email.includes('@');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      const { uid } = await authApi.forgotPassword(email);
      navigate({ 
        to: '/auth/otp', 
        search: { email, uid, type: 'forgotpassword' } 
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process request. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background aesthetic */}
      <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-prism-blue/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-[420px] bg-navy-mid/80 backdrop-blur-xl border border-border rounded-xl p-8 shadow-card relative z-10">
        <div className="flex justify-center mb-6">
          <PrismLogo size={32} />
        </div>
        <h2 className="text-2xl font-heading font-bold text-center text-text-primary mb-2">Reset Password</h2>
        <p className="text-text-secondary text-sm text-center mb-8 font-body">Enter your email to receive a verification code</p>
        
        {error && (
          <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded text-amber-500 text-xs flex items-center gap-2">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="font-mono text-xs text-text-secondary uppercase tracking-wider">Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="trader@fund.com"
              className="bg-navy border border-border rounded-lg px-4 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
              required
            />
          </div>

          <Button type="submit" variant="primary" size="lg" className="mt-4" disabled={!isValid || isLoading}>
            {isLoading ? 'Sending Code...' : 'Send Reset Code'}
          </Button>
          
          <button 
            type="button" 
            onClick={() => navigate({ to: '/auth/login' })} 
            className="flex items-center justify-center gap-2 text-xs text-text-secondary hover:text-text-primary transition-colors mt-2"
          >
            <ArrowLeft size={12} />
            Back to Login
          </button>
        </form>
      </div>
    </div>
  );
}
