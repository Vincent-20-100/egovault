"""
check_consistency.py
Audit qualité du vault — détecte anomalies sans modifier.
Usage: python scripts/check_consistency.py [--vault PATH]
"""
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# Permet l'exécution directe (python scripts/check_consistency.py) et via -m
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts._config import get_vault_path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML requis : pip install pyyaml")

NOTE_FOLDERS = ["notes"]
REQUIRED_FIELDS = {"date_creation", "date_modification", "tags", "note_type", "source_type", "depth"}
VALID_NOTE_TYPES   = {"idee", "synthese", "reflexion", "concept"}
VALID_SOURCE_TYPES = {"youtube", "audio", "video", "pdf", "web", "livre", "cours", "personnel"}
VALID_DEPTHS       = {"atomique", "note", "approfondi"}
ACCENT_PATTERN = re.compile(r"[àâäéèêëîïôöùûüç]")


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}, text
    try:
        return yaml.safe_load(match.group(1)) or {}, text
    except yaml.YAMLError:
        return {}, text


def all_notes(vault_path):
    for folder in NOTE_FOLDERS:
        p = vault_path / folder
        if p.exists():
            for note in p.glob("*.md"):
                if note.name == "_context.md":
                    continue
                yield note


def run_checks(vault_path: Path) -> dict:
    issues = defaultdict(list)

    for note in all_notes(vault_path):
        fm, text = parse_frontmatter(note)
        rel = note.relative_to(vault_path)

        # Champs manquants
        for field in REQUIRED_FIELDS:
            if field not in fm:
                issues["missing_fields"].append(f"{rel} — champ manquant : '{field}'")

        # Valeurs invalides
        for field, valid_set in [
            ("note_type",   VALID_NOTE_TYPES),
            ("source_type", VALID_SOURCE_TYPES),
            ("depth",       VALID_DEPTHS),
        ]:
            val = fm.get(field)
            if val and val not in valid_set:
                issues["invalid_values"].append(
                    f"{rel} — {field}: '{val}' invalide (autorisé: {sorted(valid_set)})"
                )

        # Tags avec accents ou majuscules
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            if ACCENT_PATTERN.search(tag) or tag != tag.lower():
                issues["bad_tags"].append(f"{rel} — tag mal formaté : '{tag}'")

        # Liens cassés [[...]]
        for link in re.findall(r"\[\[([^\]]+)\]\]", text):
            clean = link.split("|")[0].strip()
            candidates = list(vault_path.rglob(f"{Path(clean).name}.md"))
            if not candidates and not (vault_path / clean).exists():
                issues["broken_links"].append(f"{rel} — lien cassé : '[[{link}]]'")

    return dict(issues)


def print_report(issues: dict):
    if not any(issues.values()):
        print("Aucune anomalie détectée.")
        return
    for category, items in issues.items():
        if items:
            print(f"\n[{category}]")
            for item in items:
                print(f"  - {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default=".", help="Chemin racine du vault")
    args = parser.parse_args()
    vault_path = get_vault_path() if args.vault == "." else Path(args.vault)
    issues = run_checks(vault_path)
    print_report(issues)
