import bpy
from pathlib import Path

from .helpers.utils import (
    gather_descendants,
    build_parent_map_from_scene,
    collection_path,
    normalize_catalog_path,
    resolve_library_path,
)
from .helpers.catalogs import read_cdf, write_cdf, ensure_catalog
from .helpers.previews import refresh_previews

class OUTLINER_OT_all_objects_into_assets(bpy.types.Operator):
    """Create per-parent collection assets, mark all objects as assets, mirror Collections into Catalogs."""
    bl_idname = "outliner.all_objects_into_assets"
    bl_label = "All Objects into Assets (Hierarchy)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__package__].preferences
        master_name = prefs.master_collection_name.strip() or "Assets"
        library_name = prefs.asset_library
        catalog_root = prefs.catalog_root.strip()
        asset_suffix = prefs.asset_suffix
        refresh_mode = prefs.preview_refresh_mode  # 'NONE'|'MISSING'|'ALL'

        # Resolve asset library + CDF path
        lib_path = resolve_library_path(library_name)
        if lib_path is None:
            self.report({'ERROR'}, f"Asset library '{library_name}' not available (LOCAL requires saved .blend).")
            return {'CANCELLED'}
        cdf_path = Path(lib_path) / "blender_assets.cats.txt"

        # Ensure master collection exists
        master_col = bpy.data.collections.get(master_name)
        if not master_col:
            master_col = bpy.data.collections.new(master_name)
            try:
                context.scene.collection.children.link(master_col)
            except Exception:
                pass

        # Build scene collection hierarchy map
        parent_map = build_parent_map_from_scene(context.scene)

        # Load existing catalogs
        cdf_entries = read_cdf(cdf_path)
        coll_to_catalog = {}

        # Exclude master collection and generated *_asset collections from being mirrored
        excluded = {master_col.name}

        # Pass 1: mirror all regular Collections into catalogs (hierarchy)
        for coll in bpy.data.collections:
            if coll.name in excluded or coll.name.endswith(asset_suffix):
                continue
            path_parts = collection_path(coll, parent_map) if coll in parent_map else [coll.name]
            cat_path = normalize_catalog_path(path_parts, catalog_root)
            uid = ensure_catalog(cdf_entries, cat_path, path_parts[-1] if path_parts else coll.name)
            coll_to_catalog[coll] = (uid, path_parts[-1], cat_path)

        obj_assets = []
        col_assets = []

        # Pass 2: mark ALL OBJECTS as assets; assign to deepest catalog of their collections
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

        # Pass 3: for each object with children, create/update <name><suffix> collection with all descendants; mark it as asset
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

            members = gather_descendants(obj)

            # Link members into the collection (avoid re-linking using users_collection)
            for m in members:
                if isinstance(m, bpy.types.Object) and (col not in m.users_collection):
                    try:
                        col.objects.link(m)
                    except RuntimeError:
                        pass

            # Mark collection as asset
            if not col.asset_data:
                try:
                    col.asset_mark()
                except Exception:
                    pass

            # Assign collection asset to the object's deepest catalog
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

        # Persist catalogs to disk
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

        # Preview refresh
        ran = True
        if refresh_mode != 'NONE':
            ran = refresh_previews(list(obj_assets) + list(col_assets), refresh_mode)

        msg = f"Assets: {len(obj_assets)} objects, {len(col_assets)} collections | Catalogs: {len(cdf_entries)}"
        if refresh_mode != 'NONE':
            msg += " | Previews refreshed" if ran else " | Preview refresh skipped"
        self.report({'INFO'}, msg)
        return {'FINISHED'}
