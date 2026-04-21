-- Apply after 0001_init.sql and after deploying the daily_trigger Edge Function.
-- Run this in the Supabase SQL editor (pg_cron jobs are stored in cron.job).

-- 07:00 UTC daily. Adjust to your timezone offset if you want local 7am.
select
  cron.schedule(
    'paper_breaker_daily_digest',
    '0 7 * * *',
    $$
    select net.http_post(
      url := (select decrypted_secret from vault.decrypted_secrets
              where name = 'DAILY_TRIGGER_FN_URL'),
      headers := jsonb_build_object('Content-Type', 'application/json'),
      body := '{}'::jsonb
    );
    $$
  );

-- Unschedule with:
--   select cron.unschedule('paper_breaker_daily_digest');
