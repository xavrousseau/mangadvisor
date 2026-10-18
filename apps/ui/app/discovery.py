"""Écran Découvrir de Mangadvisor 1.0.

Ce module ne connaît pas la base de données. Toutes les sources et actions lui
sont transmises par l'application, pour ne pas dupliquer la logique métier.
"""
from __future__ import annotations

from typing import Any, Callable

import streamlit as st

PAGE_SIZE = 12

GENRES: dict[str, str | None] = {
    "Tous les genres": None,
    "Action": "Action",
    "Aventure": "Adventure",
    "Drame": "Drama",
    "Fantastique": "Fantasy",
    "Mystère": "Mystery",
    "Psychologique": "Psychological",
    "Romance": "Romance",
    "Tranche de vie": "Slice of Life",
    "Sport": "Sports",
}


def normalize_search(value: str) -> str:
    """Recherche lisible, sans espaces superflus ni requête démesurée."""
    return " ".join(value.split())[:120]


def paginated_catalog(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """Le 13e résultat sert uniquement à savoir si la page suivante existe."""
    return items[:PAGE_SIZE], len(items) > PAGE_SIZE


def render_discovery(
    *,
    get_mangas: Callable[..., list[dict[str, Any]]],
    get_cover_urls: Callable[[tuple[int, ...]], dict[int, str]],
    display_manga_cover: Callable[..., None],
    get_manga_detail: Callable[[int], dict[str, Any]],
    display_manga_detail: Callable[[dict[str, Any]], None],
    get_similar_recommendations: Callable[..., dict[str, Any]],
    display_manga_recommendations: Callable[[list[dict[str, Any]]], None],
    recommendation_limit: int,
) -> None:
    """Catalogue filtrable → sélection → fiche complète → recommandations."""
    st.markdown("## Explore ton prochain manga")
    st.caption("Parcours le catalogue, ouvre une fiche et découvre des titres similaires.")

    search_col, genre_col = st.columns([2, 1], gap="medium")
    with search_col:
        raw_query = st.text_input(
            "Rechercher par titre",
            value="",
            placeholder="Berserk, Nana, Monster...",
            key="ma_discover_search",
        )
    with genre_col:
        genre_label = st.selectbox(
            "Genre",
            list(GENRES),
            key="ma_discover_genre",
        )
    only_finished = st.checkbox(
        "Séries terminées uniquement",
        key="ma_discover_finished",
    )

    query = normalize_search(raw_query)
    genre = GENRES[genre_label]
    search_signature = (query, genre, bool(only_finished))
    if st.session_state.get("ma_discover_signature") != search_signature:
        st.session_state["ma_discover_signature"] = search_signature
        st.session_state["ma_discover_page"] = 1
        st.session_state.pop("ma_discover_selected_id", None)
        st.session_state.pop("ma_discover_similar", None)

    page = int(st.session_state.get("ma_discover_page", 1))
    fetched = get_mangas(
        search=query or None,
        limit=PAGE_SIZE + 1,
        offset=(page - 1) * PAGE_SIZE,
        genre=genre,
        only_finished=bool(only_finished),
    )
    items, has_next = paginated_catalog(fetched)

    st.caption(f"Page {page} · {len(items)} mangas affichés")
    if not items:
        st.info("Aucun résultat pour ces critères. Essaie un autre titre ou un autre genre.")
    else:
        cover_urls = get_cover_urls(tuple(int(item["id"]) for item in items if item.get("id")))
        for start in range(0, len(items), 3):
            columns = st.columns(3, gap="medium")
            for column, manga in zip(columns, items[start:start + 3]):
                with column:
                    with st.container(border=True):
                        display_manga_cover(manga, cover_urls)
                        st.write(manga.get("title") or "Titre inconnu")
                        score = manga.get("score")
                        score_text = f"★ {float(score):.1f}/10" if score is not None else "Non noté"
                        st.caption(f"{score_text} · {manga.get('manga_type') or 'Manga'}")
                        genres = manga.get("genres") or []
                        if genres:
                            st.caption(" · ".join(genres[:2]))
                        manga_id = manga.get("id")
                        if manga_id and st.button(
                            "Voir la fiche →",
                            key=f"ma_discover_open_{manga_id}",
                            use_container_width=True,
                        ):
                            st.session_state["ma_discover_selected_id"] = int(manga_id)
                            st.session_state.pop("ma_discover_similar", None)

    previous_col, next_col = st.columns(2)
    with previous_col:
        if st.button("← Précédent", disabled=page <= 1, key="ma_discover_previous"):
            st.session_state["ma_discover_page"] = page - 1
            st.rerun()
    with next_col:
        if st.button("Suivant →", disabled=not has_next, key="ma_discover_next"):
            st.session_state["ma_discover_page"] = page + 1
            st.rerun()

    chosen_id = st.session_state.get("ma_discover_selected_id")
    if chosen_id:
        st.divider()
        close_col, heading_col = st.columns([1, 4], gap="medium")
        with close_col:
            if st.button("✕ Fermer", key="ma_discover_close"):
                st.session_state.pop("ma_discover_selected_id", None)
                st.session_state.pop("ma_discover_similar", None)
                st.rerun()
        with heading_col:
            st.caption("FICHE SÉLECTIONNÉE · DONNÉES DU CATALOGUE")

        manga = get_manga_detail(int(chosen_id))
        display_manga_detail(manga)
        st.divider()
        st.markdown("### Et si tu aimais aussi…")
        if st.button(
            "✨ Trouver des mangas similaires",
            key="ma_discover_similar_button",
            type="primary",
        ):
            st.session_state["ma_discover_similar"] = get_similar_recommendations(
                title=manga["title"], limit=recommendation_limit
            )
        similar = st.session_state.get("ma_discover_similar")
        if similar is not None:
            recommendations = similar.get("recommendations") or []
            if recommendations:
                display_manga_recommendations(recommendations)
            else:
                st.info("Aucune recommandation trouvée pour ce titre.")
