/* NOTES:
 * - This script is run every time the app starts up.
 * - Timestamps are unix millisecond epochs.
 * - AUTOINCREMENT for id's are not needed.
 * - users.upstream_id is stored as bytes, not a hex string.
 * - stats.country and stats.username are stats, since they can be changed by the user to effect standings.
 * - stats.country is an ISO 3166-1 country code, with additional vanity flags. Can be disabled by the user.
 * - rating, glicko, rd, apm, pps and vs could be NULL if the player is unranked.
 * - rating might come as -1 in the api instead of being non-existent or null.
 * - fetches.created_at DEFAULT expression is from https://stackoverflow.com/a/32789171
 */

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS fetches (
    id INTEGER NOT NULL PRIMARY KEY,
    created_at INT NOT NULL DEFAULT (CAST(ROUND((julianday('now') - 2440587.5)*86400000) As INT)),
    success INT NOT NULL,
    error TEXT,
    cache_status TEXT,
    cached_at INT,
    cached_until INT
) STRICT;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL PRIMARY KEY,
    upstream_id BLOB NOT NULL UNIQUE,
    role TEXT NOT NULL,
    bestrank TEXT NOT NULL,
    supporter INT NOT NULL,
    verified INT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS stats (
    id INTEGER NOT NULL PRIMARY KEY,
    fetch_id INT NOT NULL REFERENCES fetches (id),
    user_id INT NOT NULL REFERENCES users (id),
    username TEXT NOT NULL,
    country TEXT,
    rank TEXT NOT NULL,
    decaying INT NOT NULL,
    xp REAL NOT NULL,
    gamesplayed INT NOT NULL,
    gameswon INT NOT NULL,
    rating REAL,
    glicko REAL,
    rd REAL,
    apm REAL,
    pps REAL,
    vs REAL
) STRICT;
