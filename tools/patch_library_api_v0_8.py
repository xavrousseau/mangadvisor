from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"


MODELS_BLOCK = '''
LibraryStatus = Literal[
    "OWNED",
    "READING",
    "READ",
    "WANT_TO_READ",
    "DROPPED",
    "NOT_INTERESTED",
]


class LibraryItemRequest(BaseModel):
    manga_id: int = Field(
        ...,
        ge=1,
        description="Identifiant interne Mangadvisor du manga.",
    )
    library_status: LibraryStatus = Field(
        ...,
        description="Statut du manga dans la bibliothèque utilisateur.",
    )
    user_score: float | None = Field(
        default=None,
        ge=0,
        le=10,
        description="Note utilisateur optionnelle entre 0 et 10.",
    )
    is_favorite: bool = Field(
        default=False,
        description="Indique si le manga est un favori.",
    )
    owned_volumes: int | None = Field(
        default=None,
        ge=0,
        description="Nombre de volumes possédés.",
    )
    read_volumes: int | None = Field(
        default=None,
        ge=0,
        description="Nombre de volumes lus.",
    )
    notes: str | None = Field(
        default=None,
        description="Notes personnelles.",
    )
    started_at: str | None = Field(
        default=None,
        description="Date de début de lecture au format YYYY-MM-DD.",
    )
    finished_at: str | None = Field(
        default=None,
        description="Date de fin de lecture au format YYYY-MM-DD.",
    )


class LibraryRecommendationRequest(BaseModel):
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Nombre de recommandations à retourner.",
    )
    min_score: float = Field(
        default=6.8,
        ge=0,
        le=10,
        description="Score minimum du manga recommandé.",
    )
    only_finished: bool = Field(
        default=False,
        description="Si true, recommande uniquement des mangas terminés.",
    )
    exclude_sensitive_mismatches: bool = Field(
        default=False,
        description="Si true, exclut les mangas avec éléments éloignants.",
    )
'''


