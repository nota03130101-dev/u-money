-- U Money records table RLS baseline
-- Verified manually on 2026-07-26 with two test accounts.
-- This file is not executed automatically. Before applying it to an existing
-- project, first compare the current policies in Supabase SQL Editor.

alter table public.records enable row level security;

drop policy if exists "Users can view own records" on public.records;
drop policy if exists "Users can insert own records" on public.records;
drop policy if exists "Users can update own records" on public.records;
drop policy if exists "Users can delete own records" on public.records;

create policy "Users can view own records"
on public.records
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can insert own records"
on public.records
for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can update own records"
on public.records
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users can delete own records"
on public.records
for delete
to authenticated
using ((select auth.uid()) = user_id);
