from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"[ERREUR] Bloc introuvable : {label}")

    return text.replace(old, new, 1)


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    # --------------------------------------------------
    # 1. Ajouter recommendation_goal à l'appel API
    # --------------------------------------------------
    old = '''def get_library_recommendations(
    limit: int = 5,
    min_score: float = 6.8,
    only_finished: bool = False,
    exclude_sensitive_mismatches: bool = False,
) -> dict[str, Any]:'''

    new = '''def get_library_recommendations(
    limit: int = 5,
    min_score: float = 6.8,
    only_finished: bool = False,
    exclude_sensitive_mismatches: bool = False,
    recommendation_goal: str = "SIMILAR_SAFE",
) -> dict[str, Any]:'''

    if old in text:
        text = replace_once(text, old, new, "signature get_library_recommendations")
        print("[OK] Signature get_library_recommendations mise à jour.")
    else:
        print("[INFO] Signature déjà modifiée ou bloc différent.")

    old = '''            "exclude_sensitive_mismatches": exclude_sensitive_mismatches,
        },'''

    new = '''            "exclude_sensitive_mismatches": exclude_sensitive_mismatches,
            "recommendation_goal": recommendation_goal,
        },'''

    if old in text and '"recommendation_goal": recommendation_goal' not in text:
        text = replace_once(text, old, new, "payload get_library_recommendations")
        print("[OK] Payload recommendation_goal ajouté.")
    else:
        print("[INFO] Payload recommendation_goal déjà présent ou bloc différent.")

    # --------------------------------------------------
    # 2. Afficher le bonus objectif dans les cartes reco
    # --------------------------------------------------
    old = '''        community_from = recommendation.get("community_recommended_from") or []'''

    new = '''        recommendation_goal = recommendation.get("recommendation_goal")
        goal_bonus = recommendation.get("goal_bonus")
        base_recommendation_score = recommendation.get("base_recommendation_score")
        volumes = recommendation.get("volumes")
        chapters = recommendation.get("chapters")

        if recommendation_goal:
            st.write("**Objectif bibliothèque :**")
            st.write(
                f"{recommendation_goal} — "
                f"score initial {format_number(base_recommendation_score, 1)} ; "
                f"bonus objectif {format_number(goal_bonus, 1)}"
            )

            if volumes is not None or chapters is not None:
                st.write(
                    f"Volumes : {volumes if volumes is not None else 'N/A'} — "
                    f"Chapitres : {chapters if chapters is not None else 'N/A'}"
                )

        community_from = recommendation.get("community_recommended_from") or []'''

    if old in text and "Objectif bibliothèque" not in text:
        text = replace_once(text, old, new, "affichage objectif dans carte reco")
        print("[OK] Affichage objectif bibliothèque ajouté dans les cartes.")
    else:
        print("[INFO] Affichage objectif déjà présent ou bloc différent.")

    # --------------------------------------------------
    # 3. Ajouter le selectbox objectif dans l'onglet bibliothèque
    # --------------------------------------------------
    old = '''    library_reco_exclude_sensitive = st.checkbox(
        "Exclure les recommandations avec éléments éloignants",
        value=False,
        key="library_reco_exclude_sensitive",
    )

    if st.button("Me recommander depuis ma bibliothèque", type="primary"):'''

    new = '''    library_reco_exclude_sensitive = st.checkbox(
        "Exclure les recommandations avec éléments éloignants",
        value=False,
        key="library_reco_exclude_sensitive",
    )

    library_goal_label = st.selectbox(
        "Objectif de recommandation",
        options=[
            "Proche de mes goûts",
            "Quoi lire ensuite",
            "Série terminée / plutôt courte",
        ],
        index=0,
        key="library_recommendation_goal_label",
        help=(
            "Permet d'adapter la recommandation selon ton besoin du moment : "
            "rester proche de tes goûts, trouver quoi lire maintenant, ou privilégier une série terminée et raisonnable."
        ),
    )

    library_goal_map = {
        "Proche de mes goûts": "SIMILAR_SAFE",
        "Quoi lire ensuite": "READ_NEXT",
        "Série terminée / plutôt courte": "SHORT_FINISHED",
    }

    library_recommendation_goal = library_goal_map[library_goal_label]

    if st.button("Me recommander depuis ma bibliothèque", type="primary"):'''

    if old in text and "library_recommendation_goal_label" not in text:
        text = replace_once(text, old, new, "selectbox objectif bibliothèque")
        print("[OK] Selectbox objectif bibliothèque ajouté.")
    else:
        print("[INFO] Selectbox objectif déjà présent ou bloc différent.")

    # --------------------------------------------------
    # 4. Envoyer recommendation_goal à l'API
    # --------------------------------------------------
    old = '''            exclude_sensitive_mismatches=library_reco_exclude_sensitive,
        )'''

    new = '''            exclude_sensitive_mismatches=library_reco_exclude_sensitive,
            recommendation_goal=library_recommendation_goal,
        )'''

    if old in text and "recommendation_goal=library_recommendation_goal" not in text:
        text = replace_once(text, old, new, "appel get_library_recommendations avec objectif")
        print("[OK] Objectif envoyé à l'API.")
    else:
        print("[INFO] Objectif déjà envoyé à l'API ou bloc différent.")

    # --------------------------------------------------
    # 5. Afficher l'objectif retourné
    # --------------------------------------------------
    old = '''        positive_sources = result.get("positive_sources", [])
        recommendations = result.get("recommendations", [])'''

    new = '''        positive_sources = result.get("positive_sources", [])
        recommendations = result.get("recommendations", [])
        recommendation_goal = result.get("recommendation_goal", library_recommendation_goal)
        profile_summary = result.get("profile_summary", {})'''

    if old in text and "profile_summary = result.get" not in text:
        text = replace_once(text, old, new, "lecture objectif retourné")
        print("[OK] Lecture recommendation_goal/profile_summary ajoutée.")
    else:
        print("[INFO] Lecture objectif déjà présente ou bloc différent.")

    old = '''        if positive_sources:
            st.write("Mangas utilisés pour construire ton profil :")
            st.write(", ".join([source.get("title", "") for source in positive_sources]))

        st.write(
            f"Mangas exclus car déjà dans ta bibliothèque : **{result.get('excluded_library_manga_count', 0)}**"
        )'''

    new = '''        st.write(f"Objectif utilisé : **{recommendation_goal}**")

        if positive_sources:
            st.write("Mangas utilisés pour construire ton profil :")
            st.write(", ".join([source.get("title", "") for source in positive_sources]))

        if profile_summary:
            with st.expander("Voir le profil détecté par Mangadvisor"):
                st.write(
                    f"Règle de sélection : {profile_summary.get('source_selection_rule', 'Non renseignée')}"
                )

                top_genres = profile_summary.get("top_genres") or []
                top_themes = profile_summary.get("top_themes") or []
                top_demographics = profile_summary.get("top_demographics") or []

                if top_genres:
                    st.write("**Genres dominants :**")
                    st.write(", ".join([item.get("name", "") for item in top_genres[:5]]))

                if top_themes:
                    st.write("**Thèmes dominants :**")
                    st.write(", ".join([item.get("name", "") for item in top_themes[:5]]))

                if top_demographics:
                    st.write("**Cibles éditoriales dominantes :**")
                    st.write(", ".join([item.get("name", "") for item in top_demographics[:5]]))

        st.write(
            f"Mangas exclus car déjà dans ta bibliothèque : **{result.get('excluded_library_manga_count', 0)}**"
        )'''

    if old in text and "Voir le profil détecté par Mangadvisor" not in text:
        text = replace_once(text, old, new, "affichage objectif et profil détecté")
        print("[OK] Affichage objectif/profil détecté ajouté.")
    else:
        print("[INFO] Affichage objectif/profil déjà présent ou bloc différent.")

    UI_PATH.write_text(text, encoding="utf-8")

    print()
    print(f"[OK] Fichier mis à jour : {UI_PATH}")
    print("Relance maintenant :")
    print("  docker restart mangadvisor_ui")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())