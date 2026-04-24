import React from 'react';
import { createRouter, createRoute, createRootRoute, Outlet } from '@tanstack/react-router';
import { LandingPage } from './pages/LandingPage';
import { ExplanationPage } from './pages/ExplanationPage';
import { SignupPage } from './pages/auth/SignupPage';
import { LoginPage } from './pages/auth/LoginPage';
import { OTPPage } from './pages/auth/OTPPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { AppLayout } from './components/layout/AppLayout';
import { AdminLayout } from './components/layout/AdminLayout';
import { DiscoveryPage } from './pages/app/DiscoveryPage';
import { TrackerPage } from './pages/app/TrackerPage';
import { EventDetail } from './pages/app/EventDetail';
import { AdminLoginPage } from './pages/admin/AdminLoginPage';
import { AdminOverviewPage } from './pages/admin/AdminOverviewPage';
import { AdminDiscoveryPage } from './pages/admin/AdminDiscoveryPage';
import { AdminSystemTrackerPage } from './pages/admin/AdminSystemTrackerPage';

const adminBasePath = import.meta.env.VITE_ADMIN_ROUTE_PREFIX || '/control-room';

export const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

export const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LandingPage,
});

export const explanationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/how-it-works',
  component: ExplanationPage,
});

export const signupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/signup',
  component: SignupPage,
});

export const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/login',
  component: LoginPage,
});

export const otpRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/otp',
  component: OTPPage,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      email: (search.email as string) || '',
      uid: (search.uid as string) || '',
      type: (search.type as 'signup' | 'forgotpassword') || 'signup',
    };
  },
});

export const forgotPasswordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/forgot-password',
  component: ForgotPasswordPage,
});

export const resetPasswordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/reset-password',
  component: ResetPasswordPage,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      reset_token: (search.reset_token as string) || '',
    };
  },
});

export const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/app',
  component: AppLayout,
});

export const adminLoginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: `${adminBasePath}/login`,
  component: AdminLoginPage,
});

export const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: adminBasePath,
  component: AdminLayout,
});

export const discoverRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/',
  component: DiscoveryPage,
});

export const trackerRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/tracker',
  component: TrackerPage,
});

export const analysisRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/events/$eventId',
  component: EventDetail,
  validateSearch: (search: Record<string, unknown>) => ({
    source: (search.source as string) || '',
  }),
});

const appRouteWithChildren = appRoute.addChildren([discoverRoute, trackerRoute, analysisRoute]);
const adminIndexRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: '/',
  component: AdminOverviewPage,
});

const adminDiscoveryRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: '/discovery',
  component: AdminDiscoveryPage,
});

const adminSystemTrackerRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: '/system-tracker',
  component: AdminSystemTrackerPage,
});

const adminRouteWithChildren = adminRoute.addChildren([
  adminIndexRoute,
  adminDiscoveryRoute,
  adminSystemTrackerRoute,
]);

const routeTree = rootRoute.addChildren([
  landingRoute,
  explanationRoute,
  signupRoute,
  loginRoute,
  otpRoute,
  forgotPasswordRoute,
  resetPasswordRoute,
  appRouteWithChildren,
  adminLoginRoute,
  adminRouteWithChildren,
]);

export const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
