from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_recommendation_profile_tests.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"[ERREUR] Bloc introuvable : {label}")

    return text.replace(old, new, 1)


def patch_main_py() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")

    old = """                (COUNT(DISTINCT manga_id) FILTER (
                    WHERE name IN (
                        'Supernatural',
                        'Urban Fantasy',
                        'Super Power'
                    )
                ))::int AS source_supernatural_count,

                (COUNT(DISTINCT manga_id) FILTER (
                    WHERE name IN (
                        'Mystery',
                        'Suspense'
                    )
                ))::int AS source_mystery_count,"""

    new = """                (COUNT(DISTINCT manga_id) FILTER (
                    WHERE name IN (
                        'Supernatural',
                        'Urban Fantasy',
                        'Super Power'
                    )
                ))::int AS source_supernatural_count,

                (COUNT(DISTINCT manga_id) FILTER (
                    WHERE name IN (
                        'Action',
                        'Adventure',
                        'Super Power',
                        'Martial Arts',
                        'Urban Fantasy'
                    )
                ))::int AS source_action_adventure_count,

                (COUNT(DISTINCT manga_id) FILTER (
                    WHERE name IN (
                        'Shounen'
                    )
                ))::int AS source_shounen_count,

                (COUNT(DISTINCT manga_id) FILTER (
                    WHERE name IN (
                        'Mystery',
                        'Suspense'
                    )
                ))::int AS source_mystery_count,"""

    text = replace_once(text, old, new, "source_intent_profile - ajout action/shounen")

    old = """                MAX(
                    CASE
                        WHEN name IN ('Action', 'Adventure', 'Super Power', 'Martial Arts')
                        THEN 1 ELSE 0
                    END
                )::int AS has_action_adventure_signal,

                MAX(
                    CASE
                        WHEN name IN ('Slice of Life')
                        THEN 1 ELSE 0
                    END
                )::int AS has_slice_of_life_signal,"""

    new = """                MAX(
                    CASE
                        WHEN name IN ('Action', 'Adventure', 'Super Power', 'Martial Arts')
                        THEN 1 ELSE 0
                    END
                )::int AS has_action_adventure_signal,

                MAX(
                    CASE
                        WHEN name = 'Shounen'
                        THEN 1 ELSE 0
                    END
                )::int AS has_shounen_signal,

                MAX(
                    CASE
                        WHEN name IN ('Seinen', 'Josei')
                        THEN 1 ELSE 0
                    END
                )::int AS has_mature_demographic_signal,

                MAX(
                    CASE
                        WHEN name IN ('Slice of Life')
                        THEN 1 ELSE 0
                    END
                )::int AS has_slice_of_life_signal,"""

    text = replace_once(text, old, new, "candidate_intent_signals - ajout shounen/mature")

    old = """                COALESCE(cis.has_supernatural_signal, 0)::int AS has_supernatural_signal,
                COALESCE(cis.has_mystery_signal, 0)::int AS has_mystery_signal,
                COALESCE(cis.has_psychological_signal, 0)::int AS has_psychological_signal,
                COALESCE(cis.has_action_adventure_signal, 0)::int AS has_action_adventure_signal,
                COALESCE(cis.has_slice_of_life_signal, 0)::int AS has_slice_of_life_signal,"""

    new = """                COALESCE(cis.has_supernatural_signal, 0)::int AS has_supernatural_signal,
                COALESCE(cis.has_mystery_signal, 0)::int AS has_mystery_signal,
                COALESCE(cis.has_psychological_signal, 0)::int AS has_psychological_signal,
                COALESCE(cis.has_action_adventure_signal, 0)::int AS has_action_adventure_signal,
                COALESCE(cis.has_shounen_signal, 0)::int AS has_shounen_signal,
                COALESCE(cis.has_mature_demographic_signal, 0)::int AS has_mature_demographic_signal,
                COALESCE(cis.has_slice_of_life_signal, 0)::int AS has_slice_of_life_signal,"""

    text = replace_once(text, old, new, "candidate_base - ajout colonnes shounen/mature")

    old = """                (
                    CASE
                        WHEN sip.source_supernatural_count >= 2 THEN
                            CASE
                                WHEN COALESCE(cis.has_supernatural_signal, 0) = 1 THEN 34
                                ELSE -18
                            END
                            +
                            CASE
                                WHEN COALESCE(cis.has_supernatural_signal, 0) = 1
                                 AND COALESCE(cis.has_action_adventure_signal, 0) = 1
                                THEN 8
                                ELSE 0
                            END
                            +
                            CASE
                                WHEN COALESCE(cis.has_supernatural_signal, 0) = 0
                                 AND COALESCE(cis.has_psychological_signal, 0) = 1
                                THEN -18
                                ELSE 0
                            END
                        ELSE 0
                    END
                )::float AS supernatural_intent_score,"""

    new = """                (
                    CASE
                        WHEN sip.source_supernatural_count >= 2 THEN
                            CASE
                                WHEN COALESCE(cis.has_supernatural_signal, 0) = 1 THEN 30
                                ELSE -24
                            END

                            +
                            CASE
                                WHEN (
                                        sip.source_shounen_count >= 2
                                        OR sip.source_action_adventure_count >= 1
                                     )
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                 AND COALESCE(cis.has_shounen_signal, 0) = 1
                                 AND COALESCE(cis.has_action_adventure_signal, 0) = 1
                                THEN 54
                                ELSE 0
                            END

                            +
                            CASE
                                WHEN (
                                        sip.source_shounen_count >= 2
                                        OR sip.source_action_adventure_count >= 1
                                     )
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                 AND COALESCE(cis.has_shounen_signal, 0) = 1
                                THEN 20
                                ELSE 0
                            END

                            +
                            CASE
                                WHEN (
                                        sip.source_shounen_count >= 2
                                        OR sip.source_action_adventure_count >= 1
                                     )
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                 AND COALESCE(cis.has_action_adventure_signal, 0) = 1
                                THEN 16
                                ELSE 0
                            END

                            +
                            CASE
                                WHEN COALESCE(ccs.community_source_count, 0) >= 2
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                THEN 14
                                WHEN COALESCE(ccs.community_source_count, 0) = 1
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                THEN 6
                                ELSE 0
                            END

                            -
                            CASE
                                WHEN COALESCE(cis.has_psychological_signal, 0) = 1
                                 AND COALESCE(cis.has_action_adventure_signal, 0) = 0
                                 AND COALESCE(cis.has_shounen_signal, 0) = 0
                                THEN 22
                                ELSE 0
                            END

                            -
                            CASE
                                WHEN COALESCE(cis.has_mature_demographic_signal, 0) = 1
                                 AND COALESCE(cis.has_shounen_signal, 0) = 0
                                 AND COALESCE(cis.has_action_adventure_signal, 0) = 0
                                THEN 14
                                ELSE 0
                            END
                        ELSE 0
                    END
                )::float AS supernatural_intent_score,"""

    text = replace_once(text, old, new, "supernatural_intent_score V0.7.3")

    old = """                    - CASE
                        WHEN cb.status = 'On Hiatus' THEN 12
                        ELSE 0
                      END

                    - CASE
                        WHEN cb.common_demographic_count = 0 THEN 10
                        ELSE 0
                      END"""

    new = """                    - CASE
                        WHEN cb.title ILIKE '% Part %'
                          OR cb.title ILIKE '%Episode %'
                          OR cb.title ILIKE '%Tanpenshuu%'
                        THEN 32
                        ELSE 0
                      END

                    - CASE
                        WHEN cb.status = 'On Hiatus' THEN 12
                        ELSE 0
                      END

                    - CASE
                        WHEN cb.common_demographic_count = 0 THEN 10
                        ELSE 0
                      END"""

    text = replace_once(text, old, new, "malus suites / épisodes / spin-offs")

    MAIN_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Patch main.py appliqué : {MAIN_PATH}")


