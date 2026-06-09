from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


DELETE_FUNCTION = '''
def call_api_delete(path: str) -> dict[str, Any]:
    """
    Appelle l'API Mangadvisor en DELETE.
    """
    url = f"{API_BASE_URL}{path}"

    try:
        response = requests.delete(url, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as exc:
        st.error(f"Erreur lors de l'appel API DELETE : {exc}")
        st.stop()
'''


LIBRARY_FUNCTIONS = '''
LIBRARY_STATUS_OPTIONS = {
    "Lu": "READ",
    "En cours": "READING",
    "Possédé": "OWNED",
    "Envie de lire": "WANT_TO_READ",
    "Abandonné": "DROPPED",
    "Pas intéressé": "NOT_INTERESTED",
}

LIBRARY_STATUS_LABELS = {
    "READ": "Lu",
    "READING": "En cours",
    "OWNED": "Possédé",
    "WANT_TO_READ": "Envie de lire",
    "DROPPED": "Abandonné",
    "NOT_INTERESTED": "Pas intéressé",
}


def get_library(
    status: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}

    if status:
        params["status"] = status

    if search:
        params["q"] = search

    data = call_api_get("/library", params=params)
    return data.get("items", [])


def upsert_library_item(
    manga_id: int,
    library_status: str,
    user_score: float | None = None,
    is_favorite: bool = False,
    owned_volumes: int | None = None,
    read_volumes: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    payload = {
        "manga_id": manga_id,
        "library_status": library_status,
        "user_score": user_score,
        "is_favorite": is_favorite,
        "owned_volumes": owned_volumes,
        "read_volumes": read_volumes,
        "notes": notes,
        "started_at": None,
        "finished_at": None,
    }

    return call_api_post("/library/items", payload=payload)


def delete_library_item(manga_id: int) -> dict[str, Any]:
    return call_api_delete(f"/library/items/{manga_id}")


def get_library_recommendations(
    limit: int = 5,
    min_score: float = 6.8,
    only_finished: bool = False,
    exclude_sensitive_mismatches: bool = False,
) -> dict[str, Any]:
    return call_api_post(
        "/recommendations/library",
        payload={
            "limit": limit,
            "min_score": min_score,
            "only_finished": only_finished,
            "exclude_sensitive_mismatches": exclude_sensitive_mismatches,
        },
    )


def rerun_app() -> None:
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


def display_library_item_card(item: dict[str, Any]) -> None:
    title = item.get("title") or "Titre inconnu"
    status = item.get("library_status")
    status_label = LIBRARY_STATUS_LABELS.get(status, status or "N/A")

    with st.container(border=True):
        st.markdown(f"### {title}")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Statut bibliothèque", status_label)

        with c2:
            st.metric("Note perso", format_number(item.get("user_score"), 1))

        with c3:
            st.metric("Score manga", format_number(item.get("manga_score"), 2))

        with c4:
            st.metric("Type", item.get("manga_type") or "N/A")

        c5, c6, c7, c8 = st.columns(4)

        with c5:
            st.metric("Volumes possédés", item.get("owned_volumes") or "N/A")

        with c6:
            st.metric("Volumes lus", item.get("read_volumes") or "N/A")

        with c7:
            st.metric("Statut série", item.get("status") or "N/A")

        with c8:
            st.metric("Favori", "Oui" if item.get("is_favorite") else "Non")

        st.write("**Genres :**")
        st.write(format_list(item.get("genres"), "Genres non renseignés"))

        st.write("**Thèmes :**")
        st.write(format_list(item.get("themes"), "Thèmes non renseignés"))

        st.write("**Cible éditoriale :**")
        st.write(format_list(item.get("demographics"), "Cible non renseignée"))

        notes = item.get("notes")

        if notes:
            st.write("**Notes :**")
            st.write(notes)

        manga_id = item.get("manga_id")

        if manga_id:
            if st.button(
                "Retirer de ma bibliothèque",
                key=f"delete_library_item_{manga_id}",
            ):
                delete_library_item(int(manga_id))
                st.success(f"{title} a été retiré de ta bibliothèque.")
                rerun_app()
'''


