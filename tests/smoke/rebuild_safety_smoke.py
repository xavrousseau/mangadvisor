"""Prove safe Jikan refresh on disposable CI PostgreSQL with library + editions.

NEVER run against a personal database: credentials are intentionally hardcoded
to the synthetic GitHub Actions database and checked before executing SQL.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
COMPOSE=[
    "docker","compose","--env-file",".env",
    "-f","infra/compose/docker-compose.yml",
    "-f","infra/compose/docker-compose.dev.yml",
]
PSQL=COMPOSE+[
    "exec","-T","postgres","psql","-X","-v","ON_ERROR_STOP=1",
    "-U","manga_ci","-d","mangadvisor_ci",
]


def sql(statement: str) -> str:
    result=subprocess.run(
        PSQL+["-At"],input=statement,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT,
        check=True,timeout=60,
    )
    return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""


def assert_disposable_database():
    actual=sql("SELECT current_database() || ':' || current_user;")
    if actual!="mangadvisor_ci:manga_ci":
        raise RuntimeError("REFUS: cette verification ne peut cibler qu'une base CI jetable.")


def snapshot() -> dict[str,str]:
    queries={
        "canonical_ids":"""SELECT COALESCE(string_agg(
            id::text || '=' || source_mal_id::text, ',' ORDER BY source_mal_id
        ),'') FROM manga;""",
        "library":"""SELECT COALESCE(string_agg(
            manga_id::text || '=' || library_status, ',' ORDER BY manga_id
        ),'') FROM user_manga_library;""",
        "editions":"""SELECT COALESCE(string_agg(
            manga_id::text || '=' || isbn13, ',' ORDER BY isbn13
        ),'') FROM manga_fr_edition;""",
        "reading":"""SELECT COALESCE(string_agg(
            edition_id::text || '=' || is_owned::text || '/' || is_read::text,
            ',' ORDER BY edition_id
        ),'') FROM user_manga_volume;""",
        "genres":"SELECT count(*) FROM manga_genre;",
        "themes":"SELECT count(*) FROM manga_theme;",
        "demographics":"SELECT count(*) FROM manga_demographic;",
    }
    return {key:sql(query) for key,query in queries.items()}


def main():
    assert_disposable_database()
    # Fresh source JSON for one existing synthetic manga; no user information.
    sql("""
        UPDATE jikan_manga_source SET
            genres_json='[{"name":"Adventure"},{"name":"Mystery"}]'::jsonb,
            themes_json='[{"name":"Psychological"}]'::jsonb,
            demographics_json='[{"name":"Seinen"}]'::jsonb
        WHERE mal_id=900001;
    """)
    before=snapshot()
    assert before["library"] and before["editions"],before
    scripts=[
        "sql/schema/003_build_canonical_from_jikan.sql",
        "sql/schema/005_build_theme_demographic_from_jikan.sql",
    ]
    for iteration in (1,2):
        # Repeat exactly the supported additive SQL in an isolated CI database.
        for filename in scripts:
            sql((ROOT / filename).read_text(encoding="utf-8"))
        after=snapshot()
        for key in ("canonical_ids","library","editions","reading"):
            assert before[key]==after[key],(iteration,key,before[key],after[key])
        for key in ("genres","themes","demographics"):
            assert int(after[key])>=int(before[key]),(iteration,key,before[key],after[key])
        if iteration==1:
            first=after
        else:
            for key in ("genres","themes","demographics"):
                assert after[key]==first[key],(iteration,key,first[key],after[key])
    print("OK: SQL rebuild x2, stable manga IDs, library/ISBN/reading untouched; joins additive and idempotent.")


if __name__=="__main__":
    main()
