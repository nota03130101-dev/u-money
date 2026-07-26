# U Money Security

## Scope

U Money stores cloud records in Supabase and provides optional AI features through `ai-service`.

## Secret handling

- Never place model API keys, Supabase `service_role` keys, passwords, tokens, certificates, or deployment credentials in browser code, GitHub, CSV exports, feedback, or screenshots.
- The frontend may contain a Supabase publishable key. This is public configuration, not an administrator key; it is safe only when Supabase RLS is correctly configured.
- Production secrets belong only in the deployment platform's server-side environment variables.

## AI production requirements

- Set `APP_ENV=production` and `MOCK_MODE=false`.
- Configure a model API key, model name, Supabase URL, Supabase publishable key, `LOG_HASH_KEY`, and explicit HTTPS `ALLOWED_ORIGINS`.
- The service refuses to start in production when required settings are missing, when Mock mode is enabled, or when CORS is open to every origin.
- Limit AI parsing to 5 requests per minute and 30 per day per user in the current process. A future multi-instance deployment needs shared rate limiting.

## Database isolation

The application relies on Supabase Row Level Security (RLS) for cloud records. On 2026-07-26, the `records` table policies were checked and two test accounts confirmed that each account can select, insert, update, and delete only its own rows.

The verified policy baseline is stored in [supabase/records_rls.sql](supabase/records_rls.sql). Before changing live policies, first save the current policy output, compare it with this file, and test with two non-sensitive accounts again.

## Reporting a vulnerability

Do not report security issues in a public issue with secrets or personal data. Send the repository owner a short private description, affected area, and safe reproduction steps without including passwords, tokens, or real financial records.
