from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_library_recommendation_tests.py"
CMD_PATH = ROOT / "cmd" / "run-library-recommendation-tests.cmd"


HELPERS_BLOCK = '''
def format_profile_summary(profile_summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    if not profile_summary:
        return [
            "_Aucun résumé de profil retourné par l'API._",
            "",
        ]

    status_counts = profile_summary.get("status_counts") or {}
    top_genres = profile_summary.get("top_genres") or []
    top_themes = profile_summary.get("top_themes") or []
    top_demographics = profile_summary.get("top_demographics") or []

    lines.extend(
        [
            "### Résumé du profil bibliothèque interprété par l’API",
            "",
            f"**Règle de sélection des sources :** {profile_summary.get('source_selection_rule', 'Non renseignée')}",
            "",
            f"**Sources positives disponibles :** `{profile_summary.get('positive_source_count_available', 0)}`",
            "",
            f"**Sources positives utilisées :** `{profile_summary.get('positive_source_count_used', 0)}`",
            "",
            "#### Répartition par statut",
            "",
            "| Statut | Nombre |",
            "|---|---:|",
        ]
    )

    if status_counts:
        for status, count in sorted(status_counts.items()):
            lines.append(f"| {md_cell(status)} | {count} |")
    else:
        lines.append("| Aucun | 0 |")

    lines.extend(
        [
            "",
            "#### Top genres détectés",
            "",
            "| Genre | Sources | Poids total |",
            "|---|---:|---:|",
        ]
    )

    if top_genres:
        for item in top_genres[:10]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )
    else:
        lines.append("| Aucun | 0 | 0 |")

    lines.extend(
        [
            "",
            "#### Top thèmes détectés",
            "",
            "| Thème | Sources | Poids total |",
            "|---|---:|---:|",
        ]
    )

    if top_themes:
        for item in top_themes[:10]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )
    else:
        lines.append("| Aucun | 0 | 0 |")

    lines.extend(
        [
            "",
            "#### Top cibles éditoriales détectées",
            "",
            "| Cible | Sources | Poids total |",
            "|---|---:|---:|",
        ]
    )

    if top_demographics:
        for item in top_demographics[:10]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )
    else:
        lines.append("| Aucune | 0 | 0 |")

    lines.append("")

    return lines
'''


def main() -> int:
    text = TEST_PATH.read_text(encoding="utf-8")

    if "def format_profile_summary(" not in text:
        marker = "\n\ndef main() -> int:"
        if marker not in text:
            raise SystemExit("[ERREUR] Impossible de trouver def main() dans le script de test.")

        text = text.replace(marker, "\n" + HELPERS_BLOCK + marker, 1)
        print("[OK] Fonction format_profile_summary ajoutée.")
    else:
        print("[INFO] Fonction format_profile_summary déjà présente.")

    text = text.replace(
        'REPORT_PATH = REPORT_DIR / "library_recommendation_tests_v0_8_2.md"',
        'REPORT_PATH = REPORT_DIR / "library_recommendation_tests_v0_8_2_profile_summary.md"',
    )

    text = text.replace(
        "# Mangadvisor — Tests recommandations depuis bibliothèque V0.8.2",
        "# Mangadvisor — Tests recommandations depuis bibliothèque V0.8.2 — Profil enrichi",
    )

    old = '''        result = get_library_recommendations(limit=5)
        recommendations = result.get("recommendations", [])
        positive_sources = result.get("positive_sources", [])'''

    new = '''        result = get_library_recommendations(limit=5)
        recommendations = result.get("recommendations", [])
        positive_sources = result.get("positive_sources", [])
        positive_sources_available = result.get("positive_sources_available", [])
        profile_summary = result.get("profile_summary", {})'''

    if old in text and "positive_sources_available = result.get" not in text:
        text = text.replace(old, new, 1)
        print("[OK] Lecture profile_summary ajoutée.")
    else:
        print("[INFO] Lecture profile_summary déjà présente ou bloc différent.")

    old = '''        detail_rows.extend(
            [
                "",
                "### Recommandations obtenues",
                "",
                "| Rang | Titre | Score reco | Score manga | Statut | Genres communs | Thèmes communs | Cible commune | Raison |",
                "|---:|---|---:|---:|---|---|---|---|---|",
            ]
        )'''

    new = '''        detail_rows.extend(
            [
                "",
                "### Sources positives utilisées par l’API",
                "",
                "| Titre | Statut bibliothèque | Note | Favori | Poids positif |",
                "|---|---|---:|---|---:|",
            ]
        )

        for source in positive_sources:
            detail_rows.append(
                "| "
                f"{md_cell(source.get('title'))} | "
                f"{md_cell(source.get('library_status'))} | "
                f"{format_score(source.get('user_score'))} | "
                f"{'Oui' if source.get('is_favorite') else 'Non'} | "
                f"{format_score(source.get('positive_weight'))} |"
            )

        detail_rows.extend(
            [
                "",
                "### Sources positives disponibles",
                "",
                "| Titre | Statut bibliothèque | Note | Favori | Poids positif |",
                "|---|---|---:|---|---:|",
            ]
        )

        for source in positive_sources_available:
            detail_rows.append(
                "| "
                f"{md_cell(source.get('title'))} | "
                f"{md_cell(source.get('library_status'))} | "
                f"{format_score(source.get('user_score'))} | "
                f"{'Oui' if source.get('is_favorite') else 'Non'} | "
                f"{format_score(source.get('positive_weight'))} |"
            )

        detail_rows.extend([""])
        detail_rows.extend(format_profile_summary(profile_summary))

        detail_rows.extend(
            [
                "",
                "### Recommandations obtenues",
                "",
                "| Rang | Titre | Score reco | Score manga | Statut | Genres communs | Thèmes communs | Cible commune | Raison |",
                "|---:|---|---:|---:|---|---|---|---|---|",
            ]
        )'''

    if old in text and "### Sources positives utilisées par l’API" not in text:
        text = text.replace(old, new, 1)
        print("[OK] Sections sources positives + profil_summary ajoutées.")
    else:
        print("[INFO] Sections déjà présentes ou bloc différent.")

    TEST_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Script de test mis à jour : {TEST_PATH}")

    if CMD_PATH.exists():
        cmd_text = CMD_PATH.read_text(encoding="utf-8")

        cmd_text = cmd_text.replace(
            "library_recommendation_tests_v0_8_1.md",
            "library_recommendation_tests_v0_8_2_profile_summary.md",
        )

        cmd_text = cmd_text.replace(
            "library_recommendation_tests_v0_8_2.md",
            "library_recommendation_tests_v0_8_2_profile_summary.md",
        )

        CMD_PATH.write_text(cmd_text, encoding="utf-8")
        print(f"[OK] Commande Windows mise à jour : {CMD_PATH}")

    print()
    print("Relance maintenant :")
    print("  cmd\\run-library-recommendation-tests.cmd")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())