def patch_test_script() -> None:
    text = TEST_PATH.read_text(encoding="utf-8")

    text = text.replace(
        'ENGINE_VERSION = "V0.7.2"',
        'ENGINE_VERSION = "V0.7.3"',
    )

    text = text.replace(
        'REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_7_2.md"',
        'REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_7_3.md"',
    )

    old = """    editorial_score = recommendation.get("editorial_score")
    community_score = recommendation.get("community_score")
    quality_score = recommendation.get("quality_score")

    if community_from:"""

    new = """    editorial_score = recommendation.get("editorial_score")
    community_score = recommendation.get("community_score")
    dominant_intent_score = recommendation.get("dominant_intent_score")
    quality_score = recommendation.get("quality_score")

    if community_from:"""

    text = replace_once(text, old, new, "tests - lecture dominant_intent_score")

    old = """    if community_score is not None:
        score_parts.append(f"communauté {format_score(community_score)}")

    if quality_score is not None:
        score_parts.append(f"qualité {format_score(quality_score)}")"""

    new = """    if community_score is not None:
        score_parts.append(f"communauté {format_score(community_score)}")

    if dominant_intent_score is not None:
        score_parts.append(f"intention {format_score(dominant_intent_score)}")

    if quality_score is not None:
        score_parts.append(f"qualité {format_score(quality_score)}")"""

    text = replace_once(text, old, new, "tests - affichage dominant_intent_score")

    TEST_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Patch tests appliqué : {TEST_PATH}")


def main() -> int:
    patch_main_py()
    patch_test_script()

    print()
    print("Patch V0.7.3 terminé.")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print("  cmd\\run-recommendation-tests.cmd")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())