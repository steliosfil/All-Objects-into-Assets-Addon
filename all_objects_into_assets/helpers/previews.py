import bpy
import time

def _has_preview(idb) -> bool:
    p = getattr(idb, "preview", None)
    if not p:
        return False
    try:
        w, h = getattr(p, "image_size", (0, 0))
        return (w or 0) > 0 and (h or 0) > 0
    except Exception:
        return False

def refresh_previews(ids, mode: str):
    """
    Quick-and-reliable: pass ID directly via temp_override and call the operator.
    mode: 'NONE' | 'MISSING' | 'ALL'
    """
    if mode == 'NONE':
        return True
    for idb in ids:
        if not getattr(idb, "asset_data", None):
            continue
        if mode == 'MISSING' and _has_preview(idb):
            continue
        try:
            with bpy.context.temp_override(id=idb):
                time.sleep(0.0001)
                bpy.ops.ed.lib_id_generate_preview()
        except Exception:
            pass
    return True
