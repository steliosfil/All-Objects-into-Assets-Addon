# All Objects into Assets

Marks all objects and generated per-parent collections as assets, mirrors Collections into Asset Catalogs (hierarchy preserved), and optionally refreshes previews. Adds an Outliner header button and right-click entries.

## Requirements
- Blender **4.5+**

## Install
1. Download the ZIP from Releases (or zip the `all_objects_into_assets/` folder so the ZIP contains that folder with `__init__.py` inside).
2. Blender → Edit → Preferences → Add-ons → Install…
3. Select the ZIP, enable **All Objects into Assets**.

## Use
- Outliner header → **Assets + Catalogs**
- Or right-click in Outliner (object / collection / empty space) → **All Objects into Assets (Hierarchy)**
- Preferences → **All Objects into Assets**:
  - Master collection name (container for generated `_asset` collections)
  - Target Asset Library (LOCAL or named)
  - Catalog root prefix
  - Asset collection suffix (default `_asset`)
  - Preview refresh: None / Missing only / All
  - UI placement toggles

## Notes
- Catalogs are written to the target library’s `blender_assets.cats.txt` and saved via Blender’s `asset.catalogs_save()`.

## License
MIT © StellArc
