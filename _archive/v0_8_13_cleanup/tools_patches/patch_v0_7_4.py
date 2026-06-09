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

    old = """                (
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

    new = """                (
                    CASE
                        WHEN sip.source_supernatural_count >= 2 THEN
                            CASE
                                WHEN COALESCE(cis.has_supernatural_signal, 0) = 1 THEN 22
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
                                THEN 30
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
                                THEN 10
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
                                THEN 10
                                ELSE 0
                            END

                            +
                            CASE
                                WHEN COALESCE(ccs.community_source_count, 0) >= 2
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                THEN 10
                                WHEN COALESCE(ccs.community_source_count, 0) = 1
                                 AND COALESCE(cis.has_supernatural_signal, 0) = 1
                                THEN 4
                                ELSE 0
                            END

                            -
                            CASE
                                WHEN 'Gore' = ANY(COALESCE(cps.sensitive_mismatches, ARRAY[]::text[]))
                                THEN 42
                                ELSE 0
                            END

                            -
                            CASE
                                WHEN 'Romance' = ANY(COALESCE(cps.sensitive_mismatches, ARRAY[]::text[]))
                                THEN 28
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

    text = replace_once(text, old, new, "supernatural_intent_score V0.7.4")

    MAIN_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Patch main.py appliqué : {MAIN_PATH}")


def patch_test_script() -> None:
    text = TEST_PATH.read_text(encoding="utf-8")

    text = text.replace(
        'ENGINE_VERSION = "V0.7.3"',
        'ENGINE_VERSION = "V0.7.4"',
    )

    text = text.replace(
        'REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_7_3.md"',
        'REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_7_4.md"',
    )

    TEST_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Patch tests appliqué : {TEST_PATH}")


def main() -> int:
    patch_main_py()
    patch_test_script()

    print()
    print("Patch V0.7.4 terminé.")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print("  cmd\\run-recommendation-tests.cmd")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())