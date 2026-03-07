# Security Policy

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories**: Use the [GitHub Security Advisory](https://github.com/anchapin/ModPorter-AI/security/advisories/new) to report vulnerabilities privately.

2. **Email**: Contact us at **alex** (you can find the email associated with the GitHub account @anchapin).

### What to Include

When reporting a security vulnerability, please include:

- Type of vulnerability (e.g., XSS, SQL injection, etc.)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment of the vulnerability

## Disclosure Process

Once we receive a security vulnerability report:

1. **Acknowledgment**: We will acknowledge receipt of your report within 48 hours.

2. **Initial Assessment**: We will conduct an initial assessment to determine the severity and validity of the vulnerability.

3. **Regular Updates**: We will provide updates on the progress of addressing the vulnerability every 7 days.

4. **Resolution**: We will work on a fix and test the solution.

5. **Public Disclosure**: Once the vulnerability has been addressed, we will publicly disclose the details in the release notes.

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Best Practices

When contributing to ModPorter-AI, please follow these security best practices:

- Never commit sensitive information (API keys, passwords, tokens) to the repository
- Use environment variables for configuration secrets
- Follow the principle of least privilege
- Keep dependencies up to date
- Run security checks before submitting PRs

## Security-Related Configuration

For deployment security configurations, see:
- [Security Configuration Guide](.github/security-config-guide.md)
- [Security Check Script](.github/security-check.sh)

## Credits

We appreciate the efforts of security researchers and contributors who help us keep ModPorter-AI secure. With your permission, we will acknowledge your contribution in the security advisory.
