bl_info = {
    "name": "All Objects into Assets",
    "author": "StellArc",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "Outliner (right-click / header button)",
    "description": "Creates collection assets from parent objects with children and mirrors all collections into catalogs, assigning all assets accordingly. Includes preview refresh options.",
    "category": "Outliner",
}

import bpy
import uuid
import os
import time
from pathlib import Path

# -----------------------------
# Gather descendants
# -----------------------------
def gather_descendants(obj):
    out = [obj]
    for c in obj.children:
        out.extend(gather_descendants(c))
    return out

# -----------------------------
# CDF helpers (blender_assets.cats.txt)
# -----------------------------
def read_cdf(cdf_path):
    entries = {}
    if not cdf_path.exists():
        return entries
    with cdf_path.open("r", encoding="utf-8") as f:
        for raw in f:
            ln = raw.strip()
            if not ln or ln.startswith("#") or ln.startswith("VERSION"):
                continue
            parts = ln.split(":", 2)
            if len(parts) == 3:
                uid, path, simple = parts
                entries[path] = (uid, simple)
    return entries

def write_cdf(cdf_path, entries):
    if cdf_path.exists():
        try:
            backup = cdf_path.with_suffix(cdf_path.suffix + "~")
            cdf_path.replace(backup)
        except Exception:
            pass
    lines = [
        "# Blender Asset Catalog Definition File",
        "# UUID:catalog/path:Simple Name",
        "VERSION 1",
    ]
    for cat_path in sorted(entries.keys()):
        uid, simple = entries[cat_path]
        lines.append(f"{uid}:{cat_path}:{simple}")
    cdf_path.write_text("\n".join(lines), encoding="utf-8")

# -----------------------------
# Asset library path
# -----------------------------
def resolve_library_path(name):
    if name == "LOCAL":
        if not bpy.data.filepath:
            return None
        return Path(bpy.path.abspath("//"))
    for lib in bpy.context.preferences.filepaths.asset_libraries:
        if lib.name == name:
            return Path(bpy.path.abspath(lib.path))
    return None

# -----------------------------
# Hierarchy helpers
# -----------------------------
def build_parent_map_from_scene(scene):
    parent_map = {}
    def walk(parent):
        for ch in parent.children:
            parent_map[ch] = parent
            walk(ch)
    walk(scene.collection)
    return parent_map

def collection_path(coll, parent_map):
    path = [coll.name]
    cur = coll
    visited = set()
    while cur in parent_map and cur not in visited:
        visited.add(cur)
        par = parent_map[cur]
        if par is None or par == bpy.context.scene.collection:
            break
        path.append(par.name)
        cur = par
    path.reverse()
    return path

def normalize_catalog_path(path_parts, root_prefix):
    parts = []
    if root_prefix:
        parts.append(root_prefix.strip("/"))
    parts.extend([p.strip("/") for p in path_parts if p])
    return "/".join([p for p in parts if p])

# -----------------------------
# Preview helpers (QC-style)
# -----------------------------
def _has_preview(idb):
    p = getattr(idb, "preview", None)
    if not p:
        return False
    try:
        w, h = getattr(p, "image_size", (0, 0))
        return (w or 0) > 0 and (h or 0) > 0
    except Exception:
        return False

