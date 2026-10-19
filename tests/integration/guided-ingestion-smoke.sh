#!/usr/bin/env bash
# CI-only, disposable end-to-end test: raw Tenrai-shaped JSON -> SQL -> Web API.
# It must never run on a user's real Mangadvisor database or personal files.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" ]] || ! grep -qx 'POSTGRES_DB=mangadvisor_ci' .env; then
  echo "REFUS: test reserve a GitHub Actions et a la base mangadvisor_ci." >&2
  exit 2
fi

BASE=(docker compose --env-file .env -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.local.yml)
search_file="data/raw/jikan/search/search_page_99991.json"
top_file="data/raw/jikan/top/top_manga_page_99991.json"
reco_file="data/raw/jikan/recommendations/manga_987654321_recommendations.json"
for file in "$search_file" "$top_file" "$reco_file"; do
  if [[ -e "$file" ]]; then
    echo "REFUS: fichier de test preexistant : $file" >&2
    exit 2
  fi
done
cleanup() { rm -f "$search_file" "$top_file" "$reco_file"; }
trap cleanup EXIT

python3 - <<'PY'
import json
from pathlib import Path

def store(name, obj):
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

def manga(mal_id, title):
    return {
        "mal_id": mal_id,
        "title": title,
        "title_english": title,
        "title_japanese": None,
        "synopsis": "Fictional CI manga for an isolated integration test.",
        "status": "Finished",
        "type": "Manga",
        "chapters": 12,
        "volumes": 3,
        "score": 8.1,
        "genres": [{"mal_id": 1, "name": "Action"}],
        "themes": [{"mal_id": 2, "name": "Adventure"}],
        "demographics": [{"mal_id": 3, "name": "Shounen"}],
        "authors": [],
        "serializations": [],
    }

store("data/raw/jikan/search/search_page_99991.json", {
    "mangadvisor_source": "tenrai",
    "data": [manga(987654321, "Mangadvisor CI Smoke Alpha")]
})
store("data/raw/jikan/top/top_manga_page_99991.json", {
    "mangadvisor_source": "tenrai",
    "data": [manga(987654322, "Mangadvisor CI Smoke Beta")]
})
store("data/raw/jikan/recommendations/manga_987654321_recommendations.json", {
    "mangadvisor_source": "tenrai",
    "data": [{
        "entry": {"mal_id": 987654322, "title": "Mangadvisor CI Smoke Beta"},
        "votes": 7
    }]
})
PY

# The engine image contains only the versioned code; JSON persists by the raw-data mount.
"${BASE[@]}" build engine
load_and_link() {
  "${BASE[@]}" run --rm engine python pipelines/engine/scripts/load_jikan_to_postgres.py --sources search top
  for source in sql/schema/003_build_canonical_from_jikan.sql sql/schema/004_add_theme_demographic_tables.sql sql/schema/005_build_theme_demographic_from_jikan.sql; do
    "${BASE[@]}" exec -T postgres psql -X -v ON_ERROR_STOP=1 -U manga_ci -d mangadvisor_ci < "$source"
  done
  "${BASE[@]}" run --rm engine python pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py
}
load_and_link

query_counts() {
  "${BASE[@]}" exec -T postgres psql -X -At -v ON_ERROR_STOP=1 -U manga_ci -d mangadvisor_ci -c "
SELECT
  (SELECT count(*) FROM jikan_manga_source WHERE mal_id IN (987654321,987654322)) || '|' ||
  (SELECT count(*) FROM manga WHERE source_mal_id IN (987654321,987654322) AND source_name='tenrai') || '|' ||
  (SELECT count(*) FROM manga_genre mg JOIN manga m ON m.id=mg.manga_id WHERE m.source_mal_id IN (987654321,987654322)) || '|' ||
  (SELECT count(*) FROM manga_theme mt JOIN manga m ON m.id=mt.manga_id WHERE m.source_mal_id IN (987654321,987654322)) || '|' ||
  (SELECT count(*) FROM manga_demographic md JOIN manga m ON m.id=md.manga_id WHERE m.source_mal_id IN (987654321,987654322)) || '|' ||
  (SELECT count(*) FROM manga_recommendation_edge r JOIN manga s ON r.source_manga_id=s.id JOIN manga t ON r.recommended_manga_id=t.id WHERE s.source_mal_id=987654321 AND t.source_mal_id=987654322 AND r.votes=7);
"
}
counts="$(query_counts)"
if [[ "$counts" != '2|2|2|2|2|1' ]]; then
  echo "ERREUR: chaine ingestion incomplet: $counts" >&2
  exit 1
fi
echo "Premier chargement SQL valide: $counts"

# A re-import must preserve the canonical ID and user library link.
"${BASE[@]}" exec -T postgres psql -X -v ON_ERROR_STOP=1 -U manga_ci -d mangadvisor_ci -c "
INSERT INTO user_manga_library (user_id,manga_id,library_status,owned_volumes)
SELECT 1,id,'OWNED',3 FROM manga WHERE source_mal_id=987654321
ON CONFLICT (user_id,manga_id) DO NOTHING;
"
before="$("${BASE[@]}" exec -T postgres psql -X -At -U manga_ci -d mangadvisor_ci -c 'SELECT manga_id FROM user_manga_library WHERE user_id=1 AND manga_id=(SELECT id FROM manga WHERE source_mal_id=987654321);')"
load_and_link
after="$("${BASE[@]}" exec -T postgres psql -X -At -U manga_ci -d mangadvisor_ci -c 'SELECT manga_id FROM user_manga_library WHERE user_id=1 AND manga_id=(SELECT id FROM manga WHERE source_mal_id=987654321);')"
if [[ -z "$before" || "$before" != "$after" || "$(query_counts)" != '2|2|2|2|2|1' ]]; then
  echo "ERREUR: une re-ingestion a casse les liens ou cree des doublons." >&2
  exit 1
fi

python3 - <<'PY'
import json
from urllib.parse import urlencode
from urllib.request import urlopen

url = "http://127.0.0.1:8501/api/mangas?" + urlencode({"q": "Mangadvisor CI Smoke", "limit": 10})
with urlopen(url, timeout=15) as reply:
    payload = json.load(reply)
items = payload.get("items") if isinstance(payload, dict) else None
if not isinstance(items, list):
    raise AssertionError("L'API Web ne renvoie pas de liste d'oeuvres.")
by_id = {item["source_mal_id"]: item for item in items}
if 987654321 not in by_id or 987654322 not in by_id:
    raise AssertionError("Les mangas du pipeline SQL sont introuvables sur le site Web.")
print("API Web valide: les deux mangas de test sont consultables.")
PY
echo "SUCCES: chaine JSON -> SQL -> recommandations -> bibliotheque -> Web, sans doublons."
