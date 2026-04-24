import { api } from './client';
import type { ApiResponse, AuthUserApi } from './types';

const unwrap = <T>(response: { data: ApiResponse<T> }): T => response.data.data;

export const authApi = {
  getMe: async (): Promise<AuthUserApi> => {
    const response = await api.get('/auth/me');
    return unwrap(response);
  },
  renewAccessToken: async (): Promise<Record<string, never>> => {
    const response = await api.post('/auth/renew-access-token');
    return unwrap(response);
  },
  logout: async (): Promise<Record<string, never>> => {
    const response = await api.post('/auth/logout');
    return unwrap(response);
  },
  login: async (email: string, password: string): Promise<AuthUserApi> => {
    const response = await api.post('/auth/login', { email, password });
    return unwrap(response);
  },
  register: async (
    email: string,
    password: string,
    confirmPassword: string,
  ): Promise<AuthUserApi> => {
    const response = await api.post('/auth/signup', {
      email,
      password,
      confirm_password: confirmPassword,
    });
    return unwrap(response);
  },
  verifyOTP: async (uid: string, otpCode: string, otpType: 'signup' | 'forgotpassword' = 'signup'): Promise<any> => {
    const response = await api.post('/auth/verify-otp', {
      uid,
      otp: otpCode,
      otp_type: otpType,
    });
    return unwrap(response);
  },
  resendOTP: async (email: string, otpType: 'signup' | 'forgotpassword' = 'signup'): Promise<{ uid: string }> => {
    const response = await api.post('/auth/resend-otp', {
      email,
      otp_type: otpType,
    });
    return unwrap(response);
  },
  forgotPassword: async (email: string): Promise<{ uid: string }> => {
    const response = await api.post('/auth/forgot-password', { email });
    return unwrap(response);
  },
  resetPassword: async (resetToken: string, newPassword: string): Promise<any> => {
    const response = await api.post('/auth/reset-password', {
      reset_token: resetToken,
      new_password: newPassword,
    });
    return unwrap(response);
  },
};
