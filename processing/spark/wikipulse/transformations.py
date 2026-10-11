"""Built-in Spark expressions for the week-one event and activity contracts."""

from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DateType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

RAW_EVENT_SCHEMA = StructType(
    [
        StructField("meta", StructType([
            StructField("id", StringType()),
            StructField("dt", StringType()),
            StructField("domain", StringType()),
        ])),
        StructField("timestamp", LongType()),
        StructField("id", LongType()),
        StructField("wiki", StringType()),
        StructField("title", StringType()),
        StructField("type", StringType()),
        StructField("page_id", LongType()),
        StructField("namespace", IntegerType()),
        StructField("revision", StructType([
            StructField("old", LongType()), StructField("new", LongType()),
        ])),
        StructField("length", StructType([
            StructField("old", LongType()), StructField("new", LongType()),
        ])),
        StructField("user", StringType()),
        StructField("anon", BooleanType()),
        StructField("bot", BooleanType()),
        StructField("minor", BooleanType()),
        StructField("ingested_at", StringType()),
        StructField("collector_version", StringType()),
        StructField("_corrupt_record", StringType()),
    ]
)

SILVER_SCHEMA = StructType(
    [
        StructField("event_id", StringType()),
        StructField("event_time", TimestampType()),
        StructField("ingested_at", TimestampType()),
        StructField("processed_at", TimestampType()),
        StructField("wiki", StringType()),
        StructField("domain", StringType()),
        StructField("page_title", StringType()),
        StructField("event_type", StringType()),
        StructField("user_hash", StringType()),
        StructField("page_id", LongType()),
        StructField("revision_old", LongType()),
        StructField("revision_new", LongType()),
        StructField("length_old", LongType()),
        StructField("length_new", LongType()),
        StructField("byte_delta", LongType()),
        StructField("namespace", IntegerType()),
        StructField("is_anonymous", BooleanType()),
        StructField("is_bot", BooleanType()),
        StructField("is_minor", BooleanType()),
        StructField("kafka_topic", StringType()),
        StructField("kafka_partition", IntegerType()),
        StructField("kafka_offset", LongType()),
        StructField("pipeline_version", StringType()),
        StructField("event_date", DateType()),
        StructField("event_hour", IntegerType()),
    ]
)


