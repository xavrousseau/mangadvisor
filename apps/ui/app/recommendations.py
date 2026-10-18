"""Recommandations Mangadvisor 1.0 : parcours personnel et cartes explicables.

Le module n'altère ni le classement, ni les points attribués par l'API.
Les opérations réseau et la bibliothèque sont fournies par l'application.
"""
from __future__ import annotations

from typing import Any, Callable

import streamlit as st


GOALS = {
    "Proche de mes goûts": "SIMILAR_SAFE",
    "Quoi lire ensuite": "READ_NEXT",
    "Série terminée / plutôt courte": "SHORT_FINISHED",
}
GOAL_LABELS = {value: label for label, value in GOALS.items()}


def compact_evidence(recommendation: dict[str, Any]) -> str:
    """Explique les facteurs présents, sans inventer de pourcentage de compatibilité."""
    bits: list[str] = []
    themes = recommendation.get("common_themes") or []
    genres = recommendation.get("common_genres") or []
    demographics = recommendation.get("common_demographics") or []
    community = recommendation.get("community_recommended_from") or []
    if themes:
        bits.append("Thèmes en commun : " + ", ".join(themes[:2]))
    if genres:
        bits.append("Genres en commun : " + ", ".join(genres[:2]))
    if demographics:
        bits.append("Public proche : " + ", ".join(demographics[:1]))
    if community:
        bits.append("Aussi conseillé depuis " + ", ".join(community[:2]))
    return " · ".join(bits[:2]) if bits else (
        "Retenu par le moteur de recommandation : consulte le détail pour les critères."
    )


def format_internal_score(score: Any) -> str:
    """Le score de recommandation est en points, pas un taux sur 100."""
    if score is None:
        return "Non calculé"
    try:
        return f"{float(score):.1f} pts"
    except (TypeError, ValueError):
        return "Non calculé"


def format_community_rating(rating: Any) -> str:
    """Note des lecteurs MyAnimeList, distincte du score du moteur."""
    if rating is None:
        return "Non noté"
    try:
        return f"★ {float(rating):.1f}/10"
    except (TypeError, ValueError):
        return "Non noté"


def _show_details(recommendation: dict[str, Any]) -> None:
    """Informations originales de l'API, affichées uniquement sur demande."""
    goal = recommendation.get("recommendation_goal")
    if goal:
        st.write("**Objectif :** " + GOAL_LABELS.get(goal, str(goal)))
    base_score = recommendation.get("base_recommendation_score")
    bonus = recommendation.get("goal_bonus")
    if base_score is not None:
        st.write("**Score avant objectif :** " + format_internal_score(base_score))
    if bonus is not None:
        st.write("**Bonus objectif :** " + format_internal_score(bonus))

    st.write(
        "**Genres communs :** "
        + ", ".join(recommendation.get("common_genres") or ["Non renseignés"])
    )
    st.write(
        "**Thèmes communs :** "
        + ", ".join(recommendation.get("common_themes") or ["Non renseignés"])
    )
    st.write(
        "**Public proche :** "
        + ", ".join(recommendation.get("common_demographics") or ["Non renseigné"])
    )
    community = recommendation.get("community_recommended_from") or []
    if community:
        st.write("**Recommandé par la communauté depuis :** " + ", ".join(community))
        votes = recommendation.get("community_votes")
        if votes is not None:
            st.caption(f"Votes communautaires : {votes}")
    if recommendation.get("volumes") is not None:
        st.write(f"**Volumes :** {recommendation['volumes']}")
    if recommendation.get("chapters") is not None:
        st.write(f"**Chapitres :** {recommendation['chapters']}")
    mismatches = recommendation.get("sensitive_mismatches") or []
    if mismatches:
        st.warning("Éléments pouvant éloigner la recommandation : " + ", ".join(mismatches))
    st.write("**Explication complète du moteur :**")
    st.write(recommendation.get("reason") or "Aucune explication disponible.")


