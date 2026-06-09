from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"
TEST_PATH = ROOT / "pipelines" / "engine" / "scripts" / "run_recommendation_profile_tests.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"[ERREUR] Bloc introuvable : {label}")
    return text.replace(old, new, 1)


def patch_main_py() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")

    old = """    exclude_sensitive_mismatches: bool = Field(
        default=False,
        description="Si true, exclut les mangas avec des éléments qui peuvent éloigner la recommandation.",
    )"""

    new = """    exclude_sensitive_mismatches: bool = Field(
        default=False,
        description="Si true, exclut les mangas avec des éléments qui peuvent éloigner la recommandation.",
    )
    recommendation_mode: str = Field(
        default="auto",
        description=(
            "Mode d'intention utilisateur. Valeurs possibles : "
            "auto, surnaturel_pouvoirs, thriller_psychologique, tranche_de_vie, "
            "sport, romance, seinen_sombre, aventure_action."
        ),
    )"""

    text = replace_once(text, old, new, "ProfileRecommendationRequest.recommendation_mode")

    marker = """@app.post("/recommendations/profile")"""

    helper = r'''
def normalize_recommendation_mode(value: str | None) -> str:
    allowed_modes = {
        "auto",
        "surnaturel_pouvoirs",
        "thriller_psychologique",
        "tranche_de_vie",
        "sport",
        "romance",
        "seinen_sombre",
        "aventure_action",
    }

    mode = (value or "auto").strip().lower()

    if mode not in allowed_modes:
        return "auto"

    return mode


def has_any(values: list[str], expected: set[str]) -> bool:
    return any(value in expected for value in values)


def rerank_profile_recommendations(
    rows: list[dict[str, Any]],
    recommendation_mode: str,
) -> list[dict[str, Any]]:
    """
    Réordonne les recommandations selon une intention utilisateur explicite.

    Important :
    - le score SQL reste la base ;
    - le bonus de mode est lisible dans reco_mode_bonus ;
    - on ne l'applique que si l'utilisateur choisit un mode autre que auto.
    """
    mode = normalize_recommendation_mode(recommendation_mode)

    if mode == "auto":
        return rows

    for row in rows:
        genres = set(row.get("common_genres") or [])
        themes = set(row.get("common_themes") or [])
        demographics = set(row.get("common_demographics") or [])
        sensitive = set(row.get("sensitive_mismatches") or [])
        community_from = row.get("community_recommended_from") or []

        all_tags = genres | themes | demographics

        bonus = 0.0

        if mode == "surnaturel_pouvoirs":
            has_supernatural = has_any(
                list(all_tags),
                {"Supernatural", "Urban Fantasy", "Super Power", "Mythology"},
            )
            has_action = has_any(
                list(all_tags),
                {"Action", "Adventure", "Martial Arts", "Fantasy"},
            )
            has_shounen = "Shounen" in demographics

            if has_supernatural:
                bonus += 35
            if has_supernatural and has_action:
                bonus += 25
            if has_supernatural and has_shounen:
                bonus += 25
            if has_supernatural and has_action and has_shounen:
                bonus += 25
            if len(community_from) >= 2:
                bonus += 18
            elif len(community_from) == 1:
                bonus += 8

            if "Gore" in sensitive:
                bonus -= 45
            if "Romance" in sensitive:
                bonus -= 30
            if "Ecchi" in sensitive:
                bonus -= 35
            if "Harem" in sensitive:
                bonus -= 30

            title = row.get("title") or ""
            if "Tanpenshuu" in title or " Part " in title or "Episode " in title:
                bonus -= 25

        elif mode == "thriller_psychologique":
            if has_any(list(all_tags), {"Psychological", "Mystery", "Suspense"}):
                bonus += 35
            if "Seinen" in demographics:
                bonus += 15
            if has_any(list(all_tags), {"Action", "Adventure"}) and not has_any(
                list(all_tags), {"Psychological", "Mystery", "Suspense"}
            ):
                bonus -= 20

        elif mode == "tranche_de_vie":
            if has_any(list(all_tags), {"Iyashikei", "Slice of Life"}):
                bonus += 45
            if has_any(list(all_tags), {"Gore", "Horror", "Survival"}):
                bonus -= 45
            if has_any(list(all_tags), {"Action", "Adventure"}) and not has_any(
                list(all_tags), {"Iyashikei", "Slice of Life"}
            ):
                bonus -= 20

        elif mode == "sport":
            if has_any(list(all_tags), {"Sports", "Team Sports", "Combat Sports"}):
                bonus += 50
            if "Romance" in sensitive:
                bonus -= 15

        elif mode == "romance":
            if has_any(list(all_tags), {"Romance", "Love Polygon", "Shoujo", "Josei"}):
                bonus += 40
            if has_any(list(all_tags), {"Gore", "Horror", "Survival"}):
                bonus -= 45

        elif mode == "seinen_sombre":
            if has_any(list(all_tags), {"Seinen", "Gore", "Horror", "Survival", "Psychological"}):
                bonus += 35
            if has_any(list(all_tags), {"Shoujo", "Romance", "Slice of Life"}):
                bonus -= 25

        elif mode == "aventure_action":
            if has_any(list(all_tags), {"Action", "Adventure", "Fantasy", "Super Power"}):
                bonus += 35
            if "Shounen" in demographics:
                bonus += 20
            if has_any(list(all_tags), {"Gore", "Horror"}) and "Shounen" not in demographics:
                bonus -= 20

        row["reco_mode"] = mode
        row["reco_mode_bonus"] = round(bonus, 1)
        row["recommendation_score"] = round(
            float(row.get("recommendation_score") or 0) + bonus,
            1,
        )

    rows.sort(
        key=lambda item: (
            float(item.get("recommendation_score") or 0),
            int(item.get("community_source_count") or 0),
            int(item.get("community_votes") or 0),
            -int(item.get("popularity") or 999999),
        ),
        reverse=True,
    )

    return rows


'''

    text = replace_once(text, marker, helper + "\n\n" + marker, "insertion helpers mode intention")

    text = replace_once(
        text,
        "        LIMIT %(limit)s;",
        "        LIMIT %(internal_limit)s;",
        "SQL internal limit",
    )

    old = """"limit": payload.limit,"""
    new = """"limit": payload.limit,
                    "internal_limit": max(payload.limit * 10, 50),"""

    text = replace_once(text, old, new, "param internal_limit")

    old = """            rows = cur.fetchall()

    source_titles = [source["title"] for source in sources]

    recommendations = []"""

    new = """            rows = cur.fetchall()

    rows = rerank_profile_recommendations(
        rows=list(rows),
        recommendation_mode=payload.recommendation_mode,
    )
    rows = rows[: payload.limit]

    source_titles = [source["title"] for source in sources]

    recommendations = []"""

    text = replace_once(text, old, new, "rerank post SQL")

    old = """        if dominant_intent_score > 0:
            reason_parts.append(
                f"intention dominante du profil respectée (+{dominant_intent_score:.1f})"
            )"""

    new = """        reco_mode = row.get("reco_mode") or "auto"
        reco_mode_bonus = row.get("reco_mode_bonus") or 0

        if reco_mode != "auto":
            reason_parts.append(
                f"mode choisi : {reco_mode} ({reco_mode_bonus:+.1f})"
            )

        if dominant_intent_score > 0:
            reason_parts.append(
                f"intention dominante du profil respectée (+{dominant_intent_score:.1f})"
            )"""

    text = replace_once(text, old, new, "reason mode choisi")

    MAIN_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] API patchée : {MAIN_PATH}")


