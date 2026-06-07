from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


PROFILE_FUNCTIONS = '''
def get_library_profile() -> dict[str, Any]:
    return call_api_get("/library/profile")


def format_weighted_tags(values: list[dict[str, Any]] | None) -> str:
    if not values:
        return "Non renseigné"

    return ", ".join(
        [
            f"{item.get('name')} ({format_number(item.get('total_weight'), 1)})"
            for item in values[:5]
        ]
    )


def display_library_profile(profile: dict[str, Any]) -> None:
    st.subheader("Profil de lecture détecté")

    status_counts = profile.get("status_counts") or {}
    strongest_sources = profile.get("strongest_sources") or []
    negative_items = profile.get("negative_items") or []

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Lus", status_counts.get("READ", 0))

    with c2:
        st.metric("En cours", status_counts.get("READING", 0))

    with c3:
        st.metric("À lire", status_counts.get("WANT_TO_READ", 0))

    with c4:
        st.metric("Signaux négatifs", profile.get("negative_item_count", 0))

    st.write("**Genres dominants :**")
    st.write(format_weighted_tags(profile.get("top_genres")))

    st.write("**Thèmes dominants :**")
    st.write(format_weighted_tags(profile.get("top_themes")))

    st.write("**Cibles éditoriales dominantes :**")
    st.write(format_weighted_tags(profile.get("top_demographics")))

    if strongest_sources:
        st.write("**Mangas les plus influents dans ton profil :**")

        for source in strongest_sources[:5]:
            st.write(
                f"- **{source.get('title')}** — "
                f"{source.get('library_status')} — "
                f"note {format_number(source.get('user_score'), 1)} — "
                f"poids {format_number(source.get('positive_weight'), 1)}"
            )

    if negative_items:
        with st.expander("Voir les signaux négatifs / exclusions"):
            for item in negative_items:
                st.write(
                    f"- **{item.get('title')}** — "
                    f"{item.get('library_status')} — "
                    f"note {format_number(item.get('user_score'), 1)} — "
                    f"{item.get('negative_reason')}"
                )
'''


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    if "def get_library_profile()" not in text:
        marker = "\n\ndef display_library_item_card"
        if marker not in text:
            raise SystemExit("[ERREUR] Impossible de trouver display_library_item_card dans app.py.")

        text = text.replace(
            marker,
            "\n" + PROFILE_FUNCTIONS + marker,
            1,
        )

        print("[OK] Fonctions profil bibliothèque ajoutées.")
    else:
        print("[INFO] Fonctions profil bibliothèque déjà présentes.")

    old = '''with tab_library:
    st.subheader("1. Ajouter ou mettre à jour un manga dans ma bibliothèque")'''

    new = '''with tab_library:
    st.subheader("0. Mon profil de lecture")

    if st.button("Analyser ma bibliothèque", type="secondary"):
        library_profile = get_library_profile()
        display_library_profile(library_profile)
    else:
        st.info("Clique sur le bouton pour voir ce que Mangadvisor comprend de ta bibliothèque.")

    st.divider()

    st.subheader("1. Ajouter ou mettre à jour un manga dans ma bibliothèque")'''

    if old in text and "Analyser ma bibliothèque" not in text:
        text = text.replace(old, new, 1)
        print("[OK] Bloc profil bibliothèque ajouté dans l’onglet bibliothèque.")
    else:
        print("[INFO] Bloc profil déjà présent ou structure différente.")

    UI_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {UI_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_ui")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())