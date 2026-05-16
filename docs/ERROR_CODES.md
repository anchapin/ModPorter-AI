# Error Code Reference

Complete reference for all error codes returned by the Portkit API. Each entry includes the error code, cause, fix, and workaround.

## Error Code Format

All error codes follow the format `ERR_<CATEGORY>_<NUMBER>` for machine readability. Legacy codes may use the older `CODE_FORMAT` style.

## Parsing Errors

### ERR_PARSE_001: PARSE_ERROR

**Category:** Parse Error
**HTTP Status:** 422
**Retryable:** Yes

**Cause:** The mod file could not be parsed. This typically occurs when the JAR/ZIP structure is invalid or the mod metadata (META-INF) is corrupted.

**Fix:**
1. Verify the file is a valid Java archive (`.jar`)
2. Check that META-INF manifest files are properly formatted
3. Ensure the mod has a valid `mods.toml` or `fabric.mod.json`

**Workaround:** Try repackaging the mod with standard Java tooling.

---

### ERR_PARSE_002: INVALID_SYNTAX

**Category:** Parse Error
**HTTP Status:** 422
**Retryable:** No

**Cause:** Mod configuration files contain syntax errors. Common in `mods.toml`, `defaultconfigs`, or JSON metadata files.

**Fix:**
1. Validate the mod descriptor file syntax
2. Check for missing brackets, quotes, or commas
3. Use a linter for TOML/JSON if available

**Workaround:** Remove the problematic configuration file temporarily.

---

## Asset Errors

### ERR_ASSET_001: ASSET_ERROR

**Category:** Asset Error
**HTTP Status:** 422
**Retryable:** Yes

**Cause:** An asset referenced in the mod could not be found or processed. This includes textures, models, sounds, and other resources.

**Fix:**
1. Verify all texture paths in `pack.mcmeta` exist
2. Ensure `assets/` directory structure matches namespace references
3. Check that referenced assets are included in the JAR

**Workaround:** Provide placeholder assets or disable the feature requiring the missing asset.

---

### ERR_ASSET_002: MISSING_ASSET

**Category:** Asset Error
**HTTP Status:** 422
**Retryable:** No

**Cause:** A specific asset file referenced in code was not found in the mod package.

**Fix:**
1. Check the console/logs for which specific asset is missing
2. Add the missing file to the appropriate `assets/` folder
3. Verify case-sensitivity of file paths (Linux is case-sensitive)

**Workaround:** Remove or comment out code referencing the missing asset.

---

### ERR_ASSET_003: INVALID_ASSET_PATH

**Category:** Asset Error
**HTTP Status:** 422
**Retryable:** No

**Cause:** Asset path does not follow Minecraft's namespace convention (`assets/<namespace>/<path>`).

**Fix:**
1. Ensure path starts with `assets/` and includes namespace
2. Example: `assets/mymod/textures/item/test.png`
3. Verify the namespace folder matches your mod ID

**Workaround:** Restructure the mod to use standard asset paths.

---

## Logic Errors

### ERR_LOGIC_001: LOGIC_ERROR

**Category:** Logic Error
**HTTP Status:** 500
**Retryable:** No

**Cause:** An internal error occurred during the conversion process. This usually indicates a bug in the conversion logic or an unexpected code path.

**Fix:**
1. Report the issue to the development team with the error ID
2. Try with a simpler mod to isolate the problem
3. Check if the mod uses any non-standard Java patterns

**Workaround:** None. This requires a code fix.

---

### ERR_LOGIC_002: CONVERSION_ERROR

**Category:** Logic Error
**HTTP Status:** 422
**Retryable:** No

**Cause:** The conversion process failed. This can occur when Java code cannot be translated to equivalent Bedrock behavior.

**Fix:**
1. Simplify the mod's Java code before conversion
2. Remove or abstract platform-specific APIs
3. Break large files into smaller components

**Workaround:** Manually convert problematic code sections.

---

### ERR_LOGIC_003: BUILD_FAILED

