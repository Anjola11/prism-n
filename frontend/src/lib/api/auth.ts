import { api } from './client';

export const authApi = {
  getMe: async (): Promise<any> => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  renewAccessToken: async (): Promise<any> => {
    const response = await api.post('/auth/renew-access-token');
    return response.data;
  },
  logout: async (): Promise<any> => {
    const response = await api.post('/auth/logout');
    return response.data;
  },
  login: async (email: string, password: string): Promise<any> => {
    // URL encoded form data required for OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return response.data;
  },
  register: async (email: string, password: string): Promise<any> => {
    const response = await api.post('/auth/signup', { email, password });
    return response.data;
  },
  verifyOTP: async (email: string, otpCode: string): Promise<any> => {
    const response = await api.post('/auth/verify-otp', { email, otp_code: otpCode });
    return response.data;
  }
};
