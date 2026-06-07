from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


API_BASE_URL = os.getenv("MANGADVISOR_API_BASE_URL", "http://localhost:8000")
ROOT_DIR = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT_DIR / "docs" / "reports"

ENGINE_VERSION = "V0.7.4"

REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_v0_7_4.md"

# Copie legacy pour ne pas casser les anciens chemins / habitudes
LEGACY_REPORT_PATH = REPORT_DIR / "recommendation_profile_tests_latest.md"

# --------------------------------------------------
# Alias de titres
# --------------------------------------------------
# Objectif :
# éviter de noter "à analyser" un manga attendu simplement parce que
# le titre retourné par Jikan est le titre japonais / original.
#
# Exemples :
# - Yuu☆Yuu☆Hakusho = Yu Yu Hakusho
# - Yotsuba to! = Yotsuba&!
# - Shoujo Shuumatsu Ryokou = Girls' Last Tour
# - Kiseijuu = Parasyte
# - Nanatsu no Taizai = Seven Deadly Sins
# - Yakusoku no Neverland = The Promised Neverland

TITLE_ALIASES_RAW: dict[str, str] = {
    # Shōnen
    "Yuu☆Yuu☆Hakusho": "Yu Yu Hakusho",
    "Yuu Yuu Hakusho": "Yu Yu Hakusho",
    "Yu Yu Hakusho": "Yu Yu Hakusho",
    "Boku no Hero Academia": "My Hero Academia",
    "My Hero Academia": "My Hero Academia",
    "Kimetsu no Yaiba": "Demon Slayer",
    "Demon Slayer": "Demon Slayer",
    "Ao no Exorcist": "Blue Exorcist",
    "Blue Exorcist": "Blue Exorcist",
    "Nanatsu no Taizai": "Seven Deadly Sins",
    "Seven Deadly Sins": "Seven Deadly Sins",

    # Thriller / psychologique
    "Yakusoku no Neverland": "The Promised Neverland",
    "The Promised Neverland": "The Promised Neverland",
    "Boku dake ga Inai Machi": "Erased",
    "Erased": "Erased",
    "Kiseijuu": "Parasyte",
    "Parasyte": "Parasyte",

    # Tranche de vie / contemplatif
    "Yotsuba to!": "Yotsuba&!",
    "Yotsuba&!": "Yotsuba&!",
    "Shoujo Shuumatsu Ryokou": "Girls' Last Tour",
    "Girls' Last Tour": "Girls' Last Tour",

    # Sport
    "Tennis no Oujisama": "The Prince of Tennis",
    "The Prince of Tennis": "The Prince of Tennis",
    "Diamond no Ace": "Ace of Diamond",
    "Ace of Diamond": "Ace of Diamond",
    "Diamond no Ace Act II": "Ace of Diamond Act II",
    "Ace of Diamond Act II": "Ace of Diamond Act II",
}


