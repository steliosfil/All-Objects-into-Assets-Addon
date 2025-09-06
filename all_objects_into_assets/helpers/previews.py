import bpy
import time
from contextlib import contextmanager


# ---------- strict detector ----------
def _has_preview(idb) -> bool:
    p = getattr(idb, "preview", None)
    if not p:
        return False
    try:
        w, h = getattr(p, "image_size", (0, 0))
        w = int(w or 0)
        h = int(h or 0)
        if w <= 0 or h <= 0:
            return False
        pix = getattr(p, "image_pixels_float", None)
        return bool(pix and len(pix) >= (w * h * 4))
    except Exception:
        return False


# ---------- asset browser ctx for ops ----------
@contextmanager
def _asset_browser_ctx():
    win = bpy.context.window
    scr = win.screen if win else None
    chosen_area = None
    restore = None  # (area, prev_type, prev_ui)

    if scr:
        for area in scr.areas:
            if area.type == 'FILE_BROWSER':
                prev_ui = getattr(area, "ui_type", None)
                try:
                    area.ui_type = 'ASSETS'
                except Exception:
                    pass
                region = next((r for r in area.regions if r.type == 'WINDOW'), None)
                if region:
                    chosen_area = area
                    restore = (area, 'FILE_BROWSER', prev_ui)
                    break

    if not chosen_area and scr and scr.areas:
        area = scr.areas[0]
        prev_type = area.type
        prev_ui = getattr(area, "ui_type", None)
        try:
            area.type = 'FILE_BROWSER'
            area.ui_type = 'ASSETS'
        except Exception:
            pass
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region:
            chosen_area = area
            restore = (area, prev_type, prev_ui)

    try:
        region = next((r for r in chosen_area.regions if r.type == 'WINDOW'), None) if chosen_area else None
        yield (win, scr, chosen_area, region)
    finally:
        if restore:
            area, prev_type, prev_ui = restore
            try:
                if prev_type != 'FILE_BROWSER':
                    area.type = prev_type
                if prev_ui is not None and hasattr(area, "ui_type"):
                    area.ui_type = prev_ui
            except Exception:
                pass


def _op_generate(idb, ctx_tuple) -> bool:
    win, scr, area, region = ctx_tuple
    try:
        if all((win, scr, area, region)):
            override = {"window": win, "screen": scr, "area": area, "region": region, "id": idb}
            return bpy.ops.ed.lib_id_generate_preview(override) == {'FINISHED'}
        with bpy.context.temp_override(id=idb):
            return bpy.ops.ed.lib_id_generate_preview() == {'FINISHED'}
    except Exception:
        return False


def _op_remove(idb, ctx_tuple) -> bool:
    win, scr, area, region = ctx_tuple
    try:
        if all((win, scr, area, region)):
            override = {"window": win, "screen": scr, "area": area, "region": region, "id": idb}
            return bpy.ops.ed.lib_id_remove_preview(override) == {'FINISHED'}
        with bpy.context.temp_override(id=idb):
            return bpy.ops.ed.lib_id_remove_preview() == {'FINISHED'}
    except Exception:
        return False


# ---------- ID API path ----------
def _id_generate(idb) -> bool:
    try:
        idb.preview_ensure()
    except Exception:
        pass
    try:
        idb.asset_generate_preview()
        return True
    except Exception:
        return False


# ---------- wait helper ----------
def _wait_for_preview_jobs(timeout_sec=5.0, step=0.06):
    start = time.time()
    try:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN', iterations=1)
    except Exception:
        pass
    while bpy.app.is_job_running("RENDER_PREVIEW"):
        if (time.time() - start) >= timeout_sec:
            break
        try:
            bpy.ops.wm.redraw_timer(type='DRAW_WIN', iterations=1)
        except Exception:
            pass
        time.sleep(step)


# ---------- public API ----------
def refresh_previews(ids, mode: str) -> bool:
    """
    mode:
      - 'NONE'     → do nothing
      - 'MISSING'  → for assets without a real thumbnail: FORCE remove → generate (ID API + ops fallback)
      - 'ALL'      → FORCE remove → generate for every asset
    """
    if mode == 'NONE':
        return True

    # Unique, asset-bearing IDs
    todo = []
    seen = set()
    for idb in ids:
        if not getattr(idb, "asset_data", None):
            continue
        k = id(idb)
        if k in seen:
            continue
        seen.add(k)
        todo.append(idb)
    if not todo:
        return True

    with _asset_browser_ctx() as ab_ctx:
        if mode == 'ALL':
            # Hard reset all
            for idb in todo:
                _op_remove(idb, ab_ctx)
            targets = list(todo)
        else:
            # Build strict missing list
            targets = [idb for idb in todo if not _has_preview(idb)]
            if not targets:
                return True
            # Force-remove first to clear any stale state (this fixes “deleted but won’t regen”)
            for idb in targets:
                _op_remove(idb, ab_ctx)

        # Up to 4 rounds: ID API → wait → check → ops → wait → check (repeat)
        remaining = list(targets)
        for _ in range(4):
            if not remaining:
                break

            progressed = False

            # A) ID API
            for idb in list(remaining):
                if _id_generate(idb):
                    progressed = True

            _wait_for_preview_jobs(timeout_sec=5.0, step=0.06)
            remaining = [idb for idb in remaining if not _has_preview(idb)]
            if not remaining:
                break

            # B) Ops fallback
            for idb in list(remaining):
                if _op_generate(idb, ab_ctx):
                    progressed = True

            _wait_for_preview_jobs(timeout_sec=5.0, step=0.06)
            remaining = [idb for idb in remaining if not _has_preview(idb)]

            if not progressed:
                break

    return True
