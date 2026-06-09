from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "apps" / "api" / "app" / "main.py"


def main() -> int:
    text = MAIN_PATH.read_text(encoding="utf-8")

    replacements = {
        "cb.title ILIKE '% Part %'": "cb.title ILIKE '%% Part %%'",
        "cb.title ILIKE '%Episode %'": "cb.title ILIKE '%%Episode %%'",
        "cb.title ILIKE '%Tanpenshuu%'": "cb.title ILIKE '%%Tanpenshuu%%'",
    }

    changed = False

    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
            changed = True
            print(f"[OK] Remplacé : {old} -> {new}")
        else:
            print(f"[INFO] Déjà corrigé ou introuvable : {old}")

    if changed:
        MAIN_PATH.write_text(text, encoding="utf-8")
        print(f"[OK] Fichier corrigé : {MAIN_PATH}")
    else:
        print("[INFO] Aucun changement effectué.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())