# DNS Configuration Guide for ModPorter AI

This document provides DNS record configurations for various DNS providers.

## Domain: modporter.ai

## Required DNS Records

### A Records (Address Records)

| Type | Name | Value | TTL | Description |
|------|------|-------|-----|-------------|
| A | @ (modporter.ai) | `<PRODUCTION_SERVER_IP>` | 3600 | Main domain |
| A | www | `<PRODUCTION_SERVER_IP>` | 3600 | WWW subdomain |
| A | api | `<PRODUCTION_SERVER_IP>` | 3600 | API subdomain |
| A | grafana | `<PRODUCTION_SERVER_IP>` | 3600 | Grafana subdomain |

### MX Records (Mail Exchange)

| Type | Name | Value | Priority | TTL | Description |
|------|------|-------|----------|-----|-------------|
| MX | @ | mx1.sendgrid.net | 10 | 3600 | SendGrid primary |
| MX | @ | mx2.sendgrid.net | 20 | 3600 | SendGrid backup |

### TXT Records (Text Records)

| Type | Name | Value | TTL | Description |
|------|------|-------|-----|-------------|
| TXT | @ | `"v=spf1 include:sendgrid.net ~all"` | 3600 | SPF for email |
| TXT | modporter.ai._domainkey | `<DKIM_KEY_FROM_SENDGRID>` | 3600 | DKIM signing |
| TXT | @ | `"v=DMARC1; p=none; rua=mailto:dmarc@modporter.ai"` | 3600 | DMARC policy |

### CNAME Records (Canonical Name)

| Type | Name | Value | TTL | Description |
|------|------|-------|-----|-------------|
| CNAME | email | u12345678.ct.sendgrid.net | 3600 | SendGrid link branding |

---

## DNS Provider Specific Instructions

### Cloudflare

1. Log in to Cloudflare Dashboard
2. Select your domain (modporter.ai)
3. Go to DNS settings
4. Add records as above
5. **Important**: Disable proxy (orange cloud) for initial SSL setup
6. After SSL is working, you can enable proxy for DDoS protection

**Cloudflare-specific settings:**
- SSL/TLS Mode: Full (strict)
- Always Use HTTPS: Enabled
- HTTP Strict Transport Security (HSTS): Enabled
- Auto Minify: Enabled for HTML, CSS, JS
- Brotli Compression: Enabled

### Namecheap

1. Log in to Namecheap Dashboard
2. Select Domain List → Manage for modporter.ai
3. Go to Advanced DNS tab
4. Add records as above

**Namecheap-specific settings:**
- Email Forwarding: Disabled (using SendGrid)
- URL Redirect: Not needed

### GoDaddy

1. Log in to GoDaddy DNS Management
2. Select modporter.ai
3. Add records as above

**GoDaddy-specific settings:**
- DNS Zone File: Edit as needed
- Nameservers: Use GoDaddy nameservers

### Route53 (AWS)

1. Log in to AWS Route53 Console
2. Select Hosted Zone for modporter.ai
3. Create Record Sets as above

**Route53-specific settings:**
- Use Alias records for root domain (@)
- Create Alias to CloudFront/ALB if using AWS services

---

## Verification Commands

### Check DNS Propagation

```bash
# Check A records
dig modporter.ai +short
dig www.modporter.ai +short
dig api.modporter.ai +short

# Check MX records
dig modporter.ai MX +short

# Check TXT records
dig modporter.ai TXT +short

# Check all records
dig modporter.ai ANY
```

### Online Tools

- **DNS Propagation**: https://dnschecker.org/
- **MX Lookup**: https://mxtoolbox.com/
- **SPF Check**: https://mxtoolbox.com/spf.aspx
- **DKIM Check**: https://mxtoolbox.com/dkim.aspx
- **DMARC Check**: https://mxtoolbox.com/dmarc.aspx

---

## Email Authentication Setup

### SPF (Sender Policy Framework)

SPF record tells receiving mail servers which servers are authorized to send email for your domain.

```
v=spf1 include:sendgrid.net ~all
```

**Explanation:**
- `v=spf1` - SPF version 1
- `include:sendgrid.net` - Authorize SendGrid servers
- `~all` - Soft fail for unauthorized servers (use `-all` for hard fail)

### DKIM (DomainKeys Identified Mail)

DKIM adds a digital signature to emails.

**Setup Steps:**
1. Log in to SendGrid
2. Go to Settings → Sender Authentication
3. Authenticate your domain
4. Copy the DKIM CNAME records provided
5. Add to your DNS

### DMARC (Domain-based Message Authentication)

DMARC tells receiving servers what to do if SPF or DKIM fails.

```
v=DMARC1; p=none; rua=mailto:dmarc@modporter.ai
```

**Policy Options:**
- `p=none` - Monitor only (start with this)
- `p=quarantine` - Send failing emails to spam
- `p=reject` - Reject failing emails

**After monitoring period (1-2 weeks), update to:**
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@modporter.ai; pct=100
```

---

## SSL Certificate Verification

After DNS is configured and SSL certificates are installed:

```bash
# Check SSL certificate
openssl s_client -connect modporter.ai:443 -servername modporter.ai

# Check certificate expiry
echo | openssl s_client -connect modporter.ai:443 -servername modporter.ai 2>/dev/null | openssl x509 -noout -dates

# Check SSL Labs rating
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=modporter.ai
```

---

## Troubleshooting

### DNS Not Propagating

1. Wait up to 48 hours for full propagation
2. Check with multiple DNS servers: `dig @8.8.8.8 modporter.ai`
3. Clear local DNS cache: `sudo systemd-resolve --flush-caches`

### SSL Certificate Issues

1. Verify DNS is pointing to correct IP
2. Ensure port 80 is open for ACME challenge
3. Check certbot logs: `/var/log/letsencrypt/letsencrypt.log`

### Email Deliverability Issues

1. Verify SPF record: `dig modporter.ai TXT`
2. Check DKIM setup in SendGrid
3. Verify DMARC policy is correct
4. Check IP reputation: https://talosintelligence.com/

---

## Post-Setup Checklist

- [ ] All A records propagating correctly
- [ ] MX records pointing to SendGrid
- [ ] SPF record configured
- [ ] DKIM CNAME records added
- [ ] DMARC record configured
- [ ] SSL certificate installed and valid
- [ ] HTTPS redirect working
- [ ] Email sending successfully
- [ ] SSL Labs rating A or A+

---

## Contact Information

For DNS issues:
- Cloudflare Support: https://support.cloudflare.com/
- Namecheap Support: https://www.namecheap.com/support/
- GoDaddy Support: https://www.godaddy.com/help
- AWS Route53: https://console.aws.amazon.com/route53/

For email issues:
- SendGrid Support: https://support.sendgrid.com/
