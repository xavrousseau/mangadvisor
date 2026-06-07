from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from load.postgres_loader import get_postgres_connection  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = PROJECT_ROOT / "docs" / "reports"
REPORT_PATH = REPORT_DIR / "jikan_recommendation_edges_diagnostic.md"


PROFILES: list[dict[str, Any]] = [
    {
        "name": "Shōnen aventure / combat",
        "liked_titles": ["Naruto", "Bleach", "Hunter x Hunter"],
    },
    {
        "name": "Thriller psychologique / mystère",
        "liked_titles": ["Death Note", "Monster", "20th Century Boys"],
    },
    {
        "name": "Seinen sombre / violent / mature",
        "liked_titles": ["Berserk", "Blame!", "Battle Royale"],
    },
    {
        "name": "Romance / drame / personnages",
        "liked_titles": ["Nana", "Paradise Kiss", "Lovely★Complex"],
    },
    {
        "name": "Sport / dépassement de soi",
        "liked_titles": ["Hajime no Ippo", "Slam Dunk", "Eyeshield 21"],
    },
    {
        "name": "Aventure longue / monde vaste",
        "liked_titles": ["One Piece", "Hunter x Hunter", "Fullmetal Alchemist"],
    },
    {
        "name": "Mystère / surnaturel",
        "liked_titles": ["Death Note", "Bleach", "xxxHOLiC"],
    },
    {
        "name": "Tranche de vie / contemplatif",
        "liked_titles": ["Yokohama Kaidashi Kikou", "Mushishi", "Natsume Yuujinchou"],
    },
]


def get_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, dict):
        return row[key]

    return row[index]


def fetch_one(conn, sql: str, params: tuple[Any, ...] | None = None) -> Any:
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone()


def fetch_all(conn, sql: str, params: tuple[Any, ...] | None = None) -> list[Any]:
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def get_global_stats(conn) -> dict[str, Any]:
    sql = """
        SELECT
            COUNT(*) AS total_edges,
            COUNT(recommended_manga_id) AS linked_edges,
            COUNT(*) - COUNT(recommended_manga_id) AS unlinked_edges,
            COUNT(DISTINCT source_manga_id) AS source_manga_count,
            COUNT(DISTINCT recommended_mal_id) AS recommended_mal_count,
            SUM(COALESCE(votes, 0)) AS total_votes
        FROM manga_recommendation_edge;
    """

    row = fetch_one(conn, sql)

    total_edges = get_value(row, "total_edges", 0) or 0
    linked_edges = get_value(row, "linked_edges", 1) or 0

    linked_rate = 0.0

    if total_edges:
        linked_rate = linked_edges / total_edges * 100

    return {
        "total_edges": total_edges,
        "linked_edges": linked_edges,
        "unlinked_edges": get_value(row, "unlinked_edges", 2) or 0,
        "source_manga_count": get_value(row, "source_manga_count", 3) or 0,
        "recommended_mal_count": get_value(row, "recommended_mal_count", 4) or 0,
        "total_votes": get_value(row, "total_votes", 5) or 0,
        "linked_rate": linked_rate,
    }


def get_top_edges(conn, limit: int = 30) -> list[dict[str, Any]]:
    sql = """
        SELECT
            sm.title AS source_title,
            e.recommended_title,
            rm.title AS linked_catalog_title,
            e.votes,
            sm.score AS source_score,
            rm.score AS recommended_score
        FROM manga_recommendation_edge e
        JOIN manga sm
            ON sm.id = e.source_manga_id
        LEFT JOIN manga rm
            ON rm.id = e.recommended_manga_id
        ORDER BY
            COALESCE(e.votes, 0) DESC,
            sm.title ASC,
            e.recommended_title ASC
        LIMIT %s;
    """

    rows = fetch_all(conn, sql, (limit,))

    result = []

    for row in rows:
        result.append(
            {
                "source_title": get_value(row, "source_title", 0),
                "recommended_title": get_value(row, "recommended_title", 1),
                "linked_catalog_title": get_value(row, "linked_catalog_title", 2),
                "votes": get_value(row, "votes", 3),
                "source_score": get_value(row, "source_score", 4),
                "recommended_score": get_value(row, "recommended_score", 5),
            }
        )

    return result


def get_unlinked_top_recommendations(conn, limit: int = 30) -> list[dict[str, Any]]:
    sql = """
        SELECT
            recommended_mal_id,
            recommended_title,
            COUNT(*) AS source_count,
            SUM(COALESCE(votes, 0)) AS total_votes
        FROM manga_recommendation_edge
        WHERE recommended_manga_id IS NULL
        GROUP BY
            recommended_mal_id,
            recommended_title
        ORDER BY
            total_votes DESC NULLS LAST,
            source_count DESC,
            recommended_title ASC
        LIMIT %s;
    """

    rows = fetch_all(conn, sql, (limit,))

    result = []

    for row in rows:
        result.append(
            {
                "recommended_mal_id": get_value(row, "recommended_mal_id", 0),
                "recommended_title": get_value(row, "recommended_title", 1),
                "source_count": get_value(row, "source_count", 2),
                "total_votes": get_value(row, "total_votes", 3),
            }
        )

    return result


