# Continue Portkit Smoke Test Investigation

## Background
Running smoke tests on portkit.cloud (production) and staging.portkit.cloud (staging).

## What's Been Done
1. ✅ Added TLS certificate for staging.portkit.cloud
2. ✅ Started both staging worker machines (18530d0a990d98 and e7845d23f92183)
3. ✅ Production passed 15/15 tests (100%)

## Previous Smoke Test Results
**Production:** 15/15 PASSED (100%)

**Staging:** 12/15 PASSED (80%)
- Failed tests were related to conversion pipeline (workers were stopped):
  - Conversion Progress: Progress not updating properly
  - Conversion Completion: Timeout waiting for completion
  - Conversion History: Status 500

## Task
1. Run the smoke tests again on staging to verify the worker machines are now processing conversions
2. If tests still fail, investigate:
   - Check worker logs: `fly logs -a portkit-backend-staging --machine 18530d0a990d98`
   - Check worker logs: `fly logs -a portkit-backend-staging --machine e7845d23f92183`
   - Verify Redis connection on workers
   - Check if conversion jobs are being picked up from the queue

3. Report final test results