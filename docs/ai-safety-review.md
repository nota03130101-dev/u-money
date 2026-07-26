# U Money AI Safety Review

Date: 2026-07-26

## Review scope

This review covers the local frontend, FastAPI AI service, prompt files, tests, local Git history, and a manual two-account verification of the live `records` RLS policies. It does not claim that a future deployment platform has been verified.

## Addressed in code

- Model API keys are read only from server-side environment variables.
- The frontend contains no `service_role` key.
- Production refuses to start with Mock mode, missing model or Supabase settings, missing log hash key, wildcard CORS, or non-HTTPS CORS origins.
- AI parsing is limited per user by a short window and a daily window in the current process.
- AI responses have request and model timeouts, input validation, schema validation, and `Cache-Control: no-store`.
- AI drafts require user confirmation before the existing frontend writes records to Supabase.
- Users can disable AI locally without disabling ordinary manual accounting.
- Server logs are designed to exclude full accounting text, notes, email addresses, access tokens, and model API keys.
- Frontend messages no longer display raw Supabase error text.
- Supabase `records` RLS policies were manually reviewed for select, insert, update, and delete. Two test accounts confirmed they cannot view each other's records.

## Remaining release checks

1. Configure production secrets only in the AI hosting platform; never commit them.
2. Configure the exact public AI service URL in the frontend and add it to the production CORS allow list.
3. Confirm the model provider's retention, privacy, spending limit, and alert settings.
4. Use an HTTPS deployment with a request-body limit at the reverse proxy or hosting platform. Application validation does not replace platform-level request limits.
5. Review the external Supabase browser library loading policy before public release.

## Test evidence

The Python test suite covers authentication presence, structured AI output, invalid model output, timeouts, monthly-summary limits, and input validation. The live account A/B RLS check was completed manually with non-sensitive test records.
