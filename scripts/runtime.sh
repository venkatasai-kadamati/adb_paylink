#!/usr/bin/env bash
# Prefer tested Homebrew runtimes without changing the user's global PATH.
if [[ "$(uname -s)" == Darwin ]]; then
  for prefix in /opt/homebrew /usr/local; do
    if [[ -d "$prefix/opt/node@24/bin" ]]; then
      export PATH="$prefix/opt/node@24/bin:$PATH"
      break
    fi
  done
fi
