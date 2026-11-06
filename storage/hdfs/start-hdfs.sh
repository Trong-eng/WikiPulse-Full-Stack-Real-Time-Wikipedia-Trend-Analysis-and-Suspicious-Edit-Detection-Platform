#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  namenode)
    name_dir="${HDFS_NAME_DIR:-/data/hdfs/name}"
    mkdir -p "$name_dir"
    if [[ ! -f "$name_dir/current/VERSION" ]]; then
      if [[ -n "$(find "$name_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
        echo 'Refusing to format nonempty NameNode storage without current/VERSION' >&2
        exit 1
      fi
      hdfs namenode -format -nonInteractive
    fi
    exec hdfs namenode
    ;;
  datanode)
    exec hdfs datanode
    ;;
  *)
    echo 'Usage: start-hdfs.sh namenode|datanode' >&2
    exit 2
    ;;
esac
