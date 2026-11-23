"""Bảo vệ test Docker: chỉ kết nối broker loopback thuộc project test đã chọn."""

import subprocess


def verify_broker(project, broker):
    if not project.startswith("wikipulse-thanh-w3-"):
        raise ValueError("invalid test project")
    host, separator, port = broker.rpartition(":")
    if not separator or host != "127.0.0.1" or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("test broker must be loopback")
    container = f"{project}-kafka-1"
    label = subprocess.run(["docker", "inspect", "--format",
                            '{{index .Config.Labels "com.docker.compose.project"}}', container],
                           capture_output=True, text=True, check=True).stdout.strip()
    ports = subprocess.run(["docker", "port", container, "19092/tcp"],
                           capture_output=True, text=True, check=True).stdout.splitlines()
    if label != project or f"127.0.0.1:{port}" not in ports:
        raise ValueError("broker does not belong to test project")