PROFILES: list[dict[str, Any]] = [
    {
        "name": "Shōnen aventure / combat",
        "liked_titles": ["Naruto", "Bleach", "Hunter x Hunter"],
        "intention": "Action, aventure, combats, progression, pouvoirs, arcs longs.",
        "expected": [
            "Dragon Ball",
            "One Piece",
            "Fullmetal Alchemist",
            "D.Gray-man",
            "Kekkaishi",
            "Yu Yu Hakusho",
            "Black Clover",
            "My Hero Academia",
            "Jujutsu Kaisen",
            "Demon Slayer",
        ],
        "acceptable": [
            "Tsubasa: RESERVoir CHRoNiCLE",
            "Rave",
            "Magi",
            "Fairy Tail",
            "Shaman King",
            "Blue Exorcist",
            "Jigokuraku",
            "Soul Eater",
            "Psyren",
        ],
        "avoid": [
            "Nana",
            "Paradise Kiss",
            "Monster",
            "20th Century Boys",
            "Battle Royale",
        ],
    },
    {
        "name": "Thriller psychologique / mystère",
        "liked_titles": ["Death Note", "Monster", "20th Century Boys"],
        "intention": "Intrigues, manipulation, tension psychologique, mystère, enquête.",
        "expected": [
            "Liar Game",
            "Pluto",
            "Billy Bat",
            "Homunculus",
            "The Promised Neverland",
            "Tomodachi Game",
            "Battle Royale",
        ],
        "acceptable": [
            "Berserk",
            "Dragon Head",
            "Blame!",
            "X",
            "Parasyte",
            "Erased",
            "Ajin",
            "Dorohedoro",
            "Shinseiki Evangelion",
        ],
        "avoid": [
            "Naruto",
            "One Piece",
            "Dragon Ball",
            "Nana",
            "Love Hina",
        ],
    },
    {
        "name": "Seinen sombre / violent / mature",
        "liked_titles": ["Berserk", "Blame!", "Battle Royale"],
        "intention": "Univers sombres, violence, survie, drame, ambiance mature.",
        "expected": [
            "Gantz",
            "Vagabond",
            "Vinland Saga",
            "Kingdom",
            "Claymore",
            "Dragon Head",
            "Monster",
            "20th Century Boys",
        ],
        "acceptable": [
            "Death Note",
            "Parasyte",
            "Dorohedoro",
            "Tokyo Ghoul",
            "Tokyo Ghoul:re",
            "Attack on Titan",
            "Shingeki no Kyojin",
            "I Am a Hero",
            "Chainsaw Man",
            "Fire Punch",
        ],
        "avoid": [
            "Love Hina",
            "Ouran Koukou Host Club",
            "Nana",
            "Lovely★Complex",
            "Hikaru no Go",
        ],
    },
    {
        "name": "Romance / drame / personnages",
        "liked_titles": ["Nana", "Paradise Kiss", "Lovely★Complex"],
        "intention": "Relations humaines, romance, drame, personnages, émotions.",
        "expected": [
            "Fruits Basket",
            "Kimi ni Todoke",
            "Ao Haru Ride",
            "Orange",
            "Honey and Clover",
            "Kare Kano",
            "Kodomo no Omocha",
            "Full Moon wo Sagashite",
        ],
        "acceptable": [
            "Ouran Koukou Host Club",
            "Love Hina",
            "Maison Ikkoku",
            "Skip Beat!",
            "Akatsuki no Yona",
            "Hirunaka no Ryuusei",
            "Yubisaki to Renren",
        ],
        "avoid": [
            "Berserk",
            "Battle Royale",
            "Blame!",
            "Dragon Ball",
            "Hajime no Ippo",
        ],
    },
    {
        "name": "Sport / dépassement de soi",
        "liked_titles": ["Hajime no Ippo", "Slam Dunk", "Eyeshield 21"],
        "intention": "Sport, progression, compétition, rivalités, dépassement de soi.",
        "expected": [
            "Haikyuu!!",
            "Kuroko no Basket",
            "Blue Lock",
            "Captain Tsubasa",
            "Major",
            "Ashita no Joe",
        ],
        "acceptable": [
            "Hikaru no Go",
            "Chihayafuru",
            "Initial D",
            "Yowamushi Pedal",
            "Whistle!",
            "The Prince of Tennis",
            "Cross Game",
            "Ace of Diamond",
            "Ace of Diamond Act II",
            "Ao no Hako",
        ],
        "avoid": [
            "Berserk",
            "Nana",
            "Paradise Kiss",
            "Monster",
            "Death Note",
        ],
    },
    {
        "name": "Aventure longue / monde vaste",
        "liked_titles": ["One Piece", "Hunter x Hunter", "Fullmetal Alchemist"],
        "intention": "Mondes vastes, aventure, voyages, pouvoirs, groupes de personnages.",
        "expected": [
            "Dragon Ball",
            "Naruto",
            "Bleach",
            "D.Gray-man",
            "Magi",
            "Fairy Tail",
            "Rave",
            "Tsubasa: RESERVoir CHRoNiCLE",
        ],
        "acceptable": [
            "Shaman King",
            "Black Clover",
            "Seven Deadly Sins",
            "Kekkaishi",
            "Yu Yu Hakusho",
            "Soul Eater",
            "Tower of God",
            "Pandora Hearts",
            "Psyren",
        ],
        "avoid": [
            "Nana",
            "Paradise Kiss",
            "Monster",
            "Battle Royale",
            "Love Hina",
        ],
    },
    {
        "name": "Mystère / surnaturel",
        "liked_titles": ["Death Note", "Bleach", "xxxHOLiC"],
        "intention": "Surnaturel, mystères, esprits, phénomènes étranges, pouvoirs.",
        "expected": [
            "D.Gray-man",
            "Yu Yu Hakusho",
            "Noragami",
            "Blue Exorcist",
            "Jujutsu Kaisen",
            "Mushishi",
            "Natsume Yuujinchou",
        ],
        "acceptable": [
            "Hikaru no Go",
            "X",
            "Full Moon wo Sagashite",
            "Tsubasa: RESERVoir CHRoNiCLE",
            "The Promised Neverland",
            "Umineko no Naku Koro ni Chiru - Episode 7: Requiem of the Golden Witch",
            "JoJo no Kimyou na Bouken Part 7: Steel Ball Run",
        ],
        "avoid": [
            "Nana",
            "Paradise Kiss",
            "Hajime no Ippo",
            "Slam Dunk",
            "Love Hina",
        ],
    },
    {
        "name": "Tranche de vie / contemplatif",
        "liked_titles": ["Yokohama Kaidashi Kikou", "Mushishi", "Natsume Yuujinchou"],
        "intention": "Histoires calmes, contemplatives, poétiques, ambiance douce.",
        "expected": [
            "Aria",
            "Aqua",
            "Barakamon",
            "Yotsuba&!",
            "Girls' Last Tour",
            "Kino no Tabi",
        ],
        "acceptable": [
            "Honey and Clover",
            "March Comes in Like a Lion",
            "Nana",
            "Solanin",
            "Uchuu Kyoudai",
        ],
        "avoid": [
            "Berserk",
            "Battle Royale",
            "Dragon Ball",
            "Bleach",
            "Gantz",
            "20th Century Boys",
        ],
    },
]


