#!/usr/bin/env bash

if command -v playwright > /dev/null 2>&1; then
  playwright install-deps
  playwright install chromium
fi