def get_profile_sources(conn, liked_titles: list[str]) -> list[dict[str, Any]]:
    """
    Récupère les sources du profil.

    Si plusieurs œuvres ont le même titre, on ne garde qu'une seule ligne,
    en préférant :
    1. Manga
    2. Manhwa / Manhua
    3. One-shot
    4. Light Novel
    5. autres types
    """
    normalized_titles = [title.lower() for title in liked_titles]

    sql = """
        WITH matched_sources AS (
            SELECT
                id,
                title,
                source_mal_id,
                score,
                popularity,
                manga_type,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(title)
                    ORDER BY
                        CASE
                            WHEN manga_type = 'Manga' THEN 0
                            WHEN manga_type IN ('Manhwa', 'Manhua') THEN 1
                            WHEN manga_type = 'One-shot' THEN 2
                            WHEN manga_type = 'Light Novel' THEN 5
                            ELSE 9
                        END,
                        popularity ASC NULLS LAST,
                        score DESC NULLS LAST,
                        id ASC
                ) AS rn
            FROM manga
            WHERE LOWER(title) = ANY(%s)
        )
        SELECT
            id,
            title,
            source_mal_id,
            score,
            popularity
        FROM matched_sources
        WHERE rn = 1
        ORDER BY
            popularity ASC NULLS LAST,
            title ASC;
    """

    rows = fetch_all(conn, sql, (normalized_titles,))

    result = []

    for row in rows:
        result.append(
            {
                "id": get_value(row, "id", 0),
                "title": get_value(row, "title", 1),
                "source_mal_id": get_value(row, "source_mal_id", 2),
                "score": get_value(row, "score", 3),
                "popularity": get_value(row, "popularity", 4),
            }
        )

    return result


def get_profile_community_candidates(
    conn,
    source_ids: list[int],
    limit: int = 15,
) -> list[dict[str, Any]]:
    if not source_ids:
        return []

    sql = """
        SELECT
            COALESCE(rm.title, e.recommended_title) AS candidate_title,
            e.recommended_mal_id,
            e.recommended_manga_id,
            COUNT(DISTINCT e.source_manga_id) AS source_count,
            SUM(COALESCE(e.votes, 0)) AS total_votes,
            MAX(rm.score) AS candidate_score,
            MIN(rm.popularity) AS candidate_popularity,
            ARRAY_AGG(DISTINCT sm.title ORDER BY sm.title) AS recommended_from
        FROM manga_recommendation_edge e
        JOIN manga sm
            ON sm.id = e.source_manga_id
        LEFT JOIN manga rm
            ON rm.id = e.recommended_manga_id
        WHERE e.source_manga_id = ANY(%s)
          AND (
                e.recommended_manga_id IS NULL
                OR e.recommended_manga_id <> ALL(%s)
          )
        GROUP BY
            COALESCE(rm.title, e.recommended_title),
            e.recommended_mal_id,
            e.recommended_manga_id
        ORDER BY
            source_count DESC,
            total_votes DESC NULLS LAST,
            candidate_popularity ASC NULLS LAST,
            candidate_title ASC
        LIMIT %s;
    """

    rows = fetch_all(conn, sql, (source_ids, source_ids, limit))

    result = []

    for row in rows:
        result.append(
            {
                "candidate_title": get_value(row, "candidate_title", 0),
                "recommended_mal_id": get_value(row, "recommended_mal_id", 1),
                "recommended_manga_id": get_value(row, "recommended_manga_id", 2),
                "source_count": get_value(row, "source_count", 3),
                "total_votes": get_value(row, "total_votes", 4),
                "candidate_score": get_value(row, "candidate_score", 5),
                "candidate_popularity": get_value(row, "candidate_popularity", 6),
                "recommended_from": get_value(row, "recommended_from", 7) or [],
            }
        )

    return result


def fmt(value: Any) -> str:
    if value is None:
        return ""

    return str(value)


