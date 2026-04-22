"""Filename and version metadata preparation for Windows builds."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Windows .ico and PyInstaller version metadata resources."
    )
    parser.add_argument("--png", required=True, help="Path to source PNG icon.")
    parser.add_argument("--ico", required=True, help="Path to output ICO file.")
    parser.add_argument(
        "--version-file", required=True, help="Path to PyInstaller version file."
    )
    parser.add_argument(
        "--version", required=True, help="Application version, for example 1.2.3."
    )
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--file-description", required=True)
    parser.add_argument("--internal-name", required=True)
    parser.add_argument("--original-filename", required=True)
    parser.add_argument("--copyright", required=True)
    return parser.parse_args()


def normalize_version(version: str) -> tuple[int, int, int, int]:
    version_parts = [part.strip() for part in version.split(".") if part.strip()]
    if not version_parts:
        raise ValueError("Version must contain at least one numeric component.")

    normalized_parts: list[int] = []
    for part in version_parts[:4]:
        if not part.isdigit():
            raise ValueError(f"Version component '{part}' must be numeric.")
        normalized_parts.append(int(part))

    while len(normalized_parts) < 4:
        normalized_parts.append(0)

    return (
        normalized_parts[0],
        normalized_parts[1],
        normalized_parts[2],
        normalized_parts[3],
    )


def create_icon(png_path: Path, ico_path: Path) -> None:
    ico_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(png_path) as source_image:
        image = source_image.convert("RGBA")
        image.save(
            ico_path,
            format="ICO",
            sizes=[
                (16, 16),
                (24, 24),
                (32, 32),
                (48, 48),
                (64, 64),
                (128, 128),
                (160, 160),
            ],
        )


def create_version_file(
    version_file_path: Path,
    version: str,
    company_name: str,
    product_name: str,
    file_description: str,
    internal_name: str,
    original_filename: str,
    copyright_text: str,
) -> None:
    version_tuple = normalize_version(version)
    version_string = ".".join(str(part) for part in version_tuple)

    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{company_name}'),
            StringStruct('FileDescription', '{file_description}'),
            StringStruct('FileVersion', '{version_string}'),
            StringStruct('InternalName', '{internal_name}'),
            StringStruct('OriginalFilename', '{original_filename}'),
            StringStruct('ProductName', '{product_name}'),
            StringStruct('ProductVersion', '{version_string}'),
            StringStruct('LegalCopyright', '{copyright_text}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

    version_file_path.parent.mkdir(parents=True, exist_ok=True)
    version_file_path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    args = parse_args()

    png_path = Path(args.png).resolve()
    ico_path = Path(args.ico).resolve()
    version_file_path = Path(args.version_file).resolve()

    if not png_path.is_file():
        raise FileNotFoundError(f"PNG icon was not found: {png_path}")

    create_icon(png_path, ico_path)
    create_version_file(
        version_file_path=version_file_path,
        version=args.version,
        company_name=args.company_name,
        product_name=args.product_name,
        file_description=args.file_description,
        internal_name=args.internal_name,
        original_filename=args.original_filename,
        copyright_text=args.copyright,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