def parse_events(kafka_df):
    envelope = kafka_df.select(
        F.col("value").cast("string").alias("raw_payload"),
        F.col("topic").alias("kafka_topic"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.col("timestamp").alias("kafka_timestamp"),
    )
    parsed = envelope.withColumn(
        "_document",
        F.from_json("raw_payload", RAW_EVENT_SCHEMA, {
            "mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_corrupt_record"
        }),
    ).withColumn(
        "_event_time",
        F.coalesce(F.to_timestamp("_document.meta.dt"), F.timestamp_seconds("_document.timestamp")),
    ).withColumn("_wiki", F.lower(F.trim("_document.wiki"))).withColumn(
        "_page_title", F.trim("_document.title")
    )
    return parsed.withColumn(
        "error_code",
        F.when(
            F.col("_document").isNull() | F.col("_document._corrupt_record").isNotNull(),
            F.lit("INVALID_JSON"),
        ).when(F.col("_event_time").isNull(), F.lit("MISSING_EVENT_TIME"))
        .when(F.col("_wiki").isNull() | (F.length("_wiki") == 0), F.lit("MISSING_WIKI"))
        .when(
            (F.col("_page_title").isNull() | (F.length("_page_title") == 0))
            & F.col("_document.page_id").isNull(),
            F.lit("MISSING_PAGE"),
        ),
    )


def bronze_rows(parsed_df, pipeline_version):
    partition_time = F.coalesce("_event_time", "kafka_timestamp", F.current_timestamp())
    return parsed_df.select(
        "raw_payload", "kafka_topic", "kafka_partition", "kafka_offset", "kafka_timestamp",
        F.coalesce(
            F.to_timestamp("_document.ingested_at"), "kafka_timestamp", F.current_timestamp()
        ).alias("ingested_at"),
        F.lit(pipeline_version).alias("pipeline_version"),
        F.to_date(partition_time).alias("event_date"),
        F.hour(partition_time).alias("event_hour"),
    )


def invalid_rows(parsed_df):
    return parsed_df.filter(F.col("error_code").isNotNull()).select(
        "raw_payload", "error_code", "kafka_topic", "kafka_partition", "kafka_offset",
        "kafka_timestamp", F.current_timestamp().alias("detected_at"),
        F.to_date(F.coalesce("_event_time", "kafka_timestamp", F.current_timestamp()))
        .alias("event_date"),
        F.hour(F.coalesce("_event_time", "kafka_timestamp", F.current_timestamp()))
        .alias("event_hour"),
    )


def normalize_events(parsed_df, settings):
    domain = F.lower(F.trim("_document.meta.domain"))
    valid = parsed_df.filter(
        F.col("error_code").isNull()
        & F.col("_wiki").isin(list(settings.wiki_allowlist))
        & (F.coalesce(domain, F.lit("")) != "canary")
    )
    normalized = valid.select(
        F.col("_event_time").alias("event_time"),
        F.coalesce(
            F.to_timestamp("_document.ingested_at"), "kafka_timestamp", F.current_timestamp()
        ).alias("ingested_at"),
        F.current_timestamp().alias("processed_at"),
        F.col("_wiki").alias("wiki"),
        domain.alias("domain"),
        F.col("_page_title").alias("page_title"),
        F.coalesce(F.lower(F.trim("_document.type")), F.lit("unknown")).alias("event_type"),
        F.sha2(F.concat(
            F.lit(settings.user_hash_salt + "|"), F.coalesce("_document.user", F.lit(""))
        ), 256).alias("user_hash"),
        F.col("_document.page_id").alias("page_id"),
        F.col("_document.revision.old").alias("revision_old"),
        F.col("_document.revision.new").alias("revision_new"),
        F.col("_document.length.old").alias("length_old"),
        F.col("_document.length.new").alias("length_new"),
        (F.col("_document.length.new") - F.col("_document.length.old")).alias("byte_delta"),
        F.col("_document.namespace").alias("namespace"),
        F.coalesce(
            "_document.anon",
            F.coalesce("_document.user", F.lit("")).rlike(
                r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|^[0-9A-Fa-f]*:[0-9A-Fa-f:]+$"
            ),
        ).alias("is_anonymous"),
        F.coalesce("_document.bot", F.lit(False)).alias("is_bot"),
        F.coalesce("_document.minor", F.lit(False)).alias("is_minor"),
        "kafka_topic", "kafka_partition", "kafka_offset",
        F.lit(settings.pipeline_version).alias("pipeline_version"),
        F.to_date("_event_time").alias("event_date"),
        F.hour("_event_time").alias("event_hour"),
        F.trim("_document.meta.id").alias("_source_id"),
        F.col("_document.id").alias("_recentchange_id"),
    )
    fallback = F.sha2(F.to_json(F.struct(
        "wiki", "page_id", "page_title", "revision_new",
        F.date_format("event_time", "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'").alias("event_time"),
        "event_type", F.col("_recentchange_id").alias("recentchange_id"),
    ), {"ignoreNullFields": "false"}), 256)
    return normalized.withColumn(
        "event_id", F.when(F.length("_source_id") > 0, F.col("_source_id")).otherwise(fallback)
    ).select(SILVER_SCHEMA.fieldNames())


def deduplicate_events(normalized_df, watermark_delay):
    # Within-watermark ID dedup also catches duplicates with slightly changed timestamps.
    return normalized_df.withWatermark("event_time", watermark_delay).dropDuplicatesWithinWatermark(
        ["event_id"]
    )


def activity_windows(silver_df, watermark_delay):
    is_edit = F.col("event_type") == "edit"
    activity = silver_df.withWatermark("event_time", watermark_delay).groupBy(
        "wiki", F.window("event_time", "1 minute")
    ).agg(
        F.count("*").alias("event_count"),
        F.sum(F.when(is_edit, 1).otherwise(0)).cast("long").alias("edit_count"),
        F.sum(F.when(F.col("event_type") == "new", 1).otherwise(0))
        .cast("long").alias("new_page_count"),
        F.sum(F.when(is_edit & F.col("is_anonymous"), 1).otherwise(0))
        .cast("long").alias("anonymous_edit_count"),
        F.sum(F.when(is_edit & F.col("is_bot"), 1).otherwise(0))
        .cast("long").alias("bot_edit_count"),
    )
    return activity.select(
        "wiki", F.col("window.start").alias("window_start"),
        F.col("window.end").alias("window_end"), "event_count", "edit_count", "new_page_count",
        "anonymous_edit_count", "bot_edit_count", F.current_timestamp().alias("updated_at"),
    )


def gold_rows(activity_df):
    return activity_df.withColumn("metric_date", F.to_date("window_start")).withColumn(
        "metric_hour", F.hour("window_start")
    )
