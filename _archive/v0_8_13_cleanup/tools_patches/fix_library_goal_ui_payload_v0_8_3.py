from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


NEW_GET_LIBRARY_RECOMMENDATIONS = '''def get_library_recommendations(
    limit: int = 5,
    min_score: float = 6.8,
    only_finished: bool = False,
    exclude_sensitive_mismatches: bool = False,
    recommendation_goal: str = "SIMILAR_SAFE",
) -> dict[str, Any]:
    return call_api_post(
        "/recommendations/library",
        payload={
            "limit": limit,
            "min_score": min_score,
            "only_finished": only_finished,
            "exclude_sensitive_mismatches": exclude_sensitive_mismatches,
            "recommendation_goal": recommendation_goal,
        },
    )
'''


def replace_function(text: str, start_marker: str, end_marker: str, new_block: str) -> str:
    start = text.find(start_marker)

    if start == -1:
        raise SystemExit(f"[ERREUR] Bloc introuvable : {start_marker}")

    end = text.find(end_marker, start)

    if end == -1:
        raise SystemExit(f"[ERREUR] Fin de bloc introuvable : {end_marker}")

    return text[:start] + new_block + text[end:]


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    # Nettoie une éventuelle ligne ajoutée par erreur dans get_profile_recommendations.
    text = text.replace(
        '            "recommendation_goal": recommendation_goal,\n',
        "",
    )

    # Remplace proprement la fonction bibliothèque.
    text = replace_function(
        text=text,
        start_marker="def get_library_recommendations(",
        end_marker="\n\ndef rerun_app()",
        new_block=NEW_GET_LIBRARY_RECOMMENDATIONS,
    )

    # Vérifie que l'appel depuis l'onglet bibliothèque transmet bien l'objectif.
    old_call = """            exclude_sensitive_mismatches=library_reco_exclude_sensitive,
        )"""

    new_call = """            exclude_sensitive_mismatches=library_reco_exclude_sensitive,
            recommendation_goal=library_recommendation_goal,
        )"""

    if "recommendation_goal=library_recommendation_goal" not in text:
        if old_call not in text:
            raise SystemExit(
                "[ERREUR] Impossible d'ajouter recommendation_goal dans l'appel Streamlit."
            )

        text = text.replace(old_call, new_call, 1)
        print("[OK] Objectif ajouté dans l'appel Streamlit.")
    else:
        print("[INFO] Objectif déjà présent dans l'appel Streamlit.")

    UI_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier corrigé : {UI_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_ui")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())