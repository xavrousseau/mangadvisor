from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


EXCEL_FUNCTIONS = '''
def excel_to_csv_content(uploaded_file: Any) -> str:
    """
    Convertit un fichier Excel .xlsx en contenu CSV en mémoire.

    La logique métier d'import reste côté API via /library/import/csv.
    """
    try:
        import pandas as pd
    except ImportError:
        st.error(
            "La dépendance pandas est absente du conteneur UI. "
            "Ajoute pandas/openpyxl dans les dépendances UI puis rebuild l'image."
        )
        st.stop()

    try:
        dataframe = pd.read_excel(uploaded_file, sheet_name=0, engine="openpyxl")
    except ImportError:
        st.error(
            "La dépendance openpyxl est absente du conteneur UI. "
            "Ajoute openpyxl dans apps/ui/requirements.txt puis rebuild l'image UI."
        )
        st.stop()
    except Exception as exc:
        st.error(f"Impossible de lire le fichier Excel : {exc}")
        st.stop()

    if dataframe.empty:
        st.error("Le fichier Excel ne contient aucune ligne.")
        st.stop()

    dataframe = dataframe.fillna("")

    return dataframe.to_csv(index=False)
'''


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    if "def excel_to_csv_content(" not in text:
        marker = "\n\ndef decode_uploaded_csv"

        if marker not in text:
            raise SystemExit("[ERREUR] Impossible de trouver def decode_uploaded_csv dans app.py.")

        text = text.replace(
            marker,
            "\n" + EXCEL_FUNCTIONS + marker,
            1,
        )

        print("[OK] Fonction Excel ajoutée.")
    else:
        print("[INFO] Fonction Excel déjà présente.")

    text = text.replace(
        '''uploaded_library_file = st.file_uploader(
        "Importer un fichier CSV",
        type=["csv"],''',
        '''uploaded_library_file = st.file_uploader(
        "Importer un fichier CSV ou Excel",
        type=["csv", "xlsx"],''',
    )

    text = text.replace(
        '''"Colonnes reconnues : title, library_status, user_score, is_favorite, "
            "owned_volumes, read_volumes, notes."''',
        '''"Formats acceptés : CSV ou Excel .xlsx. Colonnes reconnues : "
            "title, library_status, user_score, is_favorite, owned_volumes, read_volumes, notes."''',
    )

    old = '''            csv_content = decode_uploaded_csv(uploaded_library_file)

            import_result = import_library_csv('''

    new = '''            uploaded_file_name = uploaded_library_file.name.lower()

            if uploaded_file_name.endswith(".xlsx"):
                csv_content = excel_to_csv_content(uploaded_library_file)
            else:
                csv_content = decode_uploaded_csv(uploaded_library_file)

            import_result = import_library_csv('''

    if old in text and "excel_to_csv_content(uploaded_library_file)" not in text:
        text = text.replace(old, new, 1)
        print("[OK] Lecture Excel branchée dans l'import.")
    else:
        print("[INFO] Lecture Excel déjà branchée ou bloc différent.")

    text = text.replace(
        "Version V0.8.7 : bibliothèque utilisateur, recommandations et import CSV.",
        "Version V0.8.8 : bibliothèque utilisateur, recommandations, import CSV et Excel.",
    )

    UI_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {UI_PATH}")
    print()
    print("Relance / rebuild maintenant :")
    print("  docker compose build mangadvisor_ui")
    print("  docker restart mangadvisor_ui")
    print()
    print("Si le nom du service diffère, utilise ta commande habituelle mangadvisor.cmd.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())