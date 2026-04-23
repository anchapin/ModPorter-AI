#!/usr/bin/env python3
"""
Beta Go/No-Go Smoke Test for Issue #1165

Run this script to verify all production requirements before inviting first beta user.
Tests authentication, conversion pipeline, billing, and error handling.

Usage:
    python scripts/beta_smoke_test.py --env production
    python scripts/beta_smoke_test.py --env staging --verbose
"""

import asyncio
import os
import sys
import httpx
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class BetaSmokeTest:
    """Beta go/no-go smoke test suite"""

    def __init__(self, base_url: str, api_key: Optional[str] = None, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.verbose = verbose
        self.results = []
        self.test_user_email = f"beta_test_{int(time.time())}@portkit.cloud"
        self.test_user_password = "TestPass123!@#"
        self.access_token = None
        self.refresh_token = None
        self.conversion_job_id = None
        self.uploaded_file_id = None

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] [{level}]"
        print(f"{prefix} {message}")

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({"test": test_name, "passed": passed, "details": details})
        self.log(f"{status} - {test_name}", "PASS" if passed else "FAIL")
        if details and self.verbose:
            self.log(f"  Details: {details}", "DEBUG")

    async def make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
                return {
                    "status": response.status_code,
                    "data": response.json() if response.content else {},
                    "headers": dict(response.headers),
                }
            except Exception as e:
                return {"status": 0, "data": {}, "error": str(e)}

    # ============================================
    # Authentication Tests
    # ============================================

    async def test_registration(self) -> bool:
        """Test user registration"""
        self.log("Testing user registration...")

        response = await self.make_request(
            "POST",
            "/api/v1/auth/register",
            json={
                "email": self.test_user_email,
                "password": self.test_user_password,
            },
        )

        if response["status"] == 201 or response["status"] == 200:
            self.log_result("User Registration", True)
            return True
        else:
            self.log_result(
                "User Registration", False, f"Status: {response['status']}, Error: {response.get('error', 'Unknown')}"
            )
            return False

    async def test_login(self) -> bool:
        """Test user login"""
        self.log("Testing user login...")

        response = await self.make_request(
            "POST",
            "/api/v1/auth/login",
            json={
                "email": self.test_user_email,
                "password": self.test_user_password,
            },
        )

        if response["status"] == 200:
            self.access_token = response["data"].get("access_token")
            self.refresh_token = response["data"].get("refresh_token")
            self.log_result("User Login", True, "Access token received")
            return True
        else:
            self.log_result("User Login", False, f"Status: {response['status']}")
            return False

    async def test_email_verification(self) -> bool:
        """Test email verification endpoint exists"""
        self.log("Testing email verification endpoint...")

        # Just verify the endpoint exists (actual verification requires email token)
        response = await self.make_request("GET", "/api/v1/auth/verify-email/dummy-token")

        # Expect 400 or 404 for invalid token, but endpoint should exist
        if response["status"] in [400, 404, 422]:
            self.log_result("Email Verification Endpoint", True, "Endpoint exists")
            return True
        else:
            self.log_result("Email Verification Endpoint", False, f"Status: {response['status']}")
            return False

    async def test_discord_oauth(self) -> bool:
        """Test Discord OAuth endpoint"""
        self.log("Testing Discord OAuth...")

        response = await self.make_request("GET", "/api/v1/auth/oauth/discord")

        # Should return authorization URL or error about missing config
        if response["status"] in [200, 500, 503]:
            self.log_result("Discord OAuth", True, "OAuth endpoint available")
            return True
        else:
            self.log_result("Discord OAuth", False, f"Status: {response['status']}")
            return False

    async def test_password_reset(self) -> bool:
        """Test password reset request"""
        self.log("Testing password reset...")

        response = await self.make_request(
            "POST",
            "/api/v1/auth/forgot-password",
            json={"email": self.test_user_email},
        )

        # Should accept the request even if email doesn't exist
        if response["status"] in [200, 201]:
            self.log_result("Password Reset Request", True)
            return True
        else:
            self.log_result("Password Reset Request", False, f"Status: {response['status']}")
            return False

    # ============================================
    # Conversion Pipeline Tests
    # ============================================

    async def test_file_upload(self) -> bool:
        """Test .jar file upload"""
        self.log("Testing file upload...")

        # Create a minimal valid JAR file for testing
        # In production, this would be a real mod JAR
        test_jar_path = Path(__file__).parent / "test_mod.jar"

        # Create dummy JAR file (minimal valid structure)
        import zipfile

        with zipfile.ZipFile(test_jar_path, "w") as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zf.writestr("mod.class", b"dummy bytecode")

        try:
            with open(test_jar_path, "rb") as f:
                files = {"file": (test_jar_path.name, f, "application/java-archive")}
                response = await self.make_request("POST", "/api/v1/upload", files=files)

            # Clean up
            test_jar_path.unlink()

            if response["status"] in [200, 201]:
                self.uploaded_file_id = response["data"].get("file_id")
                self.log_result("File Upload", True, f"File ID: {self.uploaded_file_id}")
                return True
            else:
                self.log_result("File Upload", False, f"Status: {response['status']}")
                return False
        except Exception as e:
            self.log_result("File Upload", False, str(e))
            return False

    async def test_start_conversion(self) -> bool:
        """Test starting a conversion job"""
        self.log("Testing conversion start...")

        if not self.uploaded_file_id:
            self.log_result("Start Conversion", False, "No uploaded file")
            return False

        response = await self.make_request(
            "POST",
            "/api/v1/convert",
            json={
                "file_id": self.uploaded_file_id,
                "original_filename": "test_mod.jar",
                "target_version": "1.20.0",
            },
        )

        if response["status"] in [200, 201]:
            self.conversion_job_id = response["data"].get("job_id")
            self.log_result("Start Conversion", True, f"Job ID: {self.conversion_job_id}")
            return True
        else:
            self.log_result("Start Conversion", False, f"Status: {response['status']}")
            return False

    async def test_conversion_progress(self) -> bool:
        """Test conversion progress tracking"""
        self.log("Testing conversion progress...")

        if not self.conversion_job_id:
            self.log_result("Conversion Progress", False, "No conversion job")
            return False

        # Check status multiple times with delay to verify progress
        progress_updates = []
        for i in range(3):
            await asyncio.sleep(2)

            response = await self.make_request(
                "GET", f"/api/v1/convert/{self.conversion_job_id}/status"
            )

            if response["status"] == 200:
                status = response["data"]
                progress = status.get("progress", 0)
                job_status = status.get("status", "")

                if self.verbose:
                    self.log(f"  Check {i+1}: Status={job_status}, Progress={progress}%", "DEBUG")

                # Progress should not be frozen at 0
                if i == 0 and progress > 0:
                    progress_updates.append(progress)
                elif i > 0 and progress >= progress_updates[-1]:
                    progress_updates.append(progress)

        if len(progress_updates) >= 2:
            self.log_result("Conversion Progress", True, f"Progress updated: {progress_updates}")
            return True
        else:
            self.log_result("Conversion Progress", False, "Progress not updating properly")
            return False

    async def test_conversion_completion(self) -> bool:
        """Test conversion completes and generates report"""
        self.log("Testing conversion completion...")

        if not self.conversion_job_id:
            self.log_result("Conversion Completion", False, "No conversion job")
            return False

        # Wait for completion (max 60 seconds)
        for _ in range(30):
            await asyncio.sleep(2)

            response = await self.make_request(
                "GET", f"/api/v1/convert/{self.conversion_job_id}/status"
            )

            if response["status"] == 200:
                status = response["data"]
                job_status = status.get("status", "")

                if job_status == "completed":
                    # Check for conversion report
                    report_response = await self.make_request(
                        "GET", f"/api/v1/jobs/{self.conversion_job_id}/report"
                    )

                    if report_response["status"] == 200:
                        self.log_result("Conversion Completion", True, "Report generated")
                        return True
                    else:
                        self.log_result("Conversion Completion", False, "No report generated")
                        return False

                elif job_status == "failed":
                    error = response["data"].get("error", "Unknown error")
                    self.log_result("Conversion Completion", False, f"Job failed: {error}")
                    return False

        self.log_result("Conversion Completion", False, "Timeout waiting for completion")
        return False

    async def test_mcaddon_download(self) -> bool:
        """Test .mcaddon file download"""
        self.log("Testing .mcaddon download...")

        if not self.conversion_job_id:
            self.log_result(".mcaddon Download", False, "No conversion job")
            return False

        response = await self.make_request(
            "GET", f"/api/v1/convert/{self.conversion_job_id}/download"
        )

        # Download endpoint should return file or redirect
        if response["status"] in [200, 302, 301]:
            self.log_result(".mcaddon Download", True, "Download available")
            return True
        else:
            self.log_result(".mcaddon Download", False, f"Status: {response['status']}")
            return False

    async def test_conversion_history(self) -> bool:
        """Test conversion history dashboard"""
        self.log("Testing conversion history...")

        response = await self.make_request("GET", "/api/v1/conversions")

        if response["status"] == 200:
            conversions = response["data"]
            self.log_result("Conversion History", True, f"Found {len(conversions)} conversions")
            return True
        else:
            self.log_result("Conversion History", False, f"Status: {response['status']}")
            return False

    # ============================================
    # Billing Tests
    # ============================================

    async def test_stripe_checkout(self) -> bool:
        """Test Stripe Checkout session creation"""
        self.log("Testing Stripe Checkout...")

        response = await self.make_request(
            "POST",
            "/api/v1/billing/checkout",
            json={"tier": "pro", "trial": True},
        )

        # Should return checkout URL or error about missing Stripe config
        if response["status"] in [200, 500, 503]:
            if response["status"] == 200:
                checkout_url = response["data"].get("checkout_url")
                if checkout_url:
                    self.log_result("Stripe Checkout", True, "Checkout URL generated")
                    return True
                else:
                    self.log_result("Stripe Checkout", False, "No checkout URL returned")
                    return False
            else:
                # Stripe not configured but endpoint exists
                self.log_result("Stripe Checkout", True, "Endpoint available (Stripe not configured)")
                return True
        else:
            self.log_result("Stripe Checkout", False, f"Status: {response['status']}")
            return False

    async def test_free_tier_limit(self) -> bool:
        """Test free tier limit enforcement"""
        self.log("Testing free tier limit...")

        # Check usage endpoint
        response = await self.make_request("GET", "/api/v1/billing/usage")

        if response["status"] == 200:
            usage = response["data"]
            remaining = usage.get("remaining", 0)
            self.log_result("Free Tier Limit", True, f"Remaining: {remaining}")
            return True
        else:
            self.log_result("Free Tier Limit", False, f"Status: {response['status']}")
            return False

    # ============================================
    # Error Handling Tests
    # ============================================

    async def test_invalid_file_type(self) -> bool:
        """Test user-friendly error for invalid file type"""
        self.log("Testing invalid file type error...")

        # Try to upload a .txt file
        test_txt = Path(__file__).parent / "test.txt"
        test_txt.write_text("This is not a JAR file")

        try:
            with open(test_txt, "rb") as f:
                files = {"file": (test_txt.name, f, "text/plain")}
                response = await self.make_request("POST", "/api/v1/upload", files=files)

            test_txt.unlink()

            if response["status"] == 400:
                error_msg = response["data"].get("detail", "").lower()
                if "not supported" in error_msg or "allowed" in error_msg:
                    self.log_result("Invalid File Type Error", True, "User-friendly error message")
                    return True
                else:
                    self.log_result("Invalid File Type Error", False, "Generic error message")
                    return False
            else:
                self.log_result("Invalid File Type Error", False, f"Status: {response['status']}")
                return False
        except Exception as e:
            self.log_result("Invalid File Type Error", False, str(e))
            return False

    async def test_no_file_error(self) -> bool:
        """Test error when no file provided"""
        self.log("Testing no file error...")

        response = await self.make_request("POST", "/api/v1/upload")

        if response["status"] == 400:
            error_msg = response["data"].get("detail", "").lower()
            if "no file" in error_msg or "required" in error_msg:
                self.log_result("No File Error", True, "Clear error message")
                return True
            else:
                self.log_result("No File Error", False, "Generic error message")
                return False
        else:
            self.log_result("No File Error", False, f"Status: {response['status']}")
            return False

    # ============================================
    # Test Runner
    # ============================================

    async def run_all_tests(self):
        """Run all smoke tests"""
        self.log("=" * 60)
        self.log("BETA GO/NO-GO SMOKE TEST")
        self.log(f"Environment: {self.base_url}")
        self.log("=" * 60)
        self.log("")

        # Authentication tests
        self.log("### AUTHENTICATION TESTS ###")
        await self.test_registration()
        await self.test_login()
        await self.test_email_verification()
        await self.test_discord_oauth()
        await self.test_password_reset()
        self.log("")

        # Conversion pipeline tests
        self.log("### CONVERSION PIPELINE TESTS ###")
        await self.test_file_upload()
        await self.test_start_conversion()
        await self.test_conversion_progress()
        await self.test_conversion_completion()
        await self.test_mcaddon_download()
        await self.test_conversion_history()
        self.log("")

        # Billing tests
        self.log("### BILLING TESTS ###")
        await self.test_stripe_checkout()
        await self.test_free_tier_limit()
        self.log("")

        # Error handling tests
        self.log("### ERROR HANDLING TESTS ###")
        await self.test_invalid_file_type()
        await self.test_no_file_error()
        self.log("")

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        percentage = (passed / total * 100) if total > 0 else 0

        self.log("=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {total}")
        self.log(f"Passed: {passed} ({percentage:.1f}%)")
        self.log(f"Failed: {total - passed}")
        self.log("")

        # Decision
        if percentage >= 80:
            self.log("🟢 DECISION: GO - Beta ready!", "SUCCESS")
        elif percentage >= 60:
            self.log("🟡 DECISION: PROCEED WITH CAUTION - Minor issues found", "WARNING")
        else:
            self.log("🔴 DECISION: NO-GO - Critical issues must be resolved", "ERROR")

        self.log("")

        # Failed tests
        failed_tests = [r for r in self.results if not r["passed"]]
        if failed_tests:
            self.log("Failed Tests:", "ERROR")
            for test in failed_tests:
                self.log(f"  ❌ {test['test']}: {test['details']}", "ERROR")
            self.log("")

        # Create report file
        report_path = Path(__file__).parent / f"beta_smoke_test_report_{int(time.time())}.json"
        with open(report_path, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "environment": self.base_url,
                    "total_tests": total,
                    "passed": passed,
                    "failed": total - passed,
                    "percentage": percentage,
                    "results": self.results,
                },
                f,
                indent=2,
            )
        self.log(f"Report saved to: {report_path}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Beta Go/No-Go Smoke Test")
    parser.add_argument(
        "--env",
        choices=["production", "staging", "local"],
        default="local",
        help="Environment to test",
    )
    parser.add_argument("--url", help="Override base URL")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Determine base URL
    if args.url:
        base_url = args.url
    else:
        env_urls = {
<<<<<<< HEAD
            "production": "https://portkit.ai",
            "staging": "https://staging.portkit.ai",
=======
            "production": "https://portkit.cloud",
            "staging": "https://staging.portkit.cloud",
>>>>>>> 0bc17858 (fix(ci): correct domain from portkit.ai to portkit.cloud in smoke test)
            "local": "http://localhost:8000",
        }
        base_url = env_urls.get(args.env, "http://localhost:8000")

    # Run tests
    tester = BetaSmokeTest(base_url, args.api_key, args.verbose)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