def refresh_previews_qc_style(ids, asset_library_ref, mode):
    """
    QC-style refresh: directly override the 'id' and call the operator.
    No area/window override required.
    Returns True if it ran (even if some IDs failed).
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

# -----------------------------
# Operator
# -----------------------------
class OUTLINER_OT_auto_assets_catalogs(bpy.types.Operator):
    bl_idname = "outliner.auto_assets_catalogs"
    bl_label = "Create Collection Assets + Catalogs (Hierarchy)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        master_name = prefs.master_collection_name.strip() or "Assets"
        library_name = prefs.asset_library
        catalog_root = prefs.catalog_root.strip()
        asset_suffix = prefs.asset_suffix
        refresh_mode = prefs.preview_refresh_mode  # 'NONE', 'MISSING', 'ALL'

        # Resolve library
        lib_path = resolve_library_path(library_name)
        if lib_path is None:
            self.report({'ERROR'}, f"Asset library '{library_name}' not available (LOCAL requires saved .blend).")
            return {'CANCELLED'}
        cdf_path = lib_path / "blender_assets.cats.txt"

        # Ensure master collection
        master_col = bpy.data.collections.get(master_name)
        if not master_col:
            master_col = bpy.data.collections.new(master_name)
            try:
                context.scene.collection.children.link(master_col)
            except Exception:
                pass

        # Build hierarchy mapping & CDF
        parent_map = build_parent_map_from_scene(context.scene)
        cdf_entries = read_cdf(cdf_path)
        coll_to_catalog = {}
        excluded = {master_col.name}

        # Pass 1: create catalogs for all normal collections (mirror hierarchy)
        for coll in bpy.data.collections:
            if coll.name in excluded or coll.name.endswith(asset_suffix):
                continue
            path_parts = collection_path(coll, parent_map) if coll in parent_map else [coll.name]
            cat_path = normalize_catalog_path(path_parts, catalog_root)
            if cat_path in cdf_entries:
                uid, simple = cdf_entries[cat_path]
            else:
                uid = str(uuid.uuid4())
                simple = path_parts[-1] if path_parts else coll.name
                cdf_entries[cat_path] = (uid, simple)
            coll_to_catalog[coll] = (uid, simple, cat_path)

        obj_assets = []
        col_assets = []

        # Pass 2: mark all objects and assign to deepest catalog they belong to
        for obj in bpy.data.objects:
            candidates = []
            for col in obj.users_collection:
                if col in coll_to_catalog:
                    uid, simple, cat_path = coll_to_catalog[col]
                    depth = cat_path.count("/") + 1
                    candidates.append((depth, uid, simple))
            try:
                if not obj.asset_data:
                    obj.asset_mark()
            except Exception:
                pass
            if candidates and obj.asset_data:
                candidates.sort(key=lambda t: t[0], reverse=True)
                _, uid, simple = candidates[0]
                try:
                    obj.asset_data.catalog_id = uid
                    obj.asset_data.catalog_simple_name = simple
                except Exception:
                    pass
            obj_assets.append(obj)

        # Pass 3: object-with-children -> <name><suffix> collection assets
        for obj in bpy.data.objects:
            if not obj.children:
                continue
            col_name = f"{obj.name}{asset_suffix}"
            col = bpy.data.collections.get(col_name)
            if not col:
                col = bpy.data.collections.new(col_name)
                try:
                    master_col.children.link(col)
                except Exception:
                    pass
            for m in gather_descendants(obj):
                if m.name not in col.objects:
                    try:
                        col.objects.link(m)
                    except RuntimeError:
                        pass
            if not col.asset_data:
                try:
                    col.asset_mark()
                except Exception:
                    pass
            # Assign collection asset to same (deepest) catalog as the object
            candidates = []
            for col_of_obj in obj.users_collection:
                if col_of_obj in coll_to_catalog:
                    uid, simple, cat_path = coll_to_catalog[col_of_obj]
                    depth = cat_path.count("/") + 1
                    candidates.append((depth, uid, simple))
            if candidates and col.asset_data:
                candidates.sort(key=lambda t: t[0], reverse=True)
                _, uid, simple = candidates[0]
                try:
                    col.asset_data.catalog_id = uid
                    col.asset_data.catalog_simple_name = simple
                except Exception:
                    pass
            col_assets.append(col)

        # Persist catalogs
        try:
            lib_path.mkdir(parents=True, exist_ok=True)
            write_cdf(cdf_path, cdf_entries)
            try:
                bpy.ops.asset.catalogs_save()
            except Exception:
                pass
        except Exception as e:
            self.report({'ERROR'}, f"Catalog write failed: {e}")
            return {'CANCELLED'}

        # Preview refresh (QC-style)
        ran = True
        if refresh_mode != 'NONE':
            asset_library_ref = library_name
            ran = refresh_previews_qc_style(list(obj_assets) + list(col_assets), asset_library_ref, refresh_mode)

        msg = f"Assets marked: {len(obj_assets)} objects, {len(col_assets)} collections. Catalogs: {len(cdf_entries)}"
        if refresh_mode != 'NONE':
            msg += " | Preview refresh: done" if ran else " | Preview refresh: skipped"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

# -----------------------------
# Menus / Header button (toggleable)
# -----------------------------
def outliner_object_menu(self, context):
    prefs = bpy.context.preferences.addons[__name__].preferences
    if prefs.enable_context_menu:
        self.layout.operator(OUTLINER_OT_auto_assets_catalogs.bl_idname, text="Create Collection Assets + Catalogs (Hierarchy)")

def outliner_collection_menu(self, context):
    prefs = bpy.context.preferences.addons[__name__].preferences
    if prefs.enable_context_menu:
        self.layout.operator(OUTLINER_OT_auto_assets_catalogs.bl_idname, text="Create Collection Assets + Catalogs (Hierarchy)")

def outliner_general_menu(self, context):
    prefs = bpy.context.preferences.addons[__name__].preferences
    if prefs.enable_context_menu:
        self.layout.operator(OUTLINER_OT_auto_assets_catalogs.bl_idname, text="Create Collection Assets + Catalogs (Hierarchy)")

def outliner_header_button(self, context):
    prefs = bpy.context.preferences.addons[__name__].preferences
    if not prefs.enable_outliner_header_button:
        return
    row = self.layout.row(align=True)
    row.separator()
    row.operator(
        OUTLINER_OT_auto_assets_catalogs.bl_idname,
        text="Assets + Catalogs",
        icon='ASSET_MANAGER'
    )

# -----------------------------
# Preferences
# -----------------------------
def _asset_lib_items(self, context):
    items = [("LOCAL", "Current File (LOCAL)", "Use the current blend file's folder (requires saved file)")]
    for lib in bpy.context.preferences.filepaths.asset_libraries:
        items.append((lib.name, lib.name, lib.path))
    return items

class AutoAssetsPrefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    master_collection_name: bpy.props.StringProperty(
        name="Master Collection",
        default="Assets",
    )
    asset_library: bpy.props.EnumProperty(
        name="Target Asset Library",
        items=_asset_lib_items,
    )
    catalog_root: bpy.props.StringProperty(
        name="Catalog Root Prefix",
        default="",
        description="Optional prefix folder for all catalog paths (e.g. 'Pack01' -> Pack01/Buildings/Doors).",
    )
    asset_suffix: bpy.props.StringProperty(
        name="Asset Collection Suffix",
        default="_asset",
        description="Suffix for collections created for parent objects with children",
    )
    preview_refresh_mode: bpy.props.EnumProperty(
        name="Preview Refresh Mode",
        description="Generate asset previews after processing",
        items=[
            ("NONE", "Do not refresh", "Skip previews"),
            ("MISSING", "Refresh missing only", "Only generate for assets that don't have one"),
            ("ALL", "Refresh all", "Regenerate for all affected assets"),
        ],
        default="NONE",
    )

    # UI placement toggles
    enable_context_menu: bpy.props.BoolProperty(
        name="Show in Outliner Right-Click",
        default=True,
        description="Show the operator in the Outliner context (right-click) menus",
    )
    enable_outliner_header_button: bpy.props.BoolProperty(
        name="Show Button in Outliner Header",
        default=True,
        description="Show a button in the Outliner header that runs the operator",
    )

    def draw(self, context):
        col = self.layout.column()
        col.label(text="Behavior", icon="TOOL_SETTINGS")
        col.prop(self, "master_collection_name")
        col.prop(self, "asset_library")
        col.prop(self, "catalog_root")
        col.prop(self, "asset_suffix")
        col.prop(self, "preview_refresh_mode")
        col.separator()
        col.label(text="UI Placement", icon="PREFERENCES")
        col.prop(self, "enable_context_menu")
        col.prop(self, "enable_outliner_header_button")

# -----------------------------
# Register
# -----------------------------
classes = (
    OUTLINER_OT_auto_assets_catalogs,
    AutoAssetsPrefs,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.OUTLINER_MT_object.append(outliner_object_menu)
    bpy.types.OUTLINER_MT_collection.append(outliner_collection_menu)
    bpy.types.OUTLINER_MT_context_menu.append(outliner_general_menu)
    bpy.types.OUTLINER_HT_header.append(outliner_header_button)

def unregister():
    bpy.types.OUTLINER_HT_header.remove(outliner_header_button)
    bpy.types.OUTLINER_MT_context_menu.remove(outliner_general_menu)
    bpy.types.OUTLINER_MT_collection.remove(outliner_collection_menu)
    bpy.types.OUTLINER_MT_object.remove(outliner_object_menu)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
