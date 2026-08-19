#!/usr/bin/env bash
# Launch the IdeaSifu stack (standalone; does not touch thesissifu/thesiscoach).
#
# Reads GROQ_API_KEY and GEMINI_API_KEY from the kuasaprestij .env at launch
# and passes them into compose as environment variables — no secret is written
# into the IdeaSifu project.
# Empty keys => backend serves graceful mock data (Pro tier falls back to free).
set -euo pipefail
cd "$(dirname "$0")"

KUASA_ENV="/root/kuasaprestij/.env"
if [[ -f "$KUASA_ENV" ]]; then
	GROQ_API_KEY="$(grep -E '^GROQ_API_KEY=' "$KUASA_ENV" | head -1 | cut -d= -f2-)"
	GEMINI_API_KEY="$(grep -E '^GEMINI_API_KEY=' "$KUASA_ENV" | head -1 | cut -d= -f2-)"
	export GROQ_API_KEY GEMINI_API_KEY
else
	echo "WARN: $KUASA_ENV not found — starting in mock mode." >&2
fi

[[ -z "${GROQ_API_KEY:-}" ]] && echo "WARN: GROQ_API_KEY is empty." >&2
[[ -z "${GEMINI_API_KEY:-}" ]] && echo "WARN: GEMINI_API_KEY is empty — Pro tier will fall back to free models." >&2

# Build the frontend SPA first — the web Docker image just COPYs dist/, so
# the JS must be compiled on the host before the image is rebuilt.
echo "Building frontend..."
(cd frontend && VITE_API_BASE_URL=/api npm run build)

docker compose up -d --build

echo
echo "IdeaSifu is up:"
echo "  UI      -> http://localhost:8004"
echo "  API docs-> http://localhost:8005/docs"
echo "  health  -> http://localhost:8005/health"
