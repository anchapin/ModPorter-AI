/**
 * Subscription tier utilities for feature gating (Issue #970)
 *
 * Usage:
 *   import { hasFeatureAccess, tierRank } from '../services/subscriptionTier';
 *
 *   if (hasFeatureAccess(userTier, 'api_access')) { ... }
 *   if (tierRank(userTier) >= tierRank('pro')) { ... }
 */

export type SubscriptionTier = 'free' | 'pro' | 'studio' | 'enterprise';

export const TIER_HIERARCHY: Record<SubscriptionTier, number> = {
  free: 0,
  pro: 1,
  studio: 2,
  enterprise: 3,
};

export const tierRank = (tier: SubscriptionTier): number => {
  return TIER_HIERARCHY[tier] ?? 0;
};

export const hasFeatureAccess = (
  userTier: SubscriptionTier | string | undefined,
  feature: PremiumFeature
): boolean => {
  const normalizedTier = (userTier ?? 'free').toLowerCase() as SubscriptionTier;
  const userLevel = tierRank(normalizedTier);

  const featureRequirements: Record<PremiumFeature, SubscriptionTier> = {
    unlimited_conversions: 'pro',
    complex_mods: 'pro',
    priority_support: 'pro',
    api_access: 'pro',
    visual_editor: 'pro',
    faster_processing: 'pro',
    conversion_history_90d: 'pro',
    no_branding: 'pro',
    team_collaboration: 'studio',
    custom_templates: 'studio',
    white_label: 'studio',
    slack_support: 'studio',
    conversion_history_1y: 'studio',
    advanced_analytics: 'studio',
    on_premise: 'enterprise',
    unlimited_api: 'enterprise',
    custom_integrations: 'enterprise',
    dedicated_support: 'enterprise',
    sla_guarantee: 'enterprise',
    unlimited_storage: 'enterprise',
    training_onboarding: 'enterprise',
  };

  const requiredTier = featureRequirements[feature];
  return userLevel >= tierRank(requiredTier);
};

export type PremiumFeature =
  | 'unlimited_conversions'
  | 'complex_mods'
  | 'priority_support'
  | 'api_access'
  | 'visual_editor'
  | 'faster_processing'
  | 'conversion_history_90d'
  | 'no_branding'
  | 'team_collaboration'
  | 'custom_templates'
  | 'white_label'
  | 'slack_support'
  | 'conversion_history_1y'
  | 'advanced_analytics'
  | 'on_premise'
  | 'unlimited_api'
  | 'custom_integrations'
  | 'dedicated_support'
  | 'sla_guarantee'
  | 'unlimited_storage'
  | 'training_onboarding';

export const FEATURE_GATE_MESSAGES: Record<PremiumFeature, string> = {
  unlimited_conversions: 'Upgrade to Pro for unlimited conversions',
  complex_mods: 'Upgrade to Pro for complex mod support',
  priority_support: 'Upgrade to Pro for priority email support',
  api_access: 'Upgrade to Pro for API access',
  visual_editor: 'Upgrade to Pro for visual editor access',
  faster_processing: 'Upgrade to Pro for faster processing speed',
  conversion_history_90d: 'Upgrade to Pro for 90-day conversion history',
  no_branding: 'Upgrade to Pro to remove ModPorter branding',
  team_collaboration: 'Upgrade to Studio for team collaboration',
  custom_templates: 'Upgrade to Studio for custom templates',
  white_label: 'Upgrade to Studio for white-label options',
  slack_support: 'Upgrade to Studio for Slack support',
  conversion_history_1y: 'Upgrade to Studio for 1-year conversion history',
  advanced_analytics: 'Upgrade to Studio for advanced analytics',
  on_premise: 'Contact sales for on-premise deployment',
  unlimited_api: 'Contact sales for unlimited API access',
  custom_integrations: 'Contact sales for custom integrations',
  dedicated_support: 'Contact sales for dedicated support manager',
  sla_guarantee: 'Contact sales for SLA guarantees',
  unlimited_storage: 'Contact sales for unlimited storage',
  training_onboarding: 'Contact sales for training and onboarding',
};

export const getUpgradeMessage = (feature: PremiumFeature): string => {
  return FEATURE_GATE_MESSAGES[feature];
};

export const isTrialEligible = (tier: SubscriptionTier): boolean => {
  return tier === 'pro' || tier === 'studio';
};
