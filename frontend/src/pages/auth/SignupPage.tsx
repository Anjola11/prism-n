import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { authApi } from '../../lib/api/auth';

export function SignupPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: '', password: '', confirm: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Validation state
  const passwordLengthMatch = formData.password.length >= 8;
  const passwordsMatch = formData.password === formData.confirm && formData.password.length > 0;
  const isValid = formData.email.includes('@') && passwordLengthMatch && passwordsMatch;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;

    setIsLoading(true);
    setError('');

    try {
      const user = await authApi.register(formData.email, formData.password, formData.confirm);
      navigate({ to: '/auth/otp', search: { email: formData.email, uid: user.uid } });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create account. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background aesthetic */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-prism-blue/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-informed/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-[420px] bg-navy-mid/80 backdrop-blur-xl border border-border rounded-xl p-8 shadow-card relative z-10 hidden-scrollbar">
        <div className="flex justify-center mb-6">
          <PrismLogo size={32} />
        </div>
        <h2 className="text-2xl font-heading font-bold text-center text-text-primary mb-2">Create Account</h2>
        <p className="text-text-secondary text-sm text-center mb-8 font-body">Sign up for institutional-grade intelligence</p>
        
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
              value={formData.email}
              onChange={(e) => setFormData(p => ({ ...p, email: e.target.value }))}
              placeholder="trader@fund.com"
              className="bg-navy border border-border rounded-lg px-4 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
              required
            />
          </div>
          
          <div className="flex flex-col gap-2 relative">
            <label className="font-mono text-xs text-text-secondary uppercase tracking-wider">Password</label>
            <div className="relative">
              <input 
                type={showPassword ? 'text' : 'password'} 
                value={formData.password}
                onChange={(e) => setFormData(p => ({ ...p, password: e.target.value }))}
                placeholder="••••••••"
                className="w-full bg-navy border border-border rounded-lg pl-4 pr-10 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
                required
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary">
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {formData.password.length > 0 && !passwordLengthMatch && (
              <span className="text-noise text-[10px] font-mono mt-1">Must be at least 8 characters</span>
            )}
          </div>

          <div className="flex flex-col gap-2 relative">
            <label className="font-mono text-xs text-text-secondary uppercase tracking-wider">Confirm Password</label>
            <div className="relative">
              <input 
                type={showConfirm ? 'text' : 'password'} 
                value={formData.confirm}
                onChange={(e) => setFormData(p => ({ ...p, confirm: e.target.value }))}
                placeholder="••••••••"
                className="w-full bg-navy border border-border rounded-lg pl-4 pr-10 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
                required
              />
              <button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary">
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {formData.confirm.length > 0 && !passwordsMatch && (
              <span className="text-noise text-[10px] font-mono mt-1">Passwords do not match</span>
            )}
            {passwordsMatch && (
              <span className="text-informed text-[10px] font-mono mt-1">Passwords match</span>
            )}
          </div>

          <Button type="submit" variant="primary" size="lg" className="mt-4" disabled={!isValid || isLoading}>
            {isLoading ? 'Creating Account...' : 'Sign Up'}
          </Button>
          
          <div className="flex flex-col items-center gap-4 mt-4">
            <p className="text-xs text-text-secondary font-body">
              Already have an account? <button type="button" onClick={() => navigate({ to: '/auth/login' })} className="text-prism-blue hover:underline">Log In</button>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
