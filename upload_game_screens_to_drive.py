#!/usr/bin/env python3
"""Copy selected screenshot cells from a local Excel workbook into a local test/ folder.

This utility is meant for spreadsheets where:
  * column A contains the game name
  * column C contains the screenshot image or a path to the image

It processes only the rows specified via --rows and skips rows without a screenshot.
The copied image name is derived from the game name in column A.

Usage:
  python3 upload_game_screens_to_drive.py --xlsx games.xlsx --rows 2,5,9-12 --game-col A --image-col C --output-dir test
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from openpyxl import load_workbook

try:
    from openpyxl_image_loader import SheetImageLoader
except Exception:  # pragma: no cover
    SheetImageLoader = None


def parse_excel_column(column: str) -> int:
    """Convert A/B/C style column references to 1-based indexes."""
    col = column.strip().upper()
    if not col:
        raise ValueError("Column name cannot be empty")

    if col.isdigit():
        idx = int(col)
        if idx <= 0:
            raise ValueError(f"Invalid numeric column: {col}")
        return idx

    value = 0
    for ch in col:
        if ch < 'A' or ch > 'Z':
            raise ValueError(f"Invalid column name: {column}")
        value = value * 26 + (ord(ch) - 64)
    return value


def col_to_cell_name(column: str, row_number: int) -> str:
    idx = parse_excel_column(column)
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row_number}"


def parse_row_list(value: str) -> List[int]:
    result: List[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_s, end_s = item.split("-", 1)
            try:
                start = int(start_s)
                end = int(end_s)
            except ValueError as exc:
                raise ValueError(f"Invalid row range: {item}") from exc
            if end < start:
                start, end = end, start
            result.extend(range(start, end + 1))
        else:
            try:
                result.append(int(item))
            except ValueError as exc:
                raise ValueError(f"Invalid row number: {item}") from exc
    return result


def sanitize_filename(value: str, row_number: int) -> str:
    text = str(value).strip()
    text = re.sub(r"[_\s]+", "-", text)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip(".-")
    return text or f"game_{row_number}"


def cell_ref_to_row_col(cell_ref: str) -> Tuple[int, int]:
    match = re.match(r"^\s*([A-Za-z]+)(\d+)\s*$", cell_ref)
    if not match:
        raise ValueError(f"Invalid cell reference: {cell_ref!r}")
    col_name, row_text = match.groups()
    col_number = 0
    for ch in col_name.upper():
        col_number = col_number * 26 + (ord(ch) - 64)
    return col_number, int(row_text)


def workbook_image_for_cell(ws, cell_ref: str):
    """Return a worksheet image object for a cell, including pasted Picture objects anchored to a row/column."""
    try:
        target_col, target_row = cell_ref_to_row_col(cell_ref)
    except ValueError:
        return None

    for img in getattr(ws, "_images", []):
        anchor = getattr(img, "anchor", None)
        if anchor is None or not hasattr(anchor, "_from"):
            continue
        image_col = anchor._from.col + 1
        image_row = anchor._from.row + 1
        if image_col == target_col and image_row == target_row:
            return img

    row_matches = []
    for img in getattr(ws, "_images", []):
        anchor = getattr(img, "anchor", None)
        if anchor is None or not hasattr(anchor, "_from"):
            continue
        image_row = anchor._from.row + 1
        if image_row == target_row:
            row_matches.append(img)
    if row_matches:
        return row_matches[0]
    return None


def build_output_filename(game_name: str, row_number: int, speed_value: object = None) -> str:
    """Create a filename based on the game name and the spin-speed threshold."""
    base_name = sanitize_filename(game_name, row_number)
    if speed_value is None:
        return base_name

    try:
        speed = float(str(speed_value).strip())
    except (TypeError, ValueError):
        return base_name

    if speed <= 2.5:
        return f"{base_name}_2_5_seconds"
    if speed >= 3:
        return f"{base_name}_3_seconds"
    return base_name


def speed_bucket_name(speed_value: object) -> str:
    if speed_value is None:
        return "unknown_spin_speed"

    try:
        speed = float(str(speed_value).strip())
    except (TypeError, ValueError):
        return "unknown_spin_speed"

    if speed <= 2.5:
        return "2_5_spin_speed"
    if speed >= 3:
        return "3_spin_speed"
    return "normal_spin_speed"


def debug_sheet_summary(ws, cell_ref: Optional[str] = None, *, verbose: bool = False) -> None:
    """Print a compact diagnostic summary for an Excel sheet and optional target cell."""
    image_count = len(getattr(ws, "_images", []))
    print(f"Sheet '{ws.title}' debug: max_row={ws.max_row}, max_column={ws.max_column}, embedded_images={image_count}")
    if cell_ref:
        cell = ws[cell_ref]
        value = cell.value
        print(f"Cell {cell_ref}: value={value!r}, type={type(value).__name__}")

    if verbose and getattr(ws, "_images", None):
        for idx, image in enumerate(getattr(ws, "_images", []), start=1):
            anchor = getattr(image, "anchor", None)
            print(f"  Image #{idx}: anchor={anchor!r}, type={type(image).__name__}")


def image_bytes_from_cell(ws, cell_ref: str) -> Optional[Tuple[bytes, str]]:
    """Return (bytes, extension) for an embedded Excel image or a file path."""
    embedded_image = workbook_image_for_cell(ws, cell_ref)
    if embedded_image is not None:
        image_data = embedded_image._data()
        if isinstance(image_data, bytes):
            return image_data, (embedded_image.format or "png").lower()
        if hasattr(embedded_image, "ref") and embedded_image.ref is not None:
            ref = embedded_image.ref
            if hasattr(ref, "getvalue"):
                return ref.getvalue(), (embedded_image.format or "png").lower()
            if hasattr(ref, "read"):
                ref.seek(0)
                return ref.read(), (embedded_image.format or "png").lower()

    if SheetImageLoader is not None:
        try:
            image = SheetImageLoader(ws).get(cell_ref)
            if image is not None:
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                return buffer.getvalue(), "png"
        except Exception:
            pass
    elif not ws[cell_ref].value:
        raise RuntimeError(
            "Embedded worksheet images require the optional package 'openpyxl-image-loader'. "
            "Install it with: pip install openpyxl-image-loader"
        )

    cell = ws[cell_ref]
    value = cell.value
    if value is None:
        return None

    if isinstance(value, bytes):
        return value, "png"

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        path = Path(value).expanduser()
        if path.exists() and path.is_file():
            return path.read_bytes(), path.suffix.lstrip(".") or "png"

        if value.startswith(("http://", "https://")):
            import urllib.request

            with urllib.request.urlopen(value, timeout=30) as response:
                data = response.read()
            suffix = Path(value.split("?", 1)[0]).suffix or ".png"
            return data, suffix.lstrip(".") or "png"

    return None


def copy_image_to_local_folder(
    ws,
    game_name: str,
    row_number: int,
    image_cell_ref: str,
    output_dir: Path,
    speed_cell_ref: Optional[str] = None,
) -> str:
    image_data = image_bytes_from_cell(ws, image_cell_ref)
    if image_data is None:
        raise FileNotFoundError(f"No screenshot found at cell {image_cell_ref}")

    image_bytes, extension = image_data
    speed_value = None
    if speed_cell_ref:
        speed_value = ws[speed_cell_ref].value

    basename = build_output_filename(game_name, row_number, speed_value)
    output_dir.mkdir(parents=True, exist_ok=True)

    bucket = speed_bucket_name(ws[speed_cell_ref].value if speed_cell_ref else None)
    destination_dir = output_dir / bucket
    destination_dir.mkdir(parents=True, exist_ok=True)

    target_name = f"{basename}.{extension or 'png'}"
    target_path = destination_dir / target_name
    if target_path.exists():
        target_path = destination_dir / f"{basename}_{row_number}.{extension or 'png'}"

    target_path.write_bytes(image_bytes)
    return str(target_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read a local Excel workbook and copy screenshot images to a local test/ folder using the game name from column A."
    )
    parser.add_argument("--xlsx", required=True, help="Path to the local Excel workbook (.xlsx)")
    parser.add_argument("--sheet", default=None, help="Worksheet name to process; defaults to the first sheet")
    parser.add_argument("--rows", required=True, help="Comma-separated rows or ranges, e.g. 2,5-7,10")
    parser.add_argument("--game-col", default="A", help="Column that contains the game name (default: A)")
    parser.add_argument("--image-col", default="M", help="Column that contains the screenshot (default: M)")
    parser.add_argument("--speed-col", default="I", help="Column that stores the spin speed used for naming suffixes (default: I)")
    parser.add_argument("--output-dir", default="test", help="Local folder to store copied screenshots (default: test)")
    parser.add_argument("--debug", action="store_true", help="Print workbook and cell diagnostics for embedded images")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        print(f"Excel file not found: {xlsx_path}", file=sys.stderr)
        return 2

    row_numbers = parse_row_list(args.rows)
    if not row_numbers:
        print("No valid rows were specified via --rows", file=sys.stderr)
        return 2

    workbook = load_workbook(xlsx_path, data_only=False)
    sheet_name = args.sheet or workbook.sheetnames[0]
    if sheet_name not in workbook.sheetnames:
        print(f"Worksheet '{sheet_name}' not found in {xlsx_path}", file=sys.stderr)
        return 2

    ws = workbook[sheet_name]
    if args.debug:
        debug_sheet_summary(ws, verbose=True)
    output_dir = Path(args.output_dir)
    copied = []

    for row_number in row_numbers:
        max_row = ws.max_row
        if row_number < 1 or row_number > max_row:
            print(f"Skipping row {row_number}: out of range for worksheet '{sheet_name}' (max row {max_row})")
            continue

        game_cell_ref = col_to_cell_name(args.game_col, row_number)
        image_cell_ref = col_to_cell_name(args.image_col, row_number)
        speed_cell_ref = col_to_cell_name(args.speed_col, row_number)

        if args.debug:
            debug_sheet_summary(ws, image_cell_ref)
            print(f"Cell {speed_cell_ref}: value={ws[speed_cell_ref].value!r}, type={type(ws[speed_cell_ref].value).__name__}")

        game_name = ws[game_cell_ref].value
        if game_name is None or str(game_name).strip() == "":
            print(f"Skipping row {row_number}: empty game name in {game_cell_ref}")
            continue

        try:
            target_path = copy_image_to_local_folder(ws, game_name, row_number, image_cell_ref, output_dir, speed_cell_ref)
        except FileNotFoundError:
            print(f"Skipping row {row_number}: no screenshot in {image_cell_ref}")
            continue
        except RuntimeError as exc:
            print(f"Row {row_number}: {exc}")
            continue

        copied.append((row_number, game_name, target_path))

    if not copied:
        print("No images were copied. Check the selected rows and screenshot cells.")
        return 0

    print(f"Copied {len(copied)} images into {output_dir.resolve()}")
    for row_number, game_name, target_path in copied:
        print(f"Row {row_number} ({game_name}): {target_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
