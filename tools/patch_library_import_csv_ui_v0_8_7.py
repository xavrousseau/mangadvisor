from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "ui" / "app" / "app.py"


IMPORT_FUNCTIONS = '''
def import_library_csv(
    csv_content: str,
    delimiter: str = ",",
    default_status: str = "WANT_TO_READ",
    dry_run: bool = True,
) -> dict[str, Any]:
    return call_api_post(
        "/library/import/csv",
        payload={
            "csv_content": csv_content,
            "delimiter": delimiter,
            "default_status": default_status,
            "dry_run": dry_run,
        },
    )


def decode_uploaded_csv(uploaded_file: Any) -> str:
    raw_content = uploaded_file.getvalue()

    try:
        return raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw_content.decode("latin-1")
'''


IMPORT_UI_BLOCK = '''
    st.subheader("1. Importer une bibliothèque")

    uploaded_library_file = st.file_uploader(
        "Importer un fichier CSV",
        type=["csv"],
        help=(
            "Colonnes reconnues : title, library_status, user_score, is_favorite, "
            "owned_volumes, read_volumes, notes."
        ),
        key="library_csv_uploader",
    )

    with st.expander("Format CSV attendu"):
        st.code(
            "title,library_status,user_score,is_favorite,owned_volumes,read_volumes,notes\\n"
            "Naruto,READ,8.5,true,72,72,Très bon shonen\\n"
            "Bleach,READ,8,false,74,74,\\n"
            "One Piece,WANT_TO_READ,,false,,,\\n"
            "Fairy Tail,NOT_INTERESTED,,false,,,",
            language="csv",
        )

    c_import_1, c_import_2, c_import_3 = st.columns(3)

    with c_import_1:
        csv_delimiter_label = st.selectbox(
            "Séparateur",
            options=["Virgule ,", "Point-virgule ;"],
            index=0,
            key="library_csv_delimiter_label",
        )

    with c_import_2:
        csv_default_status_label = st.selectbox(
            "Statut par défaut si vide",
            options=list(LIBRARY_STATUS_OPTIONS.keys()),
            index=list(LIBRARY_STATUS_OPTIONS.keys()).index("Envie de lire"),
            key="library_csv_default_status_label",
        )

    with c_import_3:
        csv_dry_run = st.checkbox(
            "Simulation uniquement",
            value=True,
            help="Si coché, teste l'import sans écrire en base.",
            key="library_csv_dry_run",
        )

    csv_delimiter = "," if csv_delimiter_label == "Virgule ," else ";"
    csv_default_status = LIBRARY_STATUS_OPTIONS[csv_default_status_label]

    if uploaded_library_file is not None:
        if st.button("Importer le CSV", type="primary", key="library_csv_import_button"):
            csv_content = decode_uploaded_csv(uploaded_library_file)

            import_result = import_library_csv(
                csv_content=csv_content,
                delimiter=csv_delimiter,
                default_status=csv_default_status,
                dry_run=csv_dry_run,
            )

            if csv_dry_run:
                st.info("Simulation terminée : aucune donnée n'a été écrite en base.")
            else:
                st.success("Import terminé : la bibliothèque a été mise à jour.")

            c_result_1, c_result_2, c_result_3, c_result_4 = st.columns(4)

            with c_result_1:
                st.metric("Lignes CSV", import_result.get("total_rows", 0))

            with c_result_2:
                st.metric("Mangas trouvés", import_result.get("matched_count", 0))

            with c_result_3:
                st.metric("Non trouvés", import_result.get("not_found_count", 0))

            with c_result_4:
                st.metric("Erreurs", import_result.get("error_count", 0))

            imported_items = import_result.get("imported_items") or []
            not_found_items = import_result.get("not_found_items") or []
            error_items = import_result.get("error_items") or []

            if imported_items:
                with st.expander("Voir les lignes importées / simulées"):
                    for item in imported_items:
                        st.write(
                            f"- ligne {item.get('line')} : "
                            f"**{item.get('requested_title')}** → "
                            f"{item.get('matched_title')} "
                            f"({item.get('library_status')})"
                        )

            if not_found_items:
                with st.expander("Voir les titres non trouvés"):
                    for item in not_found_items:
                        st.warning(
                            f"ligne {item.get('line')} : {item.get('title')}"
                        )

            if error_items:
                with st.expander("Voir les erreurs"):
                    for item in error_items:
                        st.error(
                            f"ligne {item.get('line')} : {item.get('error')}"
                        )

    st.divider()

'''


def main() -> int:
    text = UI_PATH.read_text(encoding="utf-8")

    if "def import_library_csv(" not in text:
        marker = "\n\ndef get_library_profile()"
        if marker not in text:
            raise SystemExit("[ERREUR] Impossible de trouver def get_library_profile().")

        text = text.replace(
            marker,
            "\n" + IMPORT_FUNCTIONS + marker,
            1,
        )

        print("[OK] Fonctions import CSV ajoutées.")
    else:
        print("[INFO] Fonctions import CSV déjà présentes.")

    if "Importer une bibliothèque" not in text:
        marker = '    st.subheader("1. Ajouter ou mettre à jour un manga dans ma bibliothèque")'

        if marker not in text:
            raise SystemExit(
                '[ERREUR] Impossible de trouver la section "1. Ajouter ou mettre à jour".'
            )

        text = text.replace(
            marker,
            IMPORT_UI_BLOCK + marker.replace('"1.', '"2.'),
            1,
        )

        text = text.replace(
            '    st.subheader("2. Ma bibliothèque")',
            '    st.subheader("3. Ma bibliothèque")',
        )

        text = text.replace(
            '    st.subheader("3. Recommandations à partir de ma bibliothèque")',
            '    st.subheader("4. Recommandations à partir de ma bibliothèque")',
        )

        print("[OK] Bloc import CSV ajouté dans l’onglet bibliothèque.")
    else:
        print("[INFO] Bloc import CSV déjà présent.")

    text = text.replace(
        "Version V0.8 : bibliothèque utilisateur et recommandations manga depuis ton profil de lecture.",
        "Version V0.8.7 : bibliothèque utilisateur, recommandations et import CSV.",
    )

    UI_PATH.write_text(text, encoding="utf-8")

    print(f"[OK] Fichier mis à jour : {UI_PATH}")
    print()
    print("Relance maintenant :")
    print("  docker restart mangadvisor_ui")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())