"""
scripts/check_duplicates.py
Détecte les notes potentiellement dupliquées dans le vault.

Deux critères de détection :
  1. Notes numérotées : slug.md + slug-2.md (même base, suffixe numérique)
  2. Slugs proches : notes dont les slugs partagent >= N mots consécutifs

Output : rapport lisible, l'humain décide toujours.

Usage :
  python scripts/check_duplicates.py [--vault PATH] [--min-words 3]
"""
import re
import sys
import argparse
from pathlib import Path

from scripts._config import get_vault_path

NUMBERED = re.compile(r"^(.+)-(\d+)$")


def read_docstring(path: Path) -> str:
    """Retourne le docstring (premier bloc de texte après le frontmatter)."""
    text = path.read_text(encoding="utf-8")
    # Skip frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    # First non-empty lines up to first heading
    lines = []
    for line in text.strip().splitlines():
        if line.startswith("#"):
            break
        if line.startswith(">"):
            lines.append(line.lstrip("> ").strip())
        elif line.strip():
            lines.append(line.strip())
        elif lines:
            break
    return " ".join(lines)[:200]


def find_numbered_pairs(notes_dir: Path) -> list[tuple[Path, Path]]:
    """Trouve les paires slug.md + slug-2.md."""
    stems = {f.stem: f for f in notes_dir.glob("*.md") if not f.name.startswith("_")}
    pairs = []
    for stem, path in sorted(stems.items()):
        m = NUMBERED.match(stem)
        if m:
            base = m.group(1)
            if base in stems:
                pairs.append((stems[base], path))
    return pairs


def find_close_slugs(notes_dir: Path, min_words: int = 3) -> list[tuple[Path, Path]]:
    """Trouve les notes dont les slugs partagent >= min_words mots consécutifs."""
    notes = sorted(f for f in notes_dir.glob("*.md") if not f.name.startswith("_"))
    close = []
    for i, a in enumerate(notes):
        words_a = a.stem.split("-")
        for b in notes[i + 1:]:
            words_b = b.stem.split("-")
            # Chercher une sous-séquence commune de longueur >= min_words
            shared = _longest_common_subseq(words_a, words_b)
            if shared >= min_words:
                close.append((a, b))
    return close


def _longest_common_subseq(a: list, b: list) -> int:
    """Retourne la longueur de la plus longue sous-séquence contiguë commune."""
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def report(vault_path: Path, min_words: int):
    notes_dir = vault_path / "notes"
    if not notes_dir.exists():
        sys.exit(f"Dossier notes/ introuvable : {notes_dir}")

    numbered = find_numbered_pairs(notes_dir)
    close = find_close_slugs(notes_dir, min_words)

    # Déduplique : retirer les paires close qui sont déjà dans numbered
    numbered_set = {(a.stem, b.stem) for a, b in numbered}
    close = [(a, b) for a, b in close if (a.stem, b.stem) not in numbered_set]

    print("=== RAPPORT DOUBLONS ===\n")

    if numbered:
        print(f"[Notes numerotees] ({len(numbered)} paire(s)) :")
        for a, b in numbered:
            print(f"\n  {a.name}")
            print(f"  {b.name}")
            print(f"    A: {read_docstring(a)[:100]}")
            print(f"    B: {read_docstring(b)[:100]}")
        print()

    if close:
        print(f"[Slugs proches >= {min_words} mots communs] ({len(close)} paire(s)) :")
        for a, b in close:
            print(f"\n  {a.name}")
            print(f"  {b.name}")
            print(f"    A: {read_docstring(a)[:100]}")
            print(f"    B: {read_docstring(b)[:100]}")
        print()

    if not numbered and not close:
        print("Aucun doublon detecte.")
    else:
        print("Actions possibles (manuelles) :")
        print("  - Renommer vers un slug plus precis si sujets distincts")
        print("  - Fusionner si meme sujet, angles complementaires")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecte les notes potentiellement dupliquees.")
    parser.add_argument("--vault", default=None)
    parser.add_argument("--min-words", type=int, default=3,
                        help="Nombre min de mots consécutifs communs pour signaler (défaut: 3)")
    args = parser.parse_args()

    vault = Path(args.vault).resolve() if args.vault else get_vault_path()
    report(vault, args.min_words)
