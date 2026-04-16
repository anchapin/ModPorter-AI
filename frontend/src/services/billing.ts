/**
 * Billing service for Stripe subscription integration (Issue #970)
 */

import { API_BASE_URL } from './api';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export interface CheckoutRequest {
  tier: 'pro' | 'studio';
  trial?: boolean;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export interface PortalResponse {
  portal_url: string;
}

export interface SubscriptionStatus {
  tier: string;
  status: string | null;
  trial_ends_at: string | null;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
  stripe_customer_id: string | null;
}

export interface PublishableKeyResponse {
  publishable_key: string;
}

export const createCheckoutSession = async (
  request: CheckoutRequest
): Promise<CheckoutResponse> => {
  const response = await fetch(`${API_BASE_URL}/billing/checkout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ detail: 'Failed to create checkout session' }));
    throw new ApiError(
      errorData.detail || 'Failed to create checkout session',
      response.status
    );
  }

  return response.json();
};

export const createPortalSession = async (
  returnUrl?: string
): Promise<PortalResponse> => {
  const response = await fetch(`${API_BASE_URL}/billing/portal`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ return_url: returnUrl }),
  });

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ detail: 'Failed to create portal session' }));
    throw new ApiError(
      errorData.detail || 'Failed to create portal session',
      response.status
    );
  }

  return response.json();
};

export const getSubscriptionStatus = async (): Promise<SubscriptionStatus> => {
  const response = await fetch(`${API_BASE_URL}/billing/subscription`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ detail: 'Failed to get subscription status' }));
    throw new ApiError(
      errorData.detail || 'Failed to get subscription status',
      response.status
    );
  }

  return response.json();
};

export const getPublishableKey = async (): Promise<PublishableKeyResponse> => {
  const response = await fetch(`${API_BASE_URL}/billing/publishable-key`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ detail: 'Failed to get publishable key' }));
    throw new ApiError(
      errorData.detail || 'Failed to get publishable key',
      response.status
    );
  }

  return response.json();
};

export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem('access_token');
};