def normalize_text(value: str) -> str:
    """
    Normalise un titre pour comparaison robuste :
    - minuscules ;
    - accents supprimés ;
    - symboles remplacés ;
    - ponctuation supprimée ;
    - espaces compactés.
    """
    value = value.strip()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))

    value = value.lower()
    value = value.replace("☆", " ")
    value = value.replace("★", " ")
    value = value.replace("&", " and ")

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def build_title_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}

    for raw_title, canonical_title in TITLE_ALIASES_RAW.items():
        aliases[normalize_text(raw_title)] = normalize_text(canonical_title)

    return aliases


TITLE_ALIASES = build_title_aliases()


def canonical_title(value: str) -> str:
    normalized = normalize_text(value)
    return TITLE_ALIASES.get(normalized, normalized)


def post_profile_recommendation(liked_titles: list[str], limit: int = 5) -> dict[str, Any]:
    url = f"{API_BASE_URL}/recommendations/profile"

    payload = {
        "liked_titles": liked_titles,
        "limit": limit,
        "min_score": 6.8,
        "only_finished": False,
        "exclude_sensitive_mismatches": False,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erreur HTTP {exc.code} pour {liked_titles}: {body}") from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Impossible d'appeler l'API {url}. Vérifie que mangadvisor_api est lancé."
        ) from exc


def classify_recommendation(title: str, profile: dict[str, Any]) -> tuple[int, str]:
    normalized = canonical_title(title)

    expected = {canonical_title(item) for item in profile["expected"]}
    acceptable = {canonical_title(item) for item in profile["acceptable"]}
    avoid = {canonical_title(item) for item in profile["avoid"]}

    if normalized in expected:
        return 2, "Très attendu"

    if normalized in acceptable:
        return 1, "Acceptable"

    if normalized in avoid:
        return -2, "À éviter"

    return 0, "À analyser"


def status_from_score(score: int) -> str:
    if score >= 8:
        return "Très bon"
    if score >= 5:
        return "Correct"
    if score >= 2:
        return "À améliorer"
    return "Mauvais"


def markdown_list(values: list[str]) -> str:
    if not values:
        return "_Aucun_"

    return ", ".join(values)


def md_cell(value: Any) -> str:
    if value is None:
        return ""

    return str(value).replace("|", "\\|").replace("\n", " ")


def format_score(value: Any) -> str:
    if value is None:
        return ""

    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def build_reason_summary(recommendation: dict[str, Any]) -> str:
    reasons = []

    community_from = recommendation.get("community_recommended_from") or []
    community_votes = recommendation.get("community_votes") or 0

    common_demographics = recommendation.get("common_demographics") or []
    common_themes = recommendation.get("common_themes") or []
    common_genres = recommendation.get("common_genres") or []
    sensitive = recommendation.get("sensitive_mismatches") or []

    editorial_score = recommendation.get("editorial_score")
    community_score = recommendation.get("community_score")
    dominant_intent_score = recommendation.get("dominant_intent_score")
    quality_score = recommendation.get("quality_score")

    if community_from:
        reasons.append(
            f"Communauté: {', '.join(community_from)} ({community_votes} votes)"
        )

    if common_demographics:
        reasons.append(f"Cible: {', '.join(common_demographics)}")

    if common_themes:
        reasons.append(f"Thèmes: {', '.join(common_themes)}")

    if common_genres:
        reasons.append(f"Genres: {', '.join(common_genres)}")

    if sensitive:
        reasons.append(f"Écarts: {', '.join(sensitive)}")

    score_parts = []

    if editorial_score is not None:
        score_parts.append(f"éditorial {format_score(editorial_score)}")

    if community_score is not None:
        score_parts.append(f"communauté {format_score(community_score)}")

    if dominant_intent_score is not None:
        score_parts.append(f"intention {format_score(dominant_intent_score)}")

    if quality_score is not None:
        score_parts.append(f"qualité {format_score(quality_score)}")

    if score_parts:
        reasons.append("Scores: " + ", ".join(score_parts))

    return " ; ".join(reasons)