def patch_ui_py() -> None:
    text = UI_PATH.read_text(encoding="utf-8")

    old = """def get_profile_recommendations(
    liked_titles: list[str],
    limit: int = 5,
    min_score: float = 6.8,
    only_finished: bool = False,
    exclude_sensitive_mismatches: bool = False,
) -> dict[str, Any]:"""

    new = """def get_profile_recommendations(
    liked_titles: list[str],
    limit: int = 5,
    min_score: float = 6.8,
    only_finished: bool = False,
    exclude_sensitive_mismatches: bool = False,
    recommendation_mode: str = "auto",
) -> dict[str, Any]:"""

    text = replace_once(text, old, new, "UI function signature")

    old = """"exclude_sensitive_mismatches": exclude_sensitive_mismatches,"""
    new = """"exclude_sensitive_mismatches": exclude_sensitive_mismatches,
            "recommendation_mode": recommendation_mode,"""

    text = replace_once(text, old, new, "UI payload mode")

    old = """    profile_exclude_sensitive = st.checkbox(
        "Exclure les recommandations avec éléments éloignants",
        value=False,
        help="Exclut par exemple certains écarts comme Gore, Harem, Ecchi, Romance, School selon ton profil.",
    )

    st.divider()"""

    new = """    profile_exclude_sensitive = st.checkbox(
        "Exclure les recommandations avec éléments éloignants",
        value=False,
        help="Exclut par exemple certains écarts comme Gore, Harem, Ecchi, Romance, School selon ton profil.",
    )

    recommendation_mode_label = st.selectbox(
        "Ce que tu veux retrouver en priorité",
        options=[
            "Auto",
            "Surnaturel / pouvoirs",
            "Thriller / psychologique",
            "Tranche de vie / contemplatif",
            "Sport",
            "Romance / drame",
            "Seinen sombre",
            "Aventure / action",
        ],
        index=0,
        help="Permet de préciser l'intention quand un profil peut être interprété de plusieurs façons.",
    )

    recommendation_mode_map = {
        "Auto": "auto",
        "Surnaturel / pouvoirs": "surnaturel_pouvoirs",
        "Thriller / psychologique": "thriller_psychologique",
        "Tranche de vie / contemplatif": "tranche_de_vie",
        "Sport": "sport",
        "Romance / drame": "romance",
        "Seinen sombre": "seinen_sombre",
        "Aventure / action": "aventure_action",
    }

    profile_recommendation_mode = recommendation_mode_map[recommendation_mode_label]

    st.divider()"""

    text = replace_once(text, old, new, "UI selectbox mode")

    old = """            exclude_sensitive_mismatches=profile_exclude_sensitive,
        )"""

    new = """            exclude_sensitive_mismatches=profile_exclude_sensitive,
            recommendation_mode=profile_recommendation_mode,
        )"""

    text = replace_once(text, old, new, "UI call mode")

    UI_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] UI patchée : {UI_PATH}")


