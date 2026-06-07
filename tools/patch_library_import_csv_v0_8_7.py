from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"


MODEL_BLOCK = r'''
class LibraryImportCsvRequest(BaseModel):
    csv_content: str = Field(
        ...,
        description="Contenu brut du fichier CSV à importer.",
    )
    delimiter: str = Field(
        default=",",
        description="Séparateur CSV. Par défaut : virgule.",
    )
    default_status: LibraryStatus = Field(
        default="WANT_TO_READ",
        description="Statut utilisé si la colonne library_status est vide.",
    )
    dry_run: bool = Field(
        default=False,
        description="Si true, simule l'import sans écrire en base.",
    )
'''


ENDPOINT_BLOCK = r'''
def clean_import_value(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    return cleaned


def parse_import_float(value: Any) -> float | None:
    cleaned = clean_import_value(value)

    if cleaned is None:
        return None

    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        raise ValueError(f"Valeur numérique invalide : {value}")


def parse_import_int(value: Any) -> int | None:
    cleaned = clean_import_value(value)

    if cleaned is None:
        return None

    try:
        return int(float(cleaned.replace(",", ".")))
    except ValueError:
        raise ValueError(f"Valeur entière invalide : {value}")


def parse_import_bool(value: Any) -> bool:
    cleaned = clean_import_value(value)

    if cleaned is None:
        return False

    normalized = cleaned.lower()

    if normalized in {"true", "1", "yes", "y", "oui", "o", "vrai"}:
        return True

    if normalized in {"false", "0", "no", "n", "non", "faux"}:
        return False

    raise ValueError(f"Valeur booléenne invalide : {value}")


def normalize_import_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        (key or "").strip().lower(): value
        for key, value in row.items()
    }


def get_import_value(
    row: dict[str, Any],
    possible_names: list[str],
) -> Any:
    for name in possible_names:
        normalized_name = name.strip().lower()

        if normalized_name in row:
            return row[normalized_name]

    return None


def find_manga_for_import(
    cur: Any,
    title: str,
) -> dict[str, Any] | None:
    sql = """
        WITH candidates AS (
            SELECT
                id,
                source_mal_id,
                title,
                title_english,
                title_japanese,
                manga_type,
                score::float AS score,
                popularity,

                CASE
                    WHEN LOWER(title) = LOWER(%(title)s) THEN 0
                    WHEN LOWER(COALESCE(title_english, '')) = LOWER(%(title)s) THEN 1
                    WHEN LOWER(COALESCE(title_japanese, '')) = LOWER(%(title)s) THEN 2
                    WHEN title ILIKE %(like_title)s THEN 3
                    WHEN title_english ILIKE %(like_title)s THEN 4
                    WHEN title_japanese ILIKE %(like_title)s THEN 5
                    ELSE 9
                END AS match_rank

            FROM manga

            WHERE LOWER(title) = LOWER(%(title)s)
               OR LOWER(COALESCE(title_english, '')) = LOWER(%(title)s)
               OR LOWER(COALESCE(title_japanese, '')) = LOWER(%(title)s)
               OR title ILIKE %(like_title)s
               OR title_english ILIKE %(like_title)s
               OR title_japanese ILIKE %(like_title)s
        )

        SELECT
            id,
            source_mal_id,
            title,
            title_english,
            title_japanese,
            manga_type,
            score,
            popularity,
            match_rank

        FROM candidates

        ORDER BY
            match_rank ASC,
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

        LIMIT 1;
    """

    cur.execute(
        sql,
        {
            "title": title,
            "like_title": f"%{title}%",
        },
    )

    return cur.fetchone()


@app.post("/library/import/csv")
def import_library_csv(payload: LibraryImportCsvRequest) -> dict[str, Any]:
    """
    Importe une bibliothèque depuis un contenu CSV normalisé.

    Colonnes reconnues :
    - title, titre, manga
    - library_status, status, statut
    - user_score, score, note
    - is_favorite, favorite, favori
    - owned_volumes, volumes_possedes
    - read_volumes, volumes_lus
    - notes, note_perso, commentaire

    V0.8.7 :
    - première source d'import : CSV ;
    - logique conçue pour être réutilisée plus tard avec Excel / JSON / copier-coller.
    """
    import csv
    import io

    delimiter = payload.delimiter or ","

    if len(delimiter) != 1:
        raise HTTPException(
            status_code=400,
            detail="Le séparateur CSV doit contenir un seul caractère.",
        )

    default_status = validate_library_status(payload.default_status)

    csv_content = payload.csv_content.lstrip("\ufeff")

    reader = csv.DictReader(
        io.StringIO(csv_content),
        delimiter=delimiter,
    )

    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="Le CSV ne contient pas d'en-tête.",
        )

    rows = list(reader)

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Le CSV ne contient aucune ligne à importer.",
        )

    imported_items: list[dict[str, Any]] = []
    not_found_items: list[dict[str, Any]] = []
    error_items: list[dict[str, Any]] = []

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
            NULL,
            NULL
        )
        ON CONFLICT (user_id, manga_id)
        DO UPDATE SET
            library_status = EXCLUDED.library_status,
            user_score = EXCLUDED.user_score,
            is_favorite = EXCLUDED.is_favorite,
            owned_volumes = EXCLUDED.owned_volumes,
            read_volumes = EXCLUDED.read_volumes,
            notes = EXCLUDED.notes;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            for index, raw_row in enumerate(rows, start=2):
                row = normalize_import_row(raw_row)

                try:
                    title = clean_import_value(
                        get_import_value(
                            row,
                            ["title", "titre", "manga", "name", "nom"],
                        )
                    )

                    if not title:
                        error_items.append(
                            {
                                "line": index,
                                "error": "Titre manquant.",
                                "raw_row": raw_row,
                            }
                        )
                        continue

                    raw_status = clean_import_value(
                        get_import_value(
                            row,
                            ["library_status", "status", "statut"],
                        )
                    )

                    library_status = validate_library_status(
                        raw_status or default_status
                    )

                    user_score = parse_import_float(
                        get_import_value(
                            row,
                            ["user_score", "score", "note", "rating"],
                        )
                    )

                    is_favorite = parse_import_bool(
                        get_import_value(
                            row,
                            ["is_favorite", "favorite", "favori", "is_fav"],
                        )
                    )

                    owned_volumes = parse_import_int(
                        get_import_value(
                            row,
                            ["owned_volumes", "volumes_possedes", "volumes_owned"],
                        )
                    )

                    read_volumes = parse_import_int(
                        get_import_value(
                            row,
                            ["read_volumes", "volumes_lus", "volumes_read"],
                        )
                    )

                    notes = clean_import_value(
                        get_import_value(
                            row,
                            ["notes", "note_perso", "commentaire", "comments"],
                        )
                    )

                    manga = find_manga_for_import(cur, title)

                    if not manga:
                        not_found_items.append(
                            {
                                "line": index,
                                "title": title,
                                "library_status": library_status,
                            }
                        )
                        continue

                    import_item = {
                        "line": index,
                        "requested_title": title,
                        "matched_manga_id": manga["id"],
                        "matched_title": manga["title"],
                        "match_rank": manga["match_rank"],
                        "manga_type": manga["manga_type"],
                        "manga_score": manga["score"],
                        "popularity": manga["popularity"],
                        "library_status": library_status,
                        "user_score": user_score,
                        "is_favorite": is_favorite,
                        "owned_volumes": owned_volumes,
                        "read_volumes": read_volumes,
                        "notes": notes,
                    }

                    imported_items.append(import_item)

                    if not payload.dry_run:
                        cur.execute(
                            upsert_sql,
                            {
                                "user_id": DEFAULT_USER_ID,
                                "manga_id": manga["id"],
                                "library_status": library_status,
                                "user_score": user_score,
                                "is_favorite": is_favorite,
                                "owned_volumes": owned_volumes,
                                "read_volumes": read_volumes,
                                "notes": notes,
                            },
                        )

                except Exception as exc:
                    error_items.append(
                        {
                            "line": index,
                            "error": str(exc),
                            "raw_row": raw_row,
                        }
                    )

            if payload.dry_run:
                conn.rollback()
            else:
                conn.commit()

    return {
        "status": "dry_run" if payload.dry_run else "imported",
        "user_id": DEFAULT_USER_ID,
        "total_rows": len(rows),
        "matched_count": len(imported_items),
        "not_found_count": len(not_found_items),
        "error_count": len(error_items),
        "imported_items": imported_items,
        "not_found_items": not_found_items,
        "error_items": error_items,
    }
'''


