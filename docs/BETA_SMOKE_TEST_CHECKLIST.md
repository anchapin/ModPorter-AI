# Beta Go/No-Go Smoke Test Checklist

**Issue:** #1165 - End-to-end production smoke test
**Purpose:** Verify all production requirements before inviting first beta user

## 📋 Pre-Test Checklist

- [ ] Production deployment is complete (Issue #1164)
- [ ] Environment variables are configured:
  - [ ] `DATABASE_URL`
  - [ ] `REDIS_URL`
  - [ ] `RESEND_API_KEY` (for emails)
  - [ ] `STRIPE_SECRET_KEY`
  - [ ] `STRIPE_PUBLISHABLE_KEY`
  - [ ] `DISCORD_CLIENT_ID`
  - [ ] `DISCORD_CLIENT_SECRET`
- [ ] Database migrations are up to date
- [ ] Redis is running and accessible
- [ ] Email service (Resend) is configured
- [ ] Stripe is configured (test mode)

---

## 🔐 Authentication Tests

### 1. Registration + Email Verification
- [ ] Navigate to `https://portkit.ai/register`
- [ ] Enter email: `beta_test@example.com`
- [ ] Enter password: `TestPass123!@#`
- [ ] Submit registration form
- [ ] **Expected:** Success message "Registration successful"
- [ ] Check email inbox for verification link
- [ ] **Expected:** Verification email arrives within 60 seconds
- [ ] Click verification link
- [ ] **Expected:** "Email verified successfully" message

### 2. Discord OAuth Login
- [ ] Navigate to `https://portkit.ai/login`
- [ ] Click "Continue with Discord"
- [ ] Authorize Discord app
- [ ] **Expected:** Redirected to dashboard with Discord account linked
- [ ] **NO-GO Criteria:** OAuth redirect loops occur

### 3. Password Reset
- [ ] Navigate to `https://portkit.ai/forgot-password`
- [ ] Enter email: `beta_test@example.com`
- [ ] Submit form
- [ ] **Expected:** Success message (even if email doesn't exist)
- [ ] Check email inbox for reset link
- [ ] **Expected:** Password reset email arrives within 60 seconds
- [ ] Click reset link
- [ ] Enter new password: `NewPass456!@#`
- [ ] Submit
- [ ] **Expected:** "Password reset successfully" message

---

## 🔄 Conversion Pipeline Tests

### 4. Upload .jar File
- [ ] Download test mod: [Iron Chests](https://modrinth.com/mod/iron-chests) or [Farmer's Delight](https://modrinth.com/mod/farmers-delight)
- [ ] Navigate to `https://portkit.ai`
- [ ] Click "Upload Mod" button
- [ ] Select downloaded `.jar` file
- [ ] Click "Convert"
- [ ] **Expected:** Upload starts immediately, no 500 error

### 5. Progress Indicator
- [ ] Watch conversion progress
- [ ] **Expected:** Progress bar updates (not frozen spinner)
- [ ] **Expected:** Agent names shown: JavaAnalyzerAgent, BedrockArchitectAgent, etc.
- [ ] **Expected:** Progress percentage increases (0% → 25% → 50% → 100%)
- [ ] **NO-GO Criteria:** UI spins silently forever with frozen spinner

### 6. Conversion Report Generation
- [ ] Wait for conversion to complete (~2-3 minutes for simulation)
- [ ] **Expected:** "Conversion complete" message appears
- [ ] Click "View Report" button
- [ ] **Expected:** Conversion report displays with:
  - [ ] Mod name and version
  - [ ] Conversion summary
  - [ ] Converted components list
  - [ ] Any warnings or issues

### 7. Download .mcaddon File
- [ ] Click "Download .mcaddon" button
- [ ] **Expected:** File download starts immediately
- [ ] Verify downloaded file has `.mcaddon` extension
- [ ] Verify file size is reasonable (>1KB)

### 8. Completion Email
- [ ] After conversion completes, check email inbox
- [ ] **Expected:** Completion email arrives within 60 seconds
- [ ] **Expected:** Email contains:
  - [ ] Conversion ID
  - [ ] Download link
  - [ ] Success/failure status
- [ ] **NO-GO Criteria:** No completion email arrives

### 9. Conversion History Dashboard
- [ ] Navigate to `https://portkit.ai/dashboard/conversions`
- [ ] **Expected:** List of all previous conversions
- [ ] **Expected:** Each entry shows:
  - [ ] Mod name
  - [ ] Conversion date
  - [ ] Status (completed/failed)
  - [ ] Download button

### 10. Zero Output Test
- [ ] Upload and convert at least 2 different test mods
- [ ] **Expected:** Both conversions produce output files
- [ ] **NO-GO Criteria:** Any conversion produces zero output

---

## 💳 Billing Tests

### 11. Stripe Checkout
- [ ] Navigate to `https://portkit.ai/pricing`
- [ ] Click "Upgrade to Pro" button
- [ ] **Expected:** Stripe Checkout page opens
- [ ] Enter test card: `4242 4242 4242 4242`
- [ ] Enter expiry: `12/34`
- [ ] Enter CVC: `123`
- [ ] Enter ZIP: `12345`
- [ ] Click "Pay"
- [ ] **Expected:** Redirect to success page
- [ ] **Expected:** Subscription shows as "Pro" in dashboard
- [ ] **NO-GO Criteria:** Stripe checkout is broken

### 12. Subscription Activation
- [ ] After payment, check account status
- [ ] **Expected:** "Pro" tier is active
- [ ] **Expected:** Conversion limit shows "Unlimited"

### 13. Free Tier Limit Enforcement
- [ ] Create new free account (if needed)
- [ ] Convert 3 mods (free tier limit)
- [ ] Attempt to convert 4th mod
- [ ] **Expected:** Upgrade prompt appears
- [ ] **Expected:** Conversion is blocked until upgrade

---

## ⚠️ Error Handling Tests

### 14. Invalid File Type
- [ ] Try to upload a non-JAR file (e.g., `.txt`, `.png`)
- [ ] **Expected:** User-friendly error message
- [ ] **Expected:** Message says "File type not supported. Allowed: .jar, .zip"
- [ ] **Expected:** No 500 server error
- [ ] **NO-GO Criteria:** Generic 500 error shown to user

### 15. No File Provided
- [ ] Click "Convert" without selecting a file
- [ ] **Expected:** Clear error message
- [ ] **Expected:** Message says "No file provided"
- [ ] **Expected:** No 500 server error

---

## 🛑 STOP / NO-GO Criteria

**STOP if any of these occur:**

- [ ] OAuth redirect loops
- [ ] Conversion produces zero output on >1 test mod
- [ ] Stripe checkout is broken
- [ ] No completion email
- [ ] Conversion UI spins silently forever

---

## 📊 Test Results

| Test | Status | Notes |
|------|--------|-------|
| Registration + Email Verification | ⬜ Pass / ❌ Fail | |
| Discord OAuth Login | ⬜ Pass / ❌ Fail | |
| Password Reset Email | ⬜ Pass / ❌ Fail | |
| Upload .jar File | ⬜ Pass / ❌ Fail | |
| Progress Indicator | ⬜ Pass / ❌ Fail | |
| Conversion Report | ⬜ Pass / ❌ Fail | |
| Download .mcaddon | ⬜ Pass / ❌ Fail | |
| Completion Email | ⬜ Pass / ❌ Fail | |
| Conversion History | ⬜ Pass / ❌ Fail | |
| Zero Output Test | ⬜ Pass / ❌ Fail | |
| Stripe Checkout | ⬜ Pass / ❌ Fail | |
| Subscription Activation | ⬜ Pass / ❌ Fail | |
| Free Tier Limit | ⬜ Pass / ❌ Fail | |
| Invalid File Type Error | ⬜ Pass / ❌ Fail | |
| No File Error | ⬜ Pass / ❌ Fail | |

**Total Passed:** ___ / 15

---

## ✅ Go/No-Go Decision

**GO** (Ready for Beta) if:
- All critical tests pass (Authentication, Conversion Pipeline, Billing)
- No STOP/NO-GO criteria triggered
- At least 80% of all tests pass

**PROCEED WITH CAUTION** if:
- Minor issues found but core functionality works
- 60-80% of tests pass
- No critical blockers

**NO-GO** if:
- Any STOP/NO-GO criteria triggered
- Critical functionality broken
- Less than 60% of tests pass

**Decision:** ⬜ GO / 🟡 PROCEED WITH CAUTION / 🔴 NO-GO

**Date:** _______________
**Tester:** _______________
**Notes:** _______________

---

## 🚀 Post-Test Actions

If **GO**:
- [ ] Update issue #1165 with test results
- [ ] Invite first beta user
- [ ] Monitor production logs for first 24 hours
- [ ] Set up alerts for errors

If **NO-GO**:
- [ ] Create follow-up issues for each failure
- [ ] Fix critical blockers
- [ ] Re-run smoke tests
- [ ] Update issue #1165 with progress