def main() -> int:
    print("==================================================")
    print("Mangadvisor - Tests automatiques recommandations")
    print("==================================================")
    print(f"API : {API_BASE_URL}")
    print()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        f"# Mangadvisor — Résultats des tests de recommandation {ENGINE_VERSION}",
        "",
        f"Date d’exécution : `{now}`",
        "",
        f"API testée : `{API_BASE_URL}`",
        "",
        "## Synthèse",
        "",
        "| Profil | Score manuel auto | Statut | Sources reconnues |",
        "|---|---:|---|---|",
    ]

    detailed_sections: list[str] = []

    for profile in PROFILES:
        profile_name = profile["name"]
        liked_titles = profile["liked_titles"]

        print(f"Test : {profile_name}")
        print(f"Entrée : {', '.join(liked_titles)}")

        try:
            result = post_profile_recommendation(liked_titles=liked_titles, limit=5)
        except RuntimeError as exc:
            print(f"ERREUR : {exc}")
            print()

            lines.append(f"| {md_cell(profile_name)} | N/A | Erreur | N/A |")
            detailed_sections.extend(
                [
                    f"## {profile_name}",
                    "",
                    f"Erreur lors du test : `{exc}`",
                    "",
                ]
            )
            continue

        sources = result.get("sources", [])
        recommendations = result.get("recommendations", [])

        source_titles = [source.get("title", "") for source in sources]
        total_score = 0

        detail_rows = [
            f"## {profile_name}",
            "",
            f"**Intention lecteur :** {profile['intention']}",
            "",
            f"**Mangas demandés :** {markdown_list(liked_titles)}",
            "",
            f"**Sources reconnues par l’API :** {markdown_list(source_titles)}",
            "",
            "### Recommandations observées",
            "",
            "| Rang | Titre | Score reco | Catégorie | Note manuelle auto | Raisons principales |",
            "|---:|---|---:|---|---:|---|",
        ]

        for index, recommendation in enumerate(recommendations, start=1):
            title = recommendation.get("title", "")
            reco_score = recommendation.get("recommendation_score")
            manual_score, category = classify_recommendation(title, profile)
            total_score += manual_score

            reason_summary = build_reason_summary(recommendation)

            detail_rows.append(
                "| "
                f"{index} | "
                f"{md_cell(title)} | "
                f"{format_score(reco_score)} | "
                f"{md_cell(category)} | "
                f"{manual_score} | "
                f"{md_cell(reason_summary)} "
                "|"
            )

        status = status_from_score(total_score)

        print(f"Score auto : {total_score} ({status})")
        print(f"Sources reconnues : {', '.join(source_titles)}")
        print()

        lines.append(
            f"| {md_cell(profile_name)} | {total_score} | {md_cell(status)} | {md_cell(markdown_list(source_titles))} |"
        )

        detail_rows.extend(
            [
                "",
                f"**Score total automatique :** `{total_score}`",
                "",
                f"**Statut :** `{status}`",
                "",
                "### Référentiel de validation",
                "",
                f"**Très attendus :** {markdown_list(profile['expected'])}",
                "",
                f"**Acceptables :** {markdown_list(profile['acceptable'])}",
                "",
                f"**À éviter :** {markdown_list(profile['avoid'])}",
                "",
            ]
        )

        detailed_sections.extend(detail_rows)

    lines.extend(
        [
            "",
            "## Alias de titres appliqués",
            "",
            "Ces alias évitent de pénaliser le moteur lorsque Jikan retourne un titre original alors que le référentiel utilise un titre anglais ou francisé.",
            "",
            "| Titre retourné possible | Titre de référence |",
            "|---|---|",
        ]
    )

    for raw_title, canonical in sorted(TITLE_ALIASES_RAW.items()):
        if raw_title != canonical:
            lines.append(f"| {md_cell(raw_title)} | {md_cell(canonical)} |")

    lines.extend(
        [
            "",
            "## Détail des profils",
            "",
            *detailed_sections,
            "",
            "## Notes",
            "",
            "Cette notation automatique repose sur des listes de titres attendus / acceptables / à éviter.",
            "Elle ne remplace pas une validation humaine, mais elle permet de repérer rapidement les profils problématiques.",
            "",
        ]
    )

    report_content = "\n".join(lines)

    REPORT_PATH.write_text(report_content, encoding="utf-8")
    LEGACY_REPORT_PATH.write_text(report_content, encoding="utf-8")

    print("==================================================")
    print("Tests terminés")
    print(f"Rapport généré : {REPORT_PATH}")
    print(f"Copie legacy   : {LEGACY_REPORT_PATH}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())