"""Built-in Spark expressions for the v0.2 producer interfaces."""

from pyspark.sql import functions as F

from processing.spark.wikipulse.scoring import RISK_REASONS, TREND_FEATURES


def with_page_key(frame):
    return frame.withColumn("page_key", F.coalesce(
        F.col("page_id").cast("string"), F.concat(F.lit("title:"), F.col("page_title"))
    ))


def score_events(silver, config):
    edit = F.col("event_type") == "edit"
    matches = {
        "LARGE_DELETION": edit & (F.col("byte_delta") <= -config.large_deletion_bytes),
        "REVERT_PATTERN": edit & F.col("is_revert"),
        "ANONYMOUS_EDIT": edit & F.col("is_anonymous") & ~F.col("is_bot"),
    }
    reasons = F.filter(F.array(*[
        F.when(matches[name], F.lit(name)) for name in RISK_REASONS
    ]), lambda value: value.isNotNull())
    score = sum(F.when(matches[name], config.risk_weights[name]).otherwise(0)
                for name in RISK_REASONS)
    return with_page_key(silver).withColumn("risk_reasons", reasons).withColumn(
        "risk_score", F.least(score, F.lit(config.max_score)).cast("int")
    )


def suspicious_edits(scored):
    return scored.filter((F.col("event_type") == "edit") & (F.col("risk_score") > 0)).select(
        "wiki", "event_id", "page_key", "page_title",
        F.date_trunc("minute", "event_time").alias("bucket_start"), "event_time",
        F.current_timestamp().alias("updated_at"), "revision_new", "byte_delta",
        "is_anonymous", "is_bot", "risk_score", "risk_reasons",
    )


def event_details(scored):
    return scored.select(
        "event_id", "wiki", "event_time", "page_key", "page_title", "namespace", "event_type",
        "revision_old", "revision_new", "length_old", "length_new", "byte_delta",
        "is_anonymous", "is_bot", "is_minor", "risk_score", "risk_reasons",
        "pipeline_version", "processed_at",
    )


def trend_windows(silver, watermark_delay, config):
    edits = with_page_key(silver).filter(F.col("event_type") == "edit")
    grouped = edits.withWatermark("event_time", watermark_delay).groupBy(
        "wiki", "page_key", F.window("event_time", "5 minutes", "1 minute")
    ).agg(
        F.count("*").alias("edit_count"),
        F.approx_count_distinct("user_hash").alias("unique_editors"),
        F.coalesce(F.sum(F.abs(F.col("byte_delta"))), F.lit(0)).cast("long")
        .alias("abs_byte_delta"),
        # Stable latest metadata even when arrival order or retry batch boundaries change.
        F.max(F.struct("event_time", "event_id", "page_title", "namespace")).alias("_latest"),
    )
    score = sum(F.lit(config.trend_weights[name]) * F.least(
        F.col(name).cast("double") / F.lit(config.normalization_caps[name]), F.lit(1.0)
    ) for name in TREND_FEATURES)
    return grouped.select(
        "wiki", "page_key", F.col("_latest.page_title").alias("page_title"),
        F.col("_latest.namespace").alias("namespace"),
        F.col("window.start").alias("window_start"), F.col("window.end").alias("window_end"),
        "edit_count", "unique_editors", "abs_byte_delta", score.cast("double").alias("trend_score"),
        F.current_timestamp().alias("updated_at"),
    )
