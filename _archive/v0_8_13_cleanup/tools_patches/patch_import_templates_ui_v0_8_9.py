from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


TEMPLATE_FUNCTIONS = '''
def get_library_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Naruto",
            "library_status": "READ",
            "user_score": 8.5,
            "is_favorite": "true",
            "owned_volumes": 72,
            "read_volumes": 72,
            "notes": "Très bon shonen",
        },
        {
            "title": "Bleach",
            "library_status": "READ",
            "user_score": 8,
            "is_favorite": "false",
            "owned_volumes": 74,
            "read_volumes": 74,
            "notes": "",
        },
        {
            "title": "One Piece",
            "library_status": "WANT_TO_READ",
            "user_score": "",
            "is_favorite": "false",
            "owned_volumes": "",
            "read_volumes": "",
            "notes": "",
        },
        {
            "title": "Fairy Tail",
            "library_status": "NOT_INTERESTED",
            "user_score": "",
            "is_favorite": "false",
            "owned_volumes": "",
            "read_volumes": "",
            "notes": "",
        },
    ]


def build_library_template_csv() -> str:
    import csv
    import io

    rows = get_library_template_rows()
    output = io.StringIO()

    fieldnames = [
        "title",
        "library_status",
        "user_score",
        "is_favorite",
        "owned_volumes",
        "read_volumes",
        "notes",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue()


def build_library_template_excel() -> bytes:
    import io

    try:
        import pandas as pd
    except ImportError:
        st.error(
            "La dépendance pandas est absente du conteneur UI. "
            "Ajoute pandas/openpyxl dans les dépendances UI puis rebuild l'image."
        )
        st.stop()

    rows = get_library_template_rows()
    dataframe = pd.DataFrame(rows)

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="bibliotheque")

    return output.getvalue()
'''


DOWNLOAD_BLOCK = '''
        st.write("Télécharger un modèle prêt à remplir :")

        c_template_1, c_template_2 = st.columns(2)

        with c_template_1:
            st.download_button(
                label="Télécharger le modèle CSV",
                data=build_library_template_csv(),
                file_name="modele_bibliotheque_mangadvisor.csv",
                mime="text/csv",
                key="download_library_template_csv",
            )

        with c_template_2:
            st.download_button(
                label="Télécharger le modèle Excel",
                data=build_library_template_excel(),
                file_name="modele_bibliotheque_mangadvisor.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_library_template_excel",
            )

        st.caption(
            "Statuts acceptés : READ, READING, OWNED, WANT_TO_READ, DROPPED, NOT_INTERESTED."
        )

'''


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    if "def get_library_template_rows()" not in text:
        marker = "\n\ndef import_library_csv"

        if marker not in text:
            raise SystemExit("[ERREUR] Impossible de trouver def import_library_csv dans app.py.")

        text = text.replace(
            marker,
            "\n" + TEMPLATE_FUNCTIONS + marker,
            1,
        )

        print("[OK] Fonctions modèles d'import ajoutées.")
    else:
        print("[INFO] Fonctions modèles déjà présentes.")

    old = '''    with st.expander("Format CSV attendu"):
        st.code('''

    new = '''    with st.expander("Format CSV attendu"):
''' + DOWNLOAD_BLOCK + '''        st.code('''

    if old in text and "Télécharger le modèle CSV" not in text:
        text = text.replace(old, new, 1)
        print("[OK] Boutons de téléchargement ajoutés.")
    else:
        print("[INFO] Boutons déjà présents ou bloc différent.")

    text = text.replace(
        "Version V0.8.8 : bibliothèque utilisateur, recommandations, import CSV et Excel.",
        "Version V0.8.9 : bibliothèque utilisateur, recommandations, import CSV/Excel et modèles d'import.",
    )

    UI_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {UI_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_ui")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())