from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_library_status_tests.py"


OLD_SCORE_BLOCK = """                    + CASE
                        WHEN l.user_score >= 9 THEN 4.0
                        WHEN l.user_score >= 8.5 THEN 3.5
                        WHEN l.user_score >= 8 THEN 3.0
                        WHEN l.user_score >= 7 THEN 2.0
                        WHEN l.user_score >= 6 THEN 0.5
                        WHEN l.user_score IS NULL THEN 0.0
                        ELSE -2.0
                      END"""


NEW_SCORE_BLOCK = """                    + CASE
                        WHEN l.user_score >= 9 THEN 4.0
                        WHEN l.user_score >= 8.5 THEN 3.5
                        WHEN l.user_score >= 8 THEN 3.0
                        WHEN l.user_score >= 7 THEN 2.0
                        WHEN l.user_score >= 6 THEN 0.0
                        WHEN l.user_score >= 5 THEN -2.0
                        WHEN l.user_score IS NULL THEN 0.0
                        ELSE -10.0
                      END"""


def patch_main_py() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")

    count = text.count(OLD_SCORE_BLOCK)

    if count == 0:
        raise SystemExit("[ERREUR] Bloc de pondération user_score introuvable dans main.py.")

    text = text.replace(OLD_SCORE_BLOCK, NEW_SCORE_BLOCK)

    MAIN_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Pondération des notes faibles corrigée dans main.py ({count} remplacement(s)).")


def patch_test_script() -> None:
    text = TEST_PATH.read_text(encoding="utf-8")

    text = text.replace(
        'REPORT_PATH = REPORT_DIR / "library_status_tests_v0_8_4.md"',
        'REPORT_PATH = REPORT_DIR / "library_status_tests_v0_8_5.md"',
    )

    text = text.replace(
        "# Mangadvisor — Tests statuts bibliothèque V0.8.4",
        "# Mangadvisor — Tests statuts bibliothèque V0.8.5",
    )

    text = text.replace(
        "Ce rapport vérifie que les statuts `DROPPED`, `NOT_INTERESTED`, `WANT_TO_READ` et `OWNED` empêchent bien les mangas concernés de ressortir dans les recommandations.",
        "Ce rapport vérifie que les statuts `DROPPED`, `NOT_INTERESTED`, `WANT_TO_READ` et `OWNED` empêchent bien les mangas concernés de ressortir dans les recommandations. Il vérifie aussi qu'un manga lu avec une très mauvaise note ne contribue plus positivement au profil.",
    )

    text = text.replace(
        'REPORT_PATH.write_text("\\n".join(lines), encoding="utf-8")',
        'REPORT_PATH.write_text("\\n".join(lines), encoding="utf-8")',
    )

    TEST_PATH.write_text(text, encoding="utf-8")

    print("[OK] Script de test renommé en V0.8.5.")


def main() -> int:
    patch_main_py()
    patch_test_script()

    print()
    print("Patch V0.8.5 terminé.")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print("  cmd\\run-library-status-tests.cmd")
    print()
    print("À vérifier dans le rapport :")
    print("  Fairy Tail avec note 3.0 ne doit plus apparaître dans les sources positives disponibles.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())