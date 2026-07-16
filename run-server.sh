#!/bin/bash
# Django server
# Ishlatish: ./run-server.sh

cd "$(dirname "$0")"
exec ./scripts/local-run.sh "$@"