LIBRARY_TAB_BLOCK = '''
with tab_library:
    st.subheader("1. Ajouter ou mettre à jour un manga dans ma bibliothèque")

    library_search = st.text_input(
        "Rechercher un manga à ajouter",
        value="Naruto",
        help="Exemples : Naruto, Death Note, Berserk, Nana...",
        key="library_search",
    )

    library_search_results = get_mangas(
        search=library_search if library_search else None,
        limit=100,
    )

    if not library_search_results:
        st.warning("Aucun manga trouvé avec cette recherche.")
    else:
        manga_by_id = {manga["id"]: manga for manga in library_search_results}

        selected_library_manga_id = st.selectbox(
            "Manga à ajouter / modifier",
            options=list(manga_by_id.keys()),
            format_func=lambda manga_id: (
                f"{manga_by_id[manga_id].get('title')} "
                f"— {manga_by_id[manga_id].get('manga_type') or 'Type inconnu'} "
                f"— score {format_number(manga_by_id[manga_id].get('score'), 2)}"
            ),
            key="library_selected_manga_id",
        )

        selected_library_manga = manga_by_id[selected_library_manga_id]

        with st.form("library_item_form"):
            c1, c2, c3 = st.columns(3)

            with c1:
                selected_status_label = st.selectbox(
                    "Statut dans ma bibliothèque",
                    options=list(LIBRARY_STATUS_OPTIONS.keys()),
                    index=0,
                )

            with c2:
                user_score = st.number_input(
                    "Ma note /10",
                    min_value=0.0,
                    max_value=10.0,
                    value=8.0,
                    step=0.5,
                )

            with c3:
                is_favorite = st.checkbox("Favori", value=False)

            c4, c5 = st.columns(2)

            with c4:
                owned_volumes = st.number_input(
                    "Volumes possédés",
                    min_value=0,
                    value=0,
                    step=1,
                )

            with c5:
                read_volumes = st.number_input(
                    "Volumes lus",
                    min_value=0,
                    value=0,
                    step=1,
                )

            notes = st.text_area(
                "Notes personnelles",
                value="",
                placeholder="Exemple : très bon shōnen, univers sympa, envie de lire la suite...",
            )

            submitted = st.form_submit_button("Ajouter / mettre à jour")

        if submitted:
            upsert_library_item(
                manga_id=int(selected_library_manga_id),
                library_status=LIBRARY_STATUS_OPTIONS[selected_status_label],
                user_score=user_score,
                is_favorite=is_favorite,
                owned_volumes=int(owned_volumes) if owned_volumes > 0 else None,
                read_volumes=int(read_volumes) if read_volumes > 0 else None,
                notes=notes.strip() if notes.strip() else None,
            )

            st.success(
                f"{selected_library_manga.get('title')} a été ajouté / mis à jour dans ta bibliothèque."
            )

    st.divider()

    st.subheader("2. Ma bibliothèque")

    c_filter_1, c_filter_2 = st.columns(2)

    with c_filter_1:
        library_status_filter_label = st.selectbox(
            "Filtrer par statut",
            options=["Tous"] + list(LIBRARY_STATUS_OPTIONS.keys()),
            index=0,
            key="library_status_filter",
        )

    with c_filter_2:
        library_text_filter = st.text_input(
            "Rechercher dans ma bibliothèque",
            value="",
            key="library_text_filter",
        )

    selected_status_filter = None

    if library_status_filter_label != "Tous":
        selected_status_filter = LIBRARY_STATUS_OPTIONS[library_status_filter_label]

    library_items = get_library(
        status=selected_status_filter,
        search=library_text_filter.strip() if library_text_filter.strip() else None,
        limit=200,
    )

    st.write(f"Nombre de mangas dans la bibliothèque : **{len(library_items)}**")

    if not library_items:
        st.info("Ta bibliothèque est vide ou aucun manga ne correspond aux filtres.")
    else:
        for item in library_items:
            display_library_item_card(item)

    st.divider()

    st.subheader("3. Recommandations à partir de ma bibliothèque")

    c_rec_1, c_rec_2, c_rec_3 = st.columns(3)

    with c_rec_1:
        library_reco_limit = st.slider(
            "Nombre de recommandations bibliothèque",
            min_value=3,
            max_value=10,
            value=5,
            key="library_reco_limit",
        )

    with c_rec_2:
        library_reco_min_score = st.slider(
            "Score minimum",
            min_value=0.0,
            max_value=10.0,
            value=6.8,
            step=0.1,
            key="library_reco_min_score",
        )

    with c_rec_3:
        library_reco_only_finished = st.checkbox(
            "Séries terminées uniquement",
            value=False,
            key="library_reco_only_finished",
        )

    library_reco_exclude_sensitive = st.checkbox(
        "Exclure les recommandations avec éléments éloignants",
        value=False,
        key="library_reco_exclude_sensitive",
    )

    if st.button("Me recommander depuis ma bibliothèque", type="primary"):
        result = get_library_recommendations(
            limit=library_reco_limit,
            min_score=library_reco_min_score,
            only_finished=library_reco_only_finished,
            exclude_sensitive_mismatches=library_reco_exclude_sensitive,
        )

        positive_sources = result.get("positive_sources", [])
        recommendations = result.get("recommendations", [])

        if positive_sources:
            st.write("Mangas utilisés pour construire ton profil :")
            st.write(", ".join([source.get("title", "") for source in positive_sources]))

        st.write(
            f"Mangas exclus car déjà dans ta bibliothèque : **{result.get('excluded_library_manga_count', 0)}**"
        )

        if not recommendations:
            st.warning("Aucune recommandation trouvée depuis ta bibliothèque.")
        else:
            for index, recommendation in enumerate(recommendations, start=1):
                display_recommendation_card(recommendation, index)
    else:
        st.info("Ajoute quelques mangas à ta bibliothèque, puis lance une recommandation.")
'''


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    if "def call_api_delete(" not in text:
        text = text.replace(
            "\n\ndef get_health()",
            "\n" + DELETE_FUNCTION + "\n\ndef get_health()",
            1,
        )
        print("[OK] Fonction DELETE ajoutée.")
    else:
        print("[INFO] Fonction DELETE déjà présente.")

    if "def get_library(" not in text:
        text = text.replace(
            "\n\ndef format_list(",
            "\n" + LIBRARY_FUNCTIONS + "\n\ndef format_list(",
            1,
        )
        print("[OK] Fonctions bibliothèque ajoutées.")
    else:
        print("[INFO] Fonctions bibliothèque déjà présentes.")

    if "tab_library" not in text:
        old_simple_tabs = '''tab_single, tab_profile = st.tabs(
    [
        "🔎 Recommandation depuis un manga",
        "🧠 Recommandation depuis mon profil",
    ]
)'''

        new_simple_tabs = '''tab_single, tab_profile, tab_library = st.tabs(
    [
        "🔎 Recommandation depuis un manga",
        "🧠 Recommandation depuis mon profil",
        "📚 Ma bibliothèque",
    ]
)'''

        old_detail_tabs = '''tab_single, tab_profile, tab_detail = st.tabs(
    [
        "🔎 Recommandation depuis un manga",
        "🧠 Recommandation depuis mon profil",
        "📖 Fiche manga",
    ]
)'''

        new_detail_tabs = '''tab_single, tab_profile, tab_detail, tab_library = st.tabs(
    [
        "🔎 Recommandation depuis un manga",
        "🧠 Recommandation depuis mon profil",
        "📖 Fiche manga",
        "📚 Ma bibliothèque",
    ]
)'''

        if old_detail_tabs in text:
            text = text.replace(old_detail_tabs, new_detail_tabs, 1)
            print("[OK] Onglet bibliothèque ajouté après fiche manga.")
        elif old_simple_tabs in text:
            text = text.replace(old_simple_tabs, new_simple_tabs, 1)
            print("[OK] Onglet bibliothèque ajouté.")
        else:
            raise SystemExit(
                "[ERREUR] Bloc st.tabs introuvable. Envoie-moi le début de app.py autour de st.tabs."
            )

        text = text + "\n\n" + LIBRARY_TAB_BLOCK + "\n"
        print("[OK] Contenu onglet bibliothèque ajouté.")
    else:
        print("[INFO] Onglet bibliothèque déjà présent.")

    text = text.replace(
        "Version V0.7.4 stable : recommandations manga par genres, thèmes, cible éditoriale, popularité, score et signal communautaire.",
        "Version V0.8 : bibliothèque utilisateur et recommandations manga depuis ton profil de lecture.",
    )

    UI_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {UI_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_ui")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())