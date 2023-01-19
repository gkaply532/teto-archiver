#!/usr/bin/env python3

# TODO(gkm): Make with statement usage more readable in main.
# TODO(gkm): We are currently reading the stream twice, we can instead
# read through the stream once assuming "success" is the first thing
# in the stream.

import sqlite3
import math
import sys
from tempfile import TemporaryFile
from contextlib import closing
from datetime import datetime, timedelta, timezone

import ijson
import httpx


def merge_user(user):
    u = user
    l = user["league"]
    return {
        "upstream_id": bytes.fromhex(u["_id"]),
        "xp": u["xp"],
        "username": u["username"],
        "role": u["role"],
        "supporter": u["supporter"],
        "verified": u["verified"],
        "country": u["country"],
        "rank": l["rank"],
        "gamesplayed": l["gamesplayed"],
        "gameswon": l["gameswon"],
        "rating": l["rating"],
        "glicko": l["glicko"],
        "rd": l["rd"],
        "apm": l["apm"],
        "pps": l["pps"],
        "vs": l["vs"],
        "bestrank": l["bestrank"],
        "decaying": l["decaying"],
    }

def upsert_user(cur, merged):
    cur.execute(
        """
            INSERT INTO users (
                upstream_id, /* unique */ role, bestrank, supporter, verified
            ) VALUES (
                :upstream_id, :role, :bestrank, :supporter, :verified
            ) ON CONFLICT (upstream_id) DO UPDATE SET
                role = :role, bestrank = :bestrank,
                supporter = :supporter,verified = :verified
        """,
        merged
    )

def insert_stat(cur, merged):
    cur.execute(
        """
            INSERT INTO stats (
                fetch_id, user_id, username, country, rank, decaying,
                xp, gamesplayed, gameswon, rating, glicko, rd, apm, pps, vs
            )
            SELECT
                :fetch_id, id /* user_id */, :username, :country, :rank, :decaying,
                :xp, :gamesplayed, :gameswon, :rating, :glicko, :rd, :apm, :pps, :vs
            FROM users
            WHERE upstream_id = :upstream_id
        """,
        merged
    )

def skip_data(events):
    for event in events:
        if not event[0].startswith("data"):
            yield event

def main():
    with open("init.sql", "r") as f:
        script = f.read()

    with closing(sqlite3.connect("data.db")) as con, con:
        with closing(con.cursor()) as cur, con:
            cur.executescript(script)

        with closing(con.cursor()) as cur, con:
            result = cur.execute("SELECT cached_until FROM fetches ORDER BY id DESC LIMIT 1")
            row = result.fetchone()
            if row is not None:
                cached_until = row[0]

                valid_time = datetime.fromtimestamp(cached_until / 1000, timezone.utc)
                now = datetime.now(timezone.utc)
                if not now > valid_time:
                    wait_time = valid_time - now
                    wait_secs = math.ceil(wait_time.total_seconds())
                    print(
                        "The most recent fetch has not expired yet.",
                        f"It will expire in: {wait_time}",
                        "Or in seconds:",
                        wait_secs,
                        file=sys.stderr,
                        sep="\n",
                    )
                    sys.exit(1)

        with TemporaryFile() as tmp:
            timeout = timedelta(minutes=5)
            with httpx.stream("GET", "https://ch.tetr.io/api/users/lists/league/all", timeout=timeout.total_seconds()) as response:
                for data in response.iter_bytes():
                    tmp.write(data)
                    print(f"Total download: {response.num_bytes_downloaded / 1024} KiB...")

            tmp.seek(0)
            # FIXME(gkm): Abstract into a function.
            export = next(ijson.items(skip_data(ijson.parse(tmp, use_float=True)), ""))
            tmp.seek(0)
            users = ijson.items(tmp, "data.users.item", use_float=True)

            with closing(con.cursor()) as cur, con:
                success = export.get("success", False)
                cur.execute("INSERT INTO fetches (success) VALUES (?)", (success,))
                fetch_id = cur.lastrowid

                if error := export.get("error"):
                    cur.execute("UPDATE fetches SET error = ? WHERE id = ?", (error, fetch_id))

                if cache := export.get("cache"):
                    cur.execute(
                        "UPDATE fetches SET cache_status = ?, cached_at = ?, cached_until = ? WHERE id = ?",
                        (
                            cache.get("status"),
                            cache.get("cached_at"),
                            cache.get("cached_until"),
                            fetch_id
                        )
                    )

                for user in users:
                    merged = merge_user(user) | {"fetch_id": fetch_id}
                    upsert_user(cur, merged)
                    insert_stat(cur, merged)

if __name__ == "__main__":
    main()
