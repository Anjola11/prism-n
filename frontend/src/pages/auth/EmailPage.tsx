import React, { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../../components/brand/PrismLogo';
import { Button } from '../../components/ui/Button';

export function EmailPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      navigate({ to: '/auth/otp', search: { email, uid: '' } });
    }
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-navy-mid border border-border rounded-xl p-8 shadow-card">
        <div className="flex justify-center mb-8">
          <PrismLogo size={36} />
        </div>
        <h2 className="text-2xl font-heading font-bold text-center mb-2">Access Prism</h2>
        <p className="text-text-secondary text-sm text-center mb-8">Enter your email to receive a one-time passcode</p>
        
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block font-body text-sm text-text-secondary mb-2">Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-navy border border-border rounded-lg px-4 py-2.5 text-text-primary focus:outline-none focus:border-border-bright"
              placeholder="you@example.com"
              required
            />
          </div>
          <Button type="submit" variant="primary" size="lg" className="mt-2">Send OTP</Button>
        </form>
      </div>
    </div>
  );
}
