CREATE KEYSPACE IF NOT EXISTS __KEYSPACE__
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS __KEYSPACE__.wiki_activity_by_window (
    wiki text,
    window_start timestamp,
    window_end timestamp,
    event_count bigint,
    edit_count bigint,
    new_page_count bigint,
    anonymous_edit_count bigint,
    bot_edit_count bigint,
    updated_at timestamp,
    PRIMARY KEY ((wiki), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);

-- Contract v0.2 (W2-NHAN-01). One partition per wiki and 5-minute window; top-N reads it whole.
CREATE TABLE IF NOT EXISTS __KEYSPACE__.page_trends_by_window (
    wiki text,
    window_start timestamp,
    page_key text,
    window_end timestamp,
    page_title text,
    namespace int,
    edit_count bigint,
    unique_editors bigint,
    abs_byte_delta bigint,
    trend_score double,
    updated_at timestamp,
    PRIMARY KEY ((wiki, window_start), page_key)
);

-- Windows that have trend rows, newest first, so "latest" needs no table scan.
CREATE TABLE IF NOT EXISTS __KEYSPACE__.trend_windows_by_wiki (
    wiki text,
    window_start timestamp,
    updated_at timestamp,
    PRIMARY KEY ((wiki), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);

CREATE TABLE IF NOT EXISTS __KEYSPACE__.suspicious_edits_by_bucket (
    wiki text,
    bucket_start timestamp,
    event_id text,
    event_time timestamp,
    page_key text,
    page_title text,
    revision_new bigint,
    byte_delta bigint,
    is_anonymous boolean,
    is_bot boolean,
    risk_score int,
    risk_reasons set<text>,
    updated_at timestamp,
    PRIMARY KEY ((wiki, bucket_start), event_id)
);

CREATE TABLE IF NOT EXISTS __KEYSPACE__.suspicious_buckets_by_wiki (
    wiki text,
    bucket_start timestamp,
    updated_at timestamp,
    PRIMARY KEY ((wiki), bucket_start)
) WITH CLUSTERING ORDER BY (bucket_start DESC);

-- Serving lookup only; Bronze/Silver keep the full history. TTL 7 days (W3-NHAN-01).
CREATE TABLE IF NOT EXISTS __KEYSPACE__.events_by_id (
    event_id text PRIMARY KEY,
    wiki text,
    event_time timestamp,
    page_key text,
    page_title text,
    namespace int,
    event_type text,
    revision_old bigint,
    revision_new bigint,
    length_old bigint,
    length_new bigint,
    byte_delta bigint,
    is_anonymous boolean,
    is_bot boolean,
    is_minor boolean,
    risk_score int,
    risk_reasons set<text>,
    pipeline_version text,
    processed_at timestamp
) WITH default_time_to_live = 604800;
