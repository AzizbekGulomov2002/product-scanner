#!/bin/bash
# Umumiy local env o'zgaruvchilari

export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
