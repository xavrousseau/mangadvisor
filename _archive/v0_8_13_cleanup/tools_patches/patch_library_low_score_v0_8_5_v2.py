from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_library_status_tests.py"
CMD_PATH = ROOT / "cmd" / "run-library-status-tests.cmd"


def patch_main_py() -> None:
    lines = MAIN_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    new_lines = []
    replacements = 0
    waiting_for_else = False

    for line in lines:
        if "WHEN l.user_score >= 6 THEN 0.5" in line:
            indent = line.split("WHEN")[0]

            new_lines.append(f"{indent}WHEN l.user_score >= 6 THEN 0.0\n")
            new_lines.append(f"{indent}WHEN l.user_score >= 5 THEN -2.0\n")

            replacements += 1
            waiting_for_else = True
            continue

        if waiting_for_else and "ELSE -2.0" in line:
            indent = line.split("ELSE")[0]
            new_lines.append(f"{indent}ELSE -10.0\n")
            waiting_for_else = False
            continue

        new_lines.append(line)

        if waiting_for_else and "END" in line:
            waiting_for_else = False

    if replacements == 0:
        raise SystemExit(
            "[ERREUR] Aucune ligne 'WHEN l.user_score >= 6 THEN 0.5' trouvée. "
            "Le fichier est peut-être déjà modifié ou le bloc a une autre forme."
        )

    MAIN_PATH.write_text("".join(new_lines), encoding="utf-8")

    print(f"[OK] Pondération notes faibles corrigée dans main.py : {replacements} bloc(s).")


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
    print("À vérifier dans le rapport :")
    print("  Dans le scénario 'Manga lu mais très mal noté', Fairy Tail ne doit plus apparaître dans les sources positives.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())