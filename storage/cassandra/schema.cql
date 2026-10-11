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