def main() -> int:
    text = MAIN_PATH.read_text(encoding="utf-8")

    if "class LibraryImportCsvRequest" not in text:
        marker = "\n\nclass LibraryRecommendationRequest"

        if marker not in text:
            raise SystemExit(
                "[ERREUR] Impossible de trouver class LibraryRecommendationRequest."
            )

        text = text.replace(
            marker,
            "\n" + MODEL_BLOCK + marker,
            1,
        )

        print("[OK] Modèle LibraryImportCsvRequest ajouté.")
    else:
        print("[INFO] Modèle LibraryImportCsvRequest déjà présent.")

    if '@app.post("/library/import/csv")' not in text:
        marker = '\n\n@app.get("/library/profile")'

        if marker not in text:
            raise SystemExit(
                "[ERREUR] Impossible de trouver @app.get(\"/library/profile\")."
            )

        text = text.replace(
            marker,
            "\n" + ENDPOINT_BLOCK + marker,
            1,
        )

        print("[OK] Endpoint /library/import/csv ajouté.")
    else:
        print("[INFO] Endpoint /library/import/csv déjà présent.")

    text = text.replace('version="0.8.0"', 'version="0.8.7"', 1)

    MAIN_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {MAIN_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print()
    print("Puis teste dans Swagger :")
    print("  POST /library/import/csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())