def fmt_float(value: Any, decimals: int = 1) -> str:
    if value is None:
        return ""

    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def write_report() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_postgres_connection()

    try:
        stats = get_global_stats(conn)
        top_edges = get_top_edges(conn, limit=30)
        unlinked = get_unlinked_top_recommendations(conn, limit=30)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines: list[str] = [
            "# Mangadvisor — Diagnostic recommandations communautaires Jikan",
            "",
            f"Date d’exécution : `{now}`",
            "",
            "## 1. Synthèse globale",
            "",
            "| Indicateur | Valeur |",
            "|---|---:|",
            f"| Edges totales | {stats['total_edges']} |",
            f"| Edges liées au catalogue | {stats['linked_edges']} |",
            f"| Edges hors catalogue | {stats['unlinked_edges']} |",
            f"| Taux de liaison catalogue | {stats['linked_rate']:.1f}% |",
            f"| Mangas sources avec recommandations | {stats['source_manga_count']} |",
            f"| Mangas recommandés distincts | {stats['recommended_mal_count']} |",
            f"| Votes totaux | {stats['total_votes']} |",
            "",
            "## 2. Top recommandations communautaires",
            "",
            "| Source | Recommandation | Dans catalogue | Votes | Score reco catalogue |",
            "|---|---|---|---:|---:|",
        ]

        for edge in top_edges:
            linked_title = edge["linked_catalog_title"] or ""
            in_catalog = "Oui" if linked_title else "Non"

            lines.append(
                "| "
                f"{fmt(edge['source_title'])} | "
                f"{fmt(edge['recommended_title'])} | "
                f"{in_catalog} | "
                f"{fmt(edge['votes'])} | "
                f"{fmt_float(edge['recommended_score'], 2)} |"
            )

        lines.extend(
            [
                "",
                "## 3. Recommandations fréquentes hors catalogue",
                "",
                "Ces titres sont recommandés par la communauté Jikan, mais ne sont pas encore présents dans notre catalogue canonique.",
                "Ils sont de bons candidats pour enrichir automatiquement la base plus tard.",
                "",
                "| MAL ID | Titre | Sources | Votes totaux |",
                "|---:|---|---:|---:|",
            ]
        )

        for item in unlinked:
            lines.append(
                "| "
                f"{fmt(item['recommended_mal_id'])} | "
                f"{fmt(item['recommended_title'])} | "
                f"{fmt(item['source_count'])} | "
                f"{fmt(item['total_votes'])} |"
            )

        lines.extend(
            [
                "",
                "## 4. Analyse par profil de test",
                "",
            ]
        )

        for profile in PROFILES:
            profile_name = profile["name"]
            liked_titles = profile["liked_titles"]
            sources = get_profile_sources(conn, liked_titles)
            source_ids = [int(source["id"]) for source in sources]
            candidates = get_profile_community_candidates(conn, source_ids, limit=15)

            recognized_titles = set(source["title"].lower() for source in sources)
            missing_titles = [
                title for title in liked_titles if title.lower() not in recognized_titles
            ]

            lines.extend(
                [
                    f"### {profile_name}",
                    "",
                    f"**Mangas demandés :** {', '.join(liked_titles)}",
                    "",
                    f"**Sources reconnues :** {', '.join(source['title'] for source in sources) if sources else '_Aucune_'}",
                    "",
                ]
            )

            if missing_titles:
                lines.extend(
                    [
                        f"**Sources non reconnues :** {', '.join(missing_titles)}",
                        "",
                    ]
                )

            if not candidates:
                lines.extend(
                    [
                        "_Aucun candidat communautaire trouvé pour ce profil._",
                        "",
                    ]
                )
                continue

            lines.extend(
                [
                    "| Rang | Candidat | Dans catalogue | Sources | Votes | Recommandé depuis | Score | Popularité |",
                    "|---:|---|---|---:|---:|---|---:|---:|",
                ]
            )

            for index, candidate in enumerate(candidates, start=1):
                in_catalog = "Oui" if candidate["recommended_manga_id"] else "Non"
                recommended_from = ", ".join(candidate["recommended_from"])

                lines.append(
                    "| "
                    f"{index} | "
                    f"{fmt(candidate['candidate_title'])} | "
                    f"{in_catalog} | "
                    f"{fmt(candidate['source_count'])} | "
                    f"{fmt(candidate['total_votes'])} | "
                    f"{recommended_from} | "
                    f"{fmt_float(candidate['candidate_score'], 2)} | "
                    f"{fmt(candidate['candidate_popularity'])} |"
                )

            lines.append("")

        lines.extend(
            [
                "## 5. Décisions possibles",
                "",
                "À partir de ce diagnostic, on pourra décider :",
                "",
                "- si le signal communautaire est assez dense pour être utilisé dans le moteur ;",
                "- quels titres hors catalogue doivent être ajoutés en priorité ;",
                "- si un bonus communautaire doit être ajouté au score de recommandation ;",
                "- si un manga recommandé par plusieurs sources aimées doit recevoir un bonus fort ;",
                "- si les recommandations hors catalogue doivent déclencher un enrichissement automatique.",
                "",
            ]
        )

        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    finally:
        conn.close()


def main() -> int:
    print("==================================================")
    print("Mangadvisor - Diagnostic recommandations Jikan")
    print("==================================================")
    print(f"Rapport : {REPORT_PATH}")
    print()

    write_report()

    print("Diagnostic terminé.")
    print(f"Rapport généré : {REPORT_PATH}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())