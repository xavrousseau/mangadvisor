from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_library_status_tests.py"
CMD_PATH = ROOT / "cmd" / "run-library-status-tests.cmd"


NEW_SCORE_CASE = """{indent}+ CASE
{indent}    WHEN l.user_score >= 9 THEN 4.0
{indent}    WHEN l.user_score >= 8.5 THEN 3.5
{indent}    WHEN l.user_score >= 8 THEN 3.0
{indent}    WHEN l.user_score >= 7 THEN 2.0
{indent}    WHEN l.user_score >= 6 THEN 0.0
{indent}    WHEN l.user_score >= 5 THEN -2.0
{indent}    WHEN l.user_score IS NULL THEN 0.0
{indent}    ELSE -10.0
{indent}  END"""


def patch_main_py() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")

    pattern = re.compile(
        r"(?P<indent>^[ \t]*)\+\s*CASE\s*\n(?P<body>.*?^[ \t]*END)",
        flags=re.MULTILINE | re.DOTALL,
    )

    replacements = 0

    def replace_match(match: re.Match) -> str:
        nonlocal replacements

        full_block = match.group(0)
        body = match.group("body")
        indent = match.group("indent")

        if "l.user_score" not in body:
            return full_block

        replacements += 1
        return NEW_SCORE_CASE.format(indent=indent)

    new_text = pattern.sub(replace_match, text)

    if replacements == 0:
        print("[ERREUR] Aucun bloc CASE contenant l.user_score trouvé.")
        print()
        print("Diagnostic à lancer :")
        print('  findstr /N /C:"l.user_score" apps\\api\\app\\main.py')
        raise SystemExit(1)

    MAIN_PATH.write_text(new_text, encoding="utf-8")

    print(f"[OK] Pondération des notes faibles corrigée : {replacements} bloc(s) remplacé(s).")


def patch_test_script() -> None:
    if not TEST_PATH.exists():
        print("[INFO] Script de test introuvable, ignoré.")
        return

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

    TEST_PATH.write_text(text, encoding="utf-8")
    print("[OK] Script de test renommé en V0.8.5.")


def patch_cmd() -> None:
    if not CMD_PATH.exists():
        print("[INFO] Commande Windows introuvable, ignorée.")
        return

    text = CMD_PATH.read_text(encoding="utf-8")

    text = text.replace(
        "library_status_tests_v0_8_4.md",
        "library_status_tests_v0_8_5.md",
    )

    CMD_PATH.write_text(text, encoding="utf-8")
    print("[OK] Commande Windows mise à jour en V0.8.5.")


def main() -> int:
    patch_main_py()
    patch_test_script()
    patch_cmd()

    print()
    print("Patch V0.8.5 terminé.")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_api")
    print("  cmd\\run-library-status-tests.cmd")
    print()
    print("À vérifier :")
    print("  Dans le scénario 'Manga lu mais très mal noté', Fairy Tail ne doit plus apparaître dans les sources positives.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())