**Category:** Logic Error
**HTTP Status:** 422
**Retryable:** Yes

**Cause:** The converted mod failed to build. This typically happens when the generated Bedrock addon has syntax errors or incompatible content.

**Fix:**
1. Run the converter with verbose output enabled
2. Check build logs for specific failure reasons
3. Verify generated JSON files are valid

**Workaround:** Retry the conversion; transient build issues may resolve.

---

## Package Errors

### ERR_PACKAGE_001: PACKAGE_ERROR

**Category:** Package Error
**HTTP Status:** 500
**Retryable:** Yes

**Cause:** The mod package could not be created. This occurs when ZIP/JAR packaging fails or invalid files are included.

**Fix:**
1. Verify sufficient disk space is available
2. Check that no files have invalid characters in names
3. Ensure the output path is writable

**Workaround:** Retry the packaging operation.

---

### ERR_PACKAGE_002: INVALID_ARCHIVE

**Category:** Package Error
**HTTP Status:** 422
**Retryable:** No

**Cause:** The created archive is invalid. This can happen with corrupted ZIP files or unsupported compression methods.

**Fix:**
1. Use standard ZIP compression (deflate)
2. Avoid password-protected archives
3. Verify with a ZIP validator tool

**Workaround:** Use a different compression tool to create the archive.

---

## Validation Errors

### ERR_VALID_001: VALIDATION_ERROR

**Category:** Validation Error
**HTTP Status:** 422
**Retryable:** No

**Cause:** Input validation failed. The provided mod file or parameters do not meet requirements.

**Fix:**
1. Check that file type is supported (.jar for Java mods)
2. Verify file size is within limits
3. Ensure the file is not corrupted or empty

**Workaround:** Upload a valid, non-corrupted mod file.

---

### ERR_VALID_002: INVALID_FILE

**Category:** Validation Error
**HTTP Status:** 400
**Retryable:** No

**Cause:** The uploaded file is not a valid mod file. May be wrong format, corrupted, or not a mod at all.

**Fix:**
1. Verify file extension is `.jar`
2. Check file magic bytes match ZIP/JAR format
3. Ensure the file is a real Minecraft mod

**Workaround:** Convert the file to proper JAR format if it originates from another platform.

---

### ERR_VALID_003: INVALID_FILE_TYPE

**Category:** Validation Error
**HTTP Status:** 400
**Retryable:** No

**Cause:** File type is not supported. Portkit only accepts Java mod JAR files.

**Fix:**
1. Upload a `.jar` file for Java mods
2. Bedrock addons should use the appropriate upload endpoint
3. Check that the file has proper MIME type

**Workaround:** None for this error type.

---

### ERR_VALID_004: FILE_TOO_LARGE

**Category:** Validation Error
**HTTP Status:** 413
**Retryable:** No

**Cause:** The uploaded file exceeds size limits. Limits vary by tier.

**Fix:**
1. Check file size against tier limits
2. Consider upgrading to a higher tier
3. Remove unnecessary files from the mod package

**Workaround:** Split large mods into smaller modules.

---

## Network Errors

### ERR_NETWORK_001: NETWORK_ERROR

**Category:** Network Error
**HTTP Status:** 503
**Retryable:** Yes

**Cause:** Network connectivity issues. Could not reach required services.

**Fix:**
1. Check internet connection stability
2. Verify firewall/proxy settings
3. Ensure DNS resolution works

**Workaround:** Retry when connectivity improves.

---

### ERR_NETWORK_002: CONNECTION_REFUSED

**Category:** Network Error
**HTTP Status:** 503
**Retryable:** Yes

**Cause:** Connection was refused by the target service. The AI engine or conversion service may be down.

**Fix:**
1. Check service status page for outages
2. Wait and retry; transient issues resolve quickly
3. Contact support if persistent

**Workaround:** Use cached results if available.

---

### ERR_NETWORK_003: HOST_UNREACHABLE

