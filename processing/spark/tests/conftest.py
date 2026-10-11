import os

import pytest


@pytest.fixture(scope="session")
def spark():
    pytest.importorskip("pyspark", reason="Run Spark tests in the Python3.11/Java17 image")
    from pyspark.sql import SparkSession

    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    session = (
        SparkSession.builder.master("local[2]")
        .appName("wikipulse-cp0-tests")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