ENDPOINTS_BLOCK = '''
DEFAULT_USER_ID = 1


def validate_library_status(status: str | None) -> str | None:
    if status is None:
        return None

    allowed_statuses = {
        "OWNED",
        "READING",
        "READ",
        "WANT_TO_READ",
        "DROPPED",
        "NOT_INTERESTED",
    }

    normalized_status = status.strip().upper()

    if normalized_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Statut bibliothèque invalide. Valeurs autorisées : "
                + ", ".join(sorted(allowed_statuses))
            ),
        )

    return normalized_status


def fetch_library_item(
    manga_id: int,
    user_id: int = DEFAULT_USER_ID,
) -> dict[str, Any] | None:
    sql = """
        SELECT
            l.id,
            l.user_id,
            l.manga_id,
            l.library_status,
            l.user_score::float AS user_score,
            l.is_favorite,
            l.owned_volumes,
            l.read_volumes,
            l.notes,
            l.started_at::text AS started_at,
            l.finished_at::text AS finished_at,
            l.created_at::text AS created_at,
            l.updated_at::text AS updated_at,

            m.source_mal_id,
            m.title,
            m.title_english,
            m.title_japanese,
            m.status,
            m.manga_type,
            m.score::float AS manga_score,
            m.popularity,
            m.rank,
            m.members,
            m.favorites,
            m.volumes,
            m.chapters,

            COALESCE(
                array_remove(array_agg(DISTINCT g.name ORDER BY g.name), NULL),
                ARRAY[]::text[]
            ) AS genres,

            COALESCE(
                array_remove(array_agg(DISTINCT t.name ORDER BY t.name), NULL),
                ARRAY[]::text[]
            ) AS themes,

            COALESCE(
                array_remove(array_agg(DISTINCT d.name ORDER BY d.name), NULL),
                ARRAY[]::text[]
            ) AS demographics

        FROM user_manga_library l

        JOIN manga m
            ON m.id = l.manga_id

        LEFT JOIN manga_genre mg
            ON mg.manga_id = m.id
        LEFT JOIN genre g
            ON g.id = mg.genre_id

        LEFT JOIN manga_theme mt
            ON mt.manga_id = m.id
        LEFT JOIN theme t
            ON t.id = mt.theme_id

        LEFT JOIN manga_demographic md
            ON md.manga_id = m.id
        LEFT JOIN demographic d
            ON d.id = md.demographic_id

        WHERE l.user_id = %(user_id)s
          AND l.manga_id = %(manga_id)s

        GROUP BY
            l.id,
            l.user_id,
            l.manga_id,
            l.library_status,
            l.user_score,
            l.is_favorite,
            l.owned_volumes,
            l.read_volumes,
            l.notes,
            l.started_at,
            l.finished_at,
            l.created_at,
            l.updated_at,

            m.id,
            m.source_mal_id,
            m.title,
            m.title_english,
            m.title_japanese,
            m.status,
            m.manga_type,
            m.score,
            m.popularity,
            m.rank,
            m.members,
            m.favorites,
            m.volumes,
            m.chapters;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "user_id": user_id,
                    "manga_id": manga_id,
                },
            )
            return cur.fetchone()


@app.get("/library")
def get_library(
    status: str | None = Query(
        default=None,
        description="Filtre optionnel : READ, READING, OWNED, WANT_TO_READ, DROPPED, NOT_INTERESTED.",
    ),
    q: str | None = Query(
        default=None,
        description="Recherche optionnelle par titre dans la bibliothèque.",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """
    Liste la bibliothèque de l'utilisateur local.

    V0.8 :
    - pas encore d'authentification ;
    - utilisateur local fixe : user_id = 1.
    """
    normalized_status = validate_library_status(status)

    params: dict[str, Any] = {
        "user_id": DEFAULT_USER_ID,
        "limit": limit,
        "offset": offset,
    }

    filters = ["l.user_id = %(user_id)s"]

    if normalized_status:
        filters.append("l.library_status = %(library_status)s")
        params["library_status"] = normalized_status

    if q:
        filters.append(
            """
            (
                m.title ILIKE %(q)s
                OR m.title_english ILIKE %(q)s
                OR m.title_japanese ILIKE %(q)s
            )
            """
        )
        params["q"] = f"%{q}%"

    where_clause = " AND ".join(filters)

    sql = f"""
        SELECT
            l.id,
            l.user_id,
            l.manga_id,
            l.library_status,
            l.user_score::float AS user_score,
            l.is_favorite,
            l.owned_volumes,
            l.read_volumes,
            l.notes,
            l.started_at::text AS started_at,
            l.finished_at::text AS finished_at,
            l.created_at::text AS created_at,
            l.updated_at::text AS updated_at,

            m.source_mal_id,
            m.title,
            m.title_english,
            m.status,
            m.manga_type,
            m.score::float AS manga_score,
            m.popularity,
            m.volumes,
            m.chapters,

            COALESCE(
                array_remove(array_agg(DISTINCT g.name ORDER BY g.name), NULL),
                ARRAY[]::text[]
            ) AS genres,

            COALESCE(
                array_remove(array_agg(DISTINCT t.name ORDER BY t.name), NULL),
                ARRAY[]::text[]
            ) AS themes,

            COALESCE(
                array_remove(array_agg(DISTINCT d.name ORDER BY d.name), NULL),
                ARRAY[]::text[]
            ) AS demographics

        FROM user_manga_library l

        JOIN manga m
            ON m.id = l.manga_id

        LEFT JOIN manga_genre mg
            ON mg.manga_id = m.id
        LEFT JOIN genre g
            ON g.id = mg.genre_id

        LEFT JOIN manga_theme mt
            ON mt.manga_id = m.id
        LEFT JOIN theme t
            ON t.id = mt.theme_id

        LEFT JOIN manga_demographic md
            ON md.manga_id = m.id
        LEFT JOIN demographic d
            ON d.id = md.demographic_id

        WHERE {where_clause}

        GROUP BY
            l.id,
            l.user_id,
            l.manga_id,
            l.library_status,
            l.user_score,
            l.is_favorite,
            l.owned_volumes,
            l.read_volumes,
            l.notes,
            l.started_at,
            l.finished_at,
            l.created_at,
            l.updated_at,

            m.id,
            m.source_mal_id,
            m.title,
            m.title_english,
            m.status,
            m.manga_type,
            m.score,
            m.popularity,
            m.volumes,
            m.chapters

        ORDER BY
            l.updated_at DESC,
            m.title ASC

        LIMIT %(limit)s
        OFFSET %(offset)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return {
        "user_id": DEFAULT_USER_ID,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "items": rows,
    }


@app.post("/library/items")
def upsert_library_item(payload: LibraryItemRequest) -> dict[str, Any]:
    """
    Ajoute ou met à jour un manga dans la bibliothèque utilisateur.
    """
    manga_exists_sql = """
        SELECT id
        FROM manga
        WHERE id = %(manga_id)s;
    """

    upsert_sql = """
        INSERT INTO user_manga_library (
            user_id,
            manga_id,
            library_status,
            user_score,
            is_favorite,
            owned_volumes,
            read_volumes,
            notes,
            started_at,
            finished_at
        )
        VALUES (
            %(user_id)s,
            %(manga_id)s,
            %(library_status)s,
            %(user_score)s,
            %(is_favorite)s,
            %(owned_volumes)s,
            %(read_volumes)s,
            %(notes)s,
            %(started_at)s::date,
            %(finished_at)s::date
        )
        ON CONFLICT (user_id, manga_id)
        DO UPDATE SET
            library_status = EXCLUDED.library_status,
            user_score = EXCLUDED.user_score,
            is_favorite = EXCLUDED.is_favorite,
            owned_volumes = EXCLUDED.owned_volumes,
            read_volumes = EXCLUDED.read_volumes,
            notes = EXCLUDED.notes,
            started_at = EXCLUDED.started_at,
            finished_at = EXCLUDED.finished_at;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(manga_exists_sql, {"manga_id": payload.manga_id})
            manga_row = cur.fetchone()

            if not manga_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Manga introuvable avec l'id {payload.manga_id}.",
                )

            cur.execute(
                upsert_sql,
                {
                    "user_id": DEFAULT_USER_ID,
                    "manga_id": payload.manga_id,
                    "library_status": payload.library_status,
                    "user_score": payload.user_score,
                    "is_favorite": payload.is_favorite,
                    "owned_volumes": payload.owned_volumes,
                    "read_volumes": payload.read_volumes,
                    "notes": payload.notes,
                    "started_at": payload.started_at,
                    "finished_at": payload.finished_at,
                },
            )
            conn.commit()

    item = fetch_library_item(payload.manga_id)

    return {
        "status": "ok",
        "item": item,
    }


@app.put("/library/items/{manga_id}")
def update_library_item(
    manga_id: int,
    payload: LibraryItemRequest,
) -> dict[str, Any]:
    """
    Met à jour un manga dans la bibliothèque.

    Pour simplifier la V0.8, le payload reste complet.
    L'id du chemin est prioritaire sur payload.manga_id.
    """
    payload.manga_id = manga_id
    return upsert_library_item(payload)


@app.delete("/library/items/{manga_id}")
def delete_library_item(manga_id: int) -> dict[str, Any]:
    """
    Supprime un manga de la bibliothèque utilisateur.
    """
    sql = """
        DELETE FROM user_manga_library
        WHERE user_id = %(user_id)s
          AND manga_id = %(manga_id)s
        RETURNING manga_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "user_id": DEFAULT_USER_ID,
                    "manga_id": manga_id,
                },
            )
            deleted = cur.fetchone()
            conn.commit()

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Manga {manga_id} absent de la bibliothèque.",
        )

    return {
        "status": "deleted",
        "manga_id": manga_id,
    }


@app.post("/recommendations/library")
def recommend_from_library(
    payload: LibraryRecommendationRequest,
) -> dict[str, Any]:
    """
    Recommande des mangas à partir de la bibliothèque utilisateur.

    V0.8 simple :
    - construit un profil à partir des mangas positifs de la bibliothèque ;
    - exclut tous les mangas déjà présents dans la bibliothèque ;
    - réutilise le moteur profil V0.7.4.
    """
    positive_sources_sql = """
        SELECT
            m.id,
            m.title,
            l.library_status,
            l.user_score::float AS user_score,
            l.is_favorite
        FROM user_manga_library l
        JOIN manga m
            ON m.id = l.manga_id
        WHERE l.user_id = %(user_id)s
          AND l.library_status IN (
                'READ',
                'READING',
                'OWNED',
                'WANT_TO_READ'
          )
          AND l.library_status NOT IN (
                'DROPPED',
                'NOT_INTERESTED'
          )
          AND (
                l.is_favorite = TRUE
                OR l.user_score IS NULL
                OR l.user_score >= 7
                OR l.library_status IN ('READ', 'READING')
          )
        ORDER BY
            l.is_favorite DESC,
            l.user_score DESC NULLS LAST,
            l.updated_at DESC,
            m.popularity ASC NULLS LAST
        LIMIT 10;
    """

    library_manga_ids_sql = """
        SELECT manga_id
        FROM user_manga_library
        WHERE user_id = %(user_id)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                positive_sources_sql,
                {"user_id": DEFAULT_USER_ID},
            )
            positive_sources = cur.fetchall()

            cur.execute(
                library_manga_ids_sql,
                {"user_id": DEFAULT_USER_ID},
            )
            library_rows = cur.fetchall()

    if not positive_sources:
        raise HTTPException(
            status_code=400,
            detail=(
                "La bibliothèque ne contient pas encore assez de signaux positifs. "
                "Ajoute au moins un manga lu, en cours, possédé ou favori."
            ),
        )

    library_manga_ids = {
        row["manga_id"] if isinstance(row, dict) else row[0]
        for row in library_rows
    }

    liked_titles = [row["title"] for row in positive_sources]

    profile_result = recommend_from_profile(
        ProfileRecommendationRequest(
            liked_titles=liked_titles,
            limit=20,
            min_score=payload.min_score,
            only_finished=payload.only_finished,
            exclude_sensitive_mismatches=payload.exclude_sensitive_mismatches,
        )
    )

    recommendations = []

    for recommendation in profile_result.get("recommendations", []):
        manga_id = recommendation.get("id")

        if manga_id in library_manga_ids:
            continue

        recommendations.append(recommendation)

        if len(recommendations) >= payload.limit:
            break

    return {
        "user_id": DEFAULT_USER_ID,
        "source": "library",
        "positive_sources": positive_sources,
        "excluded_library_manga_count": len(library_manga_ids),
        "count": len(recommendations),
        "recommendations": recommendations,
    }
'''


def main() -> int:
    text = MAIN_PATH.read_text(encoding="utf-8")

    if "from typing import Any, Literal" not in text:
        text = text.replace(
            "from typing import Any",
            "from typing import Any, Literal",
            1,
        )

    text = text.replace(
        'version="0.7.0"',
        'version="0.8.0"',
        1,
    )

    if "class LibraryItemRequest" not in text:
        text = text.replace(
            "\n\ndef get_connection():",
            "\n" + MODELS_BLOCK + "\n\ndef get_connection():",
            1,
        )
        print("[OK] Modèles bibliothèque ajoutés.")
    else:
        print("[INFO] Modèles bibliothèque déjà présents.")

    if '@app.get("/library")' not in text:
        text = text.replace(
            '\n\n@app.get("/recommendations/similar")',
            "\n" + ENDPOINTS_BLOCK + '\n\n@app.get("/recommendations/similar")',
            1,
        )
        print("[OK] Endpoints bibliothèque ajoutés.")
    else:
        print("[INFO] Endpoints bibliothèque déjà présents.")

    MAIN_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {MAIN_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())