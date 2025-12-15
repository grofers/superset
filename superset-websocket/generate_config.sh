#!/bin/bash

# Fetch values from environment variables or set defaults
PORT="${PORT:-8080}"
LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_TO_FILE="${LOG_TO_FILE:-false}"
LOG_FILENAME="${LOG_FILENAME:-app.log}"
STATSD_HOST="${STATSD_HOST:-127.0.0.1}"
STATSD_PORT="${STATSD_PORT:-8125}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
REDIS_DB="${REDIS_DB:-0}"
REDIS_SSL="${REDIS_SSL:-false}"
REDIS_STREAM_PREFIX="${REDIS_STREAM_PREFIX:-async-events-}"
JWT_ALGORITHMS="${JWT_ALGORITHMS:-HS256}"
JWT_SECRET="${JWT_SECRET:-change-me}"
JWT_COOKIE_NAME="${JWT_COOKIE_NAME:-async-token}"
PING_SOCKETS_INTERVAL_MS="${PING_SOCKETS_INTERVAL_MS:-20000}"
SOCKET_RESPONSE_TIMEOUT_MS="${SOCKET_RESPONSE_TIMEOUT_MS:-60000}"
GC_CHANNELS_INTERVAL_MS="${GC_CHANNELS_INTERVAL_MS:-120000}"

# Create JSON config
jq -n --arg port "$PORT" \
      --arg logLevel "$LOG_LEVEL" \
      --argjson logToFile "$LOG_TO_FILE" \
      --arg logFilename "$LOG_FILENAME" \
      --arg statsdHost "$STATSD_HOST" \
      --arg statsdPort "$STATSD_PORT" \
      --arg redisHost "$REDIS_HOST" \
      --arg redisPort "$REDIS_PORT" \
      --arg redisPassword "$REDIS_PASSWORD" \
      --argjson redisDb "$REDIS_DB" \
      --argjson redisSsl "$REDIS_SSL" \
      --arg redisStreamPrefix "$REDIS_STREAM_PREFIX" \
      --arg jwtAlgorithms "$JWT_ALGORITHMS" \
      --arg jwtSecret "$JWT_SECRET" \
      --arg jwtCookieName "$JWT_COOKIE_NAME" \
      --argjson pingSocketsIntervalMs "$PING_SOCKETS_INTERVAL_MS" \
      --argjson socketResponseTimeoutMs "$SOCKET_RESPONSE_TIMEOUT_MS" \
      --argjson gcChannelsIntervalMs "$GC_CHANNELS_INTERVAL_MS" \
      '{
        port: $port | tonumber,
        logLevel: $logLevel,
        logToFile: $logToFile,
        logFilename: $logFilename,
        statsd: {
          host: $statsdHost,
          port: $statsdPort | tonumber,
          globalTags: []
        },
        redis: {
          port: $redisPort | tonumber,
          host: $redisHost,
          password: $redisPassword,
          db: $redisDb | tonumber,
          ssl: $redisSsl,
        },
        redisStreamPrefix: $redisStreamPrefix,
        jwtAlgorithms: [$jwtAlgorithms],
        jwtSecret: $jwtSecret,
        jwtCookieName: $jwtCookieName,
        pingSocketsIntervalMs: $pingSocketsIntervalMs | tonumber,
        socketResponseTimeoutMs: $socketResponseTimeoutMs | tonumber,
        gcChannelsIntervalMs: $gcChannelsIntervalMs | tonumber
      }' > config.json

echo "Configuration has been written to config.json"

gosu node pnpm start