def render_recommendation_cards(
    recommendations: list[dict[str, Any]],
    *,
    context: str,
    get_cover_urls: Callable[[tuple[int, ...]], dict[int, str]],
    display_manga_cover: Callable[..., None],
    get_manga_detail: Callable[[int], dict[str, Any]],
    display_manga_detail: Callable[[dict[str, Any]], None],
) -> None:
    """Grille compacte avec fiche détaillée ouverte sans perdre les résultats."""
    if not recommendations:
        st.info("Aucune recommandation ne correspond aux critères.")
        return

    ids = tuple(int(manga["id"]) for manga in recommendations if manga.get("id"))
    covers = get_cover_urls(ids)
    st.caption(
        "Les scores du moteur sont exprimés en points, jamais en pourcentage. "
        "La note ★ est la note communautaire sur 10."
    )

    for start in range(0, len(recommendations), 2):
        columns = st.columns(2, gap="medium")
        for column, position in zip(columns, range(start, min(start + 2, len(recommendations)))):
            item = recommendations[position]
            with column:
                with st.container(border=True):
                    cover_col, content_col = st.columns([1, 1.15], gap="small")
                    with cover_col:
                        display_manga_cover(item, covers)
                    with content_col:
                        st.markdown(
                            f'<div class="ma-rec-rank">✦ SÉLECTION Nº {position + 1}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("#### " + str(item.get("title") or "Manga inconnu"))
                        st.caption(
                            format_community_rating(item.get("score"))
                            + " · " + str(item.get("manga_type") or "Manga")
                        )
                        st.caption("Score du moteur")
                        st.markdown("**" + format_internal_score(item.get("recommendation_score")) + "**")
                    st.write(compact_evidence(item))
                    goal = item.get("recommendation_goal")
                    if goal in GOAL_LABELS:
                        st.caption("Objectif : " + GOAL_LABELS[goal])

                    with st.expander("Pourquoi ce manga ?"):
                        _show_details(item)

                    manga_id = item.get("id")
                    if manga_id and st.button(
                        "Voir la fiche détaillée →",
                        key=f"ma_rec_open_{context}_{position}_{int(manga_id)}",
                        use_container_width=True,
                    ):
                        st.session_state[f"ma_rec_detail_{context}"] = int(manga_id)

    selected = st.session_state.get(f"ma_rec_detail_{context}")
    if selected and any(item.get("id") == selected for item in recommendations):
        st.divider()
        top, close = st.columns([3, 1])
        with top:
            st.markdown("### Fiche manga sélectionnée")
        with close:
            if st.button("✕ Fermer", key=f"ma_rec_close_{context}"):
                st.session_state.pop(f"ma_rec_detail_{context}", None)
                st.rerun()
        display_manga_detail(get_manga_detail(int(selected)))


def _remember_result(key: str, signature: tuple[Any, ...]) -> None:
    """Invalide les résultats si les préférences ont changé."""
    if st.session_state.get(f"{key}_signature") != signature:
        st.session_state[f"{key}_signature"] = signature
        st.session_state.pop(f"{key}_result", None)
        st.session_state.pop(f"ma_rec_detail_{key}", None)


def _render_library_recommendations(
    *,
    limit: int,
    get_library_recommendations: Callable[..., dict[str, Any]],
    render_cards: Callable[[list[dict[str, Any]], str], None],
) -> None:
    st.caption("Mangadvisor utilise les mangas de ta bibliothèque et tes notes pour choisir.")
    goal_label = st.selectbox("Je cherche…", options=list(GOALS), key="ma_rec_goal")
    options_col, finished_col = st.columns([1, 1])
    with options_col:
        min_score = st.slider(
            "Note communautaire minimale", 0.0, 10.0, 6.8, 0.1,
            key="ma_rec_library_min_score",
        )
    with finished_col:
        only_finished = st.checkbox(
            "Séries terminées uniquement", key="ma_rec_library_finished"
        )
        exclude = st.checkbox(
            "Éviter les thèmes éloignés de mes goûts", key="ma_rec_library_exclude"
        )

    goal = GOALS[goal_label]
    signature = (limit, min_score, only_finished, exclude, goal)
    _remember_result("ma_rec_library", signature)
    if st.button("✨ Trouver mes prochaines lectures", type="primary", key="ma_rec_library_go"):
        st.session_state["ma_rec_library_result"] = get_library_recommendations(
            limit=limit,
            min_score=min_score,
            only_finished=only_finished,
            exclude_sensitive_mismatches=exclude,
            recommendation_goal=goal,
        )

    result = st.session_state.get("ma_rec_library_result")
    if result is None:
        st.info("Ajoute des mangas à ta bibliothèque, puis demande tes recommandations.")
        return

    st.markdown("### Sélection selon tes lectures")
    sources = result.get("positive_sources") or []
    if sources:
        source_titles = [str(m.get("title")) for m in sources if m.get("title")]
        if source_titles:
            st.caption("Mangas utilisés : " + ", ".join(source_titles[:8]))
    excluded = result.get("excluded_library_manga_count")
    if excluded is not None:
        st.caption(f"Mangas de bibliothèque exclus des résultats : {excluded}")
    profile = result.get("profile_summary") or {}
    with st.expander("Voir comment Mangadvisor interprète ma bibliothèque"):
        st.write(profile.get("source_selection_rule") or "Profil non renseigné.")
        for label, field in (
            ("Genres dominants", "top_genres"),
            ("Thèmes dominants", "top_themes"),
            ("Public principal", "top_demographics"),
        ):
            tags = [str(x.get("name")) for x in (profile.get(field) or []) if x.get("name")]
            if tags:
                st.write(f"**{label} :** " + ", ".join(tags[:5]))
    render_cards(result.get("recommendations") or [], "ma_rec_library")


def _render_manual_recommendations(
    *,
    limit: int,
    get_mangas: Callable[..., list[dict[str, Any]]],
    get_profile_recommendations: Callable[..., dict[str, Any]],
    render_cards: Callable[[list[dict[str, Any]], str], None],
) -> None:
    st.caption("Choisis quelques mangas que tu aimes pour obtenir des suggestions.")
    search = st.text_input(
        "Rechercher un titre à ajouter",
        placeholder="Ex. Vinland Saga, Nana, Berserk…",
        key="ma_rec_manual_search",
    )
    catalogue = get_mangas(search=search.strip() or None, limit=100)
    found_titles = [m.get("title") for m in catalogue if m.get("title")]
    # Conserver les titres déjà choisis lors d'une nouvelle recherche.
    selected_before = st.session_state.get("ma_rec_manual_titles", [])
    titles = list(dict.fromkeys([*selected_before, *found_titles]))
    default_titles = [
        title for title in ("Naruto", "Bleach", "Hunter x Hunter") if title in titles
    ] if "ma_rec_manual_titles" not in st.session_state else []
    liked = st.multiselect(
        "Mangas que j'aime (1 à 10)",
        options=titles,
        default=default_titles,
        key="ma_rec_manual_titles",
        help="Recherche un titre, sélectionne-le, puis cherche-en un autre.",
    )
    a, b = st.columns([1, 1])
    with a:
        min_score = st.slider(
            "Note communautaire minimale", 0.0, 10.0, 6.8, 0.1,
            key="ma_rec_manual_min_score",
        )
    with b:
        finished = st.checkbox("Séries terminées uniquement", key="ma_rec_manual_finished")
        exclude = st.checkbox(
            "Éviter les thèmes éloignés de mes goûts", key="ma_rec_manual_exclude"
        )

    signature = (tuple(sorted(liked)), limit, min_score, finished, exclude)
    _remember_result("ma_rec_manual", signature)
    if st.button("✨ Trouver des mangas pour moi", type="primary", key="ma_rec_manual_go"):
        if not liked:
            st.warning("Choisis au moins un manga.")
        elif len(liked) > 10:
            st.warning("Choisis au maximum 10 mangas.")
        else:
            st.session_state["ma_rec_manual_result"] = get_profile_recommendations(
                liked_titles=liked,
                limit=limit,
                min_score=min_score,
                only_finished=finished,
                exclude_sensitive_mismatches=exclude,
            )
    result = st.session_state.get("ma_rec_manual_result")
    if result is None:
        st.info("Choisis quelques titres puis lance la recommandation.")
        return
    sources = [x.get("title") for x in (result.get("sources") or []) if x.get("title")]
    if sources:
        st.caption("Mangas reconnus : " + ", ".join(sources))
    st.markdown("### Des idées selon tes goûts")
    render_cards(result.get("recommendations") or [], "ma_rec_manual")


def render_recommendation_center(
    *,
    limit: int,
    get_mangas: Callable[..., list[dict[str, Any]]],
    get_profile_recommendations: Callable[..., dict[str, Any]],
    get_library_recommendations: Callable[..., dict[str, Any]],
    render_cards: Callable[[list[dict[str, Any]], str], None],
) -> None:
    """Regroupe dans « Pour moi » les deux moteurs de recommandation existants."""
    st.markdown("## Des mangas faits pour toi")
    st.caption("Choisis la source de tes préférences. Les résultats proviennent du moteur existant.")
    mode = st.radio(
        "Comment définir tes goûts ?",
        options=["Ma bibliothèque", "Quelques mangas préférés"],
        horizontal=True,
        key="ma_rec_mode",
    )
    st.caption(f"Jusqu'à {limit} suggestions par recherche (réglage dans la barre latérale).")
    st.divider()
    if mode == "Ma bibliothèque":
        _render_library_recommendations(
            limit=limit,
            get_library_recommendations=get_library_recommendations,
            render_cards=render_cards,
        )
    else:
        _render_manual_recommendations(
            limit=limit,
            get_mangas=get_mangas,
            get_profile_recommendations=get_profile_recommendations,
            render_cards=render_cards,
        )
