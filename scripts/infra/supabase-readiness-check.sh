#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL_DIRECT:?DATABASE_URL_DIRECT is required}"
: "${SUPABASE_PROJECT_REF:?SUPABASE_PROJECT_REF is required}"

for bin in psql supabase; do
  command -v "$bin" >/dev/null 2>&1 || {
    printf '%s is required\n' "$bin" >&2
    exit 1
  }
done

psql_query() {
  psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 -Atc "$1"
}

for ext in postgis pg_trgm pgcrypto; do
  if [[ "$(psql_query "select exists(select 1 from pg_extension where extname = '$ext');")" != "t" ]]; then
    printf 'missing required extension: %s\n' "$ext" >&2
    exit 1
  fi
done

if [[ "${ALLOW_EXTRA_DB_EXTENSIONS:-0}" != "1" ]]; then
  forbidden="$(psql_query "select string_agg(extname, ',') from pg_extension where extname in ('timescaledb','vector','h3');")"
  if [[ -n "$forbidden" ]]; then
    printf 'forbidden extension(s) installed without ALLOW_EXTRA_DB_EXTENSIONS=1: %s\n' "$forbidden" >&2
    exit 1
  fi
fi

service_bypass="$(psql_query "select coalesce((select rolbypassrls::text from pg_roles where rolname = 'service_role'), 'missing');")"
if [[ "$service_bypass" != "true" ]]; then
  printf 'service_role must exist and bypass RLS; got %s\n' "$service_bypass" >&2
  exit 1
fi

realtime_messages="$(psql_query "select to_regclass('realtime.messages') is not null;")"
if [[ "$realtime_messages" != "t" ]]; then
  echo 'realtime.messages table is missing' >&2
  exit 1
fi

storage_buckets="$(psql_query "select to_regclass('storage.buckets') is not null;")"
if [[ "$storage_buckets" != "t" ]]; then
  echo 'storage.buckets table is missing' >&2
  exit 1
fi

missing_buckets="$(psql_query "with required(id) as (values ('evidence'), ('merchant-qr'), ('exports')) select string_agg(required.id, ',') from required left join storage.buckets b on b.id = required.id where b.id is null;")"
if [[ -n "$missing_buckets" ]]; then
  printf 'missing storage bucket(s): %s\n' "$missing_buckets" >&2
  exit 1
fi

echo ok
