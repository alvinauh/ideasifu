#!/usr/bin/env bash
# Launch the IdeaSifu stack (standalone; does not touch thesissifu/thesiscoach).
#
# Reads GROQ_API_KEY + OPENROUTER_API_KEY from the kuasaprestij .env at launch
# and passes them into compose as environment variables — no secret is written
# into the IdeaSifu project. Empty keys => backend serves graceful mock data.
set -euo pipefail
cd "$(dirname "$0")"

KUASA_ENV="/root/kuasaprestij/.env"
if [[ -f "$KUASA_ENV" ]]; then
	GROQ_API_KEY="$(grep -E '^GROQ_API_KEY=' "$KUASA_ENV" | head -1 | cut -d= -f2-)"
	OPENROUTER_API_KEY="$(grep -E '^OPENROUTER_API_KEY=' "$KUASA_ENV" | head -1 | cut -d= -f2-)"
	export GROQ_API_KEY OPENROUTER_API_KEY
else
	echo "WARN: $KUASA_ENV not found — starting in mock mode." >&2
fi

[[ -z "${GROQ_API_KEY:-}" ]] && echo "WARN: GROQ_API_KEY is empty." >&2
[[ -z "${OPENROUTER_API_KEY:-}" ]] && echo "WARN: OPENROUTER_API_KEY is empty." >&2

docker compose up -d --build

echo
echo "IdeaSifu is up:"
echo "  UI      -> http://localhost:8004"
echo "  API docs-> http://localhost:8005/docs"
echo "  health  -> http://localhost:8005/health"
