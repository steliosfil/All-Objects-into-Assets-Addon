import bpy

def _has_preview(idb) -> bool:
    """Return True if the datablock has a non-empty preview image."""
    p = getattr(idb, "preview", None)
    if not p:
        return False
    try:
        w, h = getattr(p, "image_size", (0, 0))
        return (w or 0) > 0 and (h or 0) > 0
    except Exception:
        return False

def _gen(idb) -> bool:
    """Generate a preview for the given ID datablock using the editor operator."""
    try:
        with bpy.context.temp_override(id=idb):
            bpy.ops.ed.lib_id_generate_preview()
        return True
    except Exception:
        return False

def _clear(idb) -> bool:
    """Remove an existing preview for the given ID datablock."""
    try:
        with bpy.context.temp_override(id=idb):
            bpy.ops.ed.lib_id_remove_preview()
        return True
    except Exception:
        return False

def refresh_previews(ids, mode: str) -> bool:
    """
    Refresh previews for the given iterable of datablocks.

    mode:
      - 'NONE'     → do nothing
      - 'MISSING'  → generate only for assets that don't have a preview
      - 'ALL'      → clear (if any) and re-generate for every asset

    Returns True if the function ran without a fatal error.
    """
    if mode == 'NONE':
        return True

    for idb in ids:
        # Only attempt previews for datablocks that are actually assets
        if not getattr(idb, "asset_data", None):
            continue

        if mode == 'MISSING':
            if not _has_preview(idb):
                _gen(idb)

        elif mode == 'ALL':
            # Clear first to make sure we always get a fresh render
            _clear(idb)
            _gen(idb)

    return True