def patch_tests_py() -> None:
    text = TEST_PATH.read_text(encoding="utf-8")

    text = text.replace('ENGINE_VERSION = "V0.7.4"', 'ENGINE_VERSION = "V0.8.0"')
    text = text.replace(
        'REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_7_4.md"',
        'REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_8_0.md"',
    )

    old = """"intention": "Surnaturel, mystères, esprits, phénomènes étranges, pouvoirs.",
        "expected": ["""

    new = """"intention": "Surnaturel, mystères, esprits, phénomènes étranges, pouvoirs.",
        "recommendation_mode": "surnaturel_pouvoirs",
        "expected": ["""

    text = replace_once(text, old, new, "test profile mode surnaturel")

    old = """def post_profile_recommendation(liked_titles: list[str], limit: int = 5) -> dict[str, Any]:"""
    new = """def post_profile_recommendation(
    liked_titles: list[str],
    limit: int = 5,
    recommendation_mode: str = "auto",
) -> dict[str, Any]:"""

    text = replace_once(text, old, new, "test function signature")

    old = """"exclude_sensitive_mismatches": False,"""
    new = """"exclude_sensitive_mismatches": False,
        "recommendation_mode": recommendation_mode,"""

    text = replace_once(text, old, new, "test payload mode")

    old = """            result = post_profile_recommendation(liked_titles=liked_titles, limit=5)"""
    new = """            result = post_profile_recommendation(
                liked_titles=liked_titles,
                limit=5,
                recommendation_mode=profile.get("recommendation_mode", "auto"),
            )"""

    text = replace_once(text, old, new, "test call mode")

    TEST_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] Tests patchés : {TEST_PATH}")


def main() -> int:
    patch_main_py()
    patch_ui_py()
    patch_tests_py()

    print()
    print("Patch intention utilisateur terminé.")
    print("Relance :")
    print("  docker restart mangadvisor_api")
    print("  docker restart mangadvisor_ui")
    print("  cmd\\run-recommendation-tests.cmd")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())