**Category:** Network Error
**HTTP Status:** 503
**Retryable:** Yes

**Cause:** Host is unreachable. Network routing or DNS issues.

**Fix:**
1. Verify the service URL is correct
2. Check local network configuration
3. Try alternative network (VPN, etc.)

**Workaround:** Wait for network issues to resolve.

---

## Rate Limit Errors

### ERR_RATE_001: RATE_LIMIT_ERROR

**Category:** Rate Limit Error
**HTTP Status:** 429
**Retryable:** Yes

**Cause:** Too many requests. Rate limit exceeded for your tier.

**Fix:**
1. Wait for the rate limit window to reset
2. Upgrade to a higher tier for more requests
3. Implement request batching if applicable

**Workaround:** Use exponential backoff when retrying.

---

### ERR_RATE_002: QUOTA_EXCEEDED

**Category:** Rate Limit Error
**HTTP Status:** 429
**Retryable:** No

**Cause:** Monthly or yearly quota has been exhausted.

**Fix:**
1. Check quota usage in dashboard
2. Upgrade tier for additional quota
3. Wait for quota reset (monthly/annual)

**Workaround:** None until quota resets.

---

## Timeout Errors

### ERR_TIMEOUT_001: CONVERSION_TIMEOUT

**Category:** Timeout Error
**HTTP Status:** 408
**Retryable:** Yes

**Cause:** Conversion took too long and was terminated. Large or complex mods may exceed timeout limits.

**Fix:**
1. Reduce mod complexity before conversion
2. Split large mods into smaller parts
3. Upgrade to a tier with longer timeout limits

**Workaround:** Retry; smaller mods convert faster.

---

### ERR_TIMEOUT_002: REQUEST_TIMEOUT

**Category:** Timeout Error
**HTTP Status:** 408
**Retryable:** Yes

**Cause:** API request timed out waiting for response.

**Fix:**
1. Check network latency to API endpoint
2. Reduce request payload size
3. Use async polling instead of waiting for callback

**Workaround:** Retry with smaller requests.

---

## Unknown Errors

### ERR_UNKNOWN_001: UNKNOWN_ERROR

**Category:** Unknown Error
**HTTP Status:** 500
**Retryable:** No

**Cause:** An unexpected error occurred that could not be classified. This is a catch-all for errors that don't match other categories.

**Fix:**
1. Note the error ID from the response
2. Report to support with error ID and timestamp
3. Include request payload if possible

**Workaround:** None. This requires investigation.

---

### ERR_UNKNOWN_002: INTERNAL_ERROR

**Category:** Unknown Error
**HTTP Status:** 500
**Retryable:** No

**Cause:** An internal server error occurred. This typically indicates a bug or unexpected condition server-side.

**Fix:**
1. Note the error ID from the response
2. Wait and retry; the issue may have been transient
3. Report to support if persistent

**Workaround:** Retry after waiting.

---

## HTTP Errors

### ERR_HTTP_001: HTTP_ERROR

**Category:** HTTP Error
**HTTP Status:** 502
**Retryable:** Yes

**Cause:** Bad gateway or proxy error. The service handling your request failed.

**Fix:**
1. Retry the request
2. Check if the underlying service is healthy
3. Contact support if persistent

**Workaround:** Retry after brief delay.

---

### ERR_HTTP_002: NOT_FOUND

**Category:** HTTP Error
**HTTP Status:** 404
**Retryable:** No

**Cause:** The requested resource was not found. This may be a mod ID that doesn't exist or a deleted conversion.

**Fix:**
1. Verify the resource ID is correct
2. Check that the resource hasn't been deleted
3. List available resources if applicable

**Workaround:** None; resource does not exist.

---

### ERR_HTTP_003: METHOD_NOT_ALLOWED

**Category:** HTTP Error
**HTTP Status:** 405
**Retryable:** No

**Cause:** HTTP method not supported for this endpoint.

**Fix:**
1. Check API documentation for correct method
2. Ensure proper REST conventions are followed
3. Verify endpoint supports the operation type

**Workaround:** Use correct HTTP method.

---

## File Processing Errors

### ERR_FILE_001: FILE_PROCESSING_ERROR

**Category:** File Processing Error
**HTTP Status:** 400
**Retryable:** Yes

**Cause:** Error during file processing. Could be reading, writing, or analyzing the file.

**Fix:**
1. Verify file is not corrupted
2. Check file permissions
3. Ensure sufficient disk space

**Workaround:** Retry with a fresh copy of the file.

---

### ERR_FILE_002: INVALID_JAR

**Category:** File Processing Error
**HTTP Status:** 400
**Retryable:** No

**Cause:** File is not a valid Java JAR archive.

**Fix:**
1. Verify file is a valid JAR using `jar -tf <file.jar>`
2. Check that file has proper ZIP structure
3. Ensure file is not password-protected

**Workaround:** Re-download or re-export the mod file.

---

### ERR_FILE_003: READ_ERROR

**Category:** File Processing Error
**HTTP Status:** 500
**Retryable:** Yes

**Cause:** Error reading from storage. Could be disk failure, permissions, or concurrent access issues.

**Fix:**
1. Check file permissions
2. Verify disk health
3. Ensure no conflicting processes

**Workaround:** Retry; transient read errors may resolve.

---

## Feature Errors

### ERR_FEATURE_001: FEATURE_DISABLED

**Category:** Feature Error
**HTTP Status:** 403
**Retryable:** No

**Cause:** The requested feature is not enabled for your tier or account.

**Fix:**
1. Check feature availability for your tier
2. Upgrade to a tier that supports the feature
3. Contact sales for feature enablement

**Workaround:** Use alternative features if available.

---

### ERR_FEATURE_002: TIER_REQUIRED

**Category:** Feature Error
**HTTP Status:** 403
**Retryable:** No

**Cause:** Feature requires a specific tier but your account is on a lower tier.

**Fix:**
1. Review tier comparison page
2. Upgrade to required tier
3. Wait for tier change to take effect

**Workaround:** Use equivalent feature from your current tier if available.

---

## Error Response Format

All error responses follow this structure:

```json
{
  "error_id": "a1b2c3d4",
  "error_code": "ERR_CATEGORY_001",
  "error_type": "validation_error",
  "error_category": "validation_error",
  "message": "Technical error message for debugging",
  "user_message": "User-friendly error message",
  "is_retryable": true,
  "timestamp": "2026-05-16T10:30:00Z",
  "path": "/api/v1/conversions",
  "method": "POST",
  "details": {},
  "correlation_id": "xyz789"
}
```

**Fields:**
- `error_id`: Unique 8-character ID for tracking
- `error_code`: Machine-readable error code
- `error_type`: Error type category (from exception class)
- `error_category`: Normalized error category
- `message`: Technical details for debugging (hidden in production if DEBUG=false)
- `user_message`: Safe message to display to users
- `is_retryable`: Whether the operation can be safely retried
- `timestamp`: ISO 8601 timestamp
- `path`: API endpoint path
- `method`: HTTP method
- `details`: Additional context (hidden if DEBUG=false)
- `correlation_id`: Request correlation ID for log tracing

## Retry Guidelines

**Retryable errors** (is_retryable: true):
- NETWORK_ERROR - Network connectivity issues often transient
- RATE_LIMIT_ERROR - Wait and retry with backoff
- CONVERSION_TIMEOUT - May succeed on retry with same timeout
- PACKAGE_ERROR - Transient packaging issues

**Non-retryable errors** (is_retryable: false):
- VALIDATION_ERROR - Fix input first, then retry
- INVALID_FILE - Upload correct file
- LOGIC_ERROR - Requires code fix
- FEATURE_DISABLED - Upgrade tier or wait

## Getting Help

If you encounter an error not listed here:
1. Note the `error_id` from the response
2. Check the [Status Page](https://status.portkit.dev) for outages
3. Contact support with error_id and timestamp