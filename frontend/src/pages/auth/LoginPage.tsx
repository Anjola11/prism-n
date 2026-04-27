import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { authApi } from '../../lib/api/auth';

export function LoginPage() {
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
      await authApi.login(formData.email, formData.password);
      navigate({ to: '/app' });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password');
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
        <h2 className="text-2xl font-heading font-bold text-center text-text-primary mb-2">Welcome Back</h2>
        <p className="text-text-secondary text-sm text-center mb-8 font-body">Sign in to Prism Intelligence</p>
        
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
            <label className="font-mono text-xs text-text-secondary uppercase tracking-wider flex justify-between">
              <span>Password</span>
              <button 
                type="button" 
                onClick={() => navigate({ to: '/auth/forgot-password' })}
                className="cursor-pointer text-prism-blue/70 hover:text-prism-blue"
              >Forgot password?</button>
            </label>
            <div className="relative">
              <input 
                type={showPassword ? 'text' : 'password'} 
                value={formData.password}
                onChange={(e) => setFormData(p => ({ ...p, password: e.target.value }))}
                placeholder="........"
                className="w-full bg-navy border border-border rounded-lg pl-4 pr-10 py-2.5 text-text-primary text-sm font-mono focus:border-prism-blue focus:outline-none transition-colors"
                required
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary">
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <Button type="submit" variant="primary" size="lg" className="mt-4" disabled={!isValid || isLoading}>
            {isLoading ? 'Logging In...' : 'Log In'}
          </Button>
          
          <div className="flex flex-col items-center gap-4 mt-4">
            <p className="text-xs text-text-secondary font-body">
              Don't have an account? <button type="button" onClick={() => navigate({ to: '/auth/signup' })} className="text-prism-blue hover:underline">Sign Up</button>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

