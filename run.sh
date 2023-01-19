#!/bin/sh

BASEDIR="$(dirname "$0")"
MAIN="$BASEDIR/main.py"
ERROUT="$(mktemp --suffix ".teto-archiver")"

for _ in $(seq 3); do
	if "$MAIN" 2> "$ERROUT"; then
		break
	else
		WAIT_TIME="$(tail -n 1 "$ERROUT")"
		echo "Command failed. Trying again in $WAIT_TIME seconds."
		sleep "$WAIT_TIME"
	fi
done

rm "$ERROUT"
