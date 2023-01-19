#!/bin/sh

BASEDIR="$(dirname "$0")"
RUNNER="$(realpath "$BASEDIR/run.sh")"

echo "55 * * * * /usr/bin/flock --nonblock \"/tmp/lock.teto-archiver\" $RUNNER"
