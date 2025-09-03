import bpy
from pathlib import Path

from .helpers.utils import (
    gather_descendants,
    build_parent_map_from_scene,
    collection_path,
    normalize_catalog_path,
    resolve_library_path,
    collections_scope_from_context,  # selection → set of Collections
)
from .helpers.catalogs import read_cdf, write_cdf, ensure_catalog
from .helpers.previews import refresh_previews


class OUTLINER_OT_all_objects_into_assets(bpy.types.Operator):
    """Create per-parent collection assets, mark objects as assets, and mirror Collections into Catalogs.

    Scope control:
      - force_scope='SELECTED' → only selected Outliner Collections (and their children).
      - force_scope='ALL'      → whole file, ignores selection.
      - force_scope='AUTO'     → selected if any, otherwise all (legacy behavior).
    """
    bl_idname = "outliner.all_objects_into_assets"
    bl_label = "All Objects into Assets (Hierarchy)"
    bl_options = {'REGISTER', 'UNDO'}

    force_scope: bpy.props.EnumProperty(
        name="Scope",
        items=[
            ("AUTO", "Auto", "Use selected Collections if any; otherwise process all"),
            ("SELECTED", "Selected Collections", "Only the selected Collections (and their children)"),
            ("ALL", "All Collections", "Process all Collections in the file"),
        ],
        default="AUTO",
    )

    @classmethod
    def poll(cls, context):
        return True

    def _compute_scope(self, context):
        """Return a set of Collections or None (meaning 'all'). Handles force_scope."""
        if self.force_scope == 'ALL':
            return None
        elif self.force_scope == 'SELECTED':
            scoped = collections_scope_from_context(context)
            if not scoped:
                self.report({'WARNING'}, "No Collections selected in the Outliner.")
                return "CANCEL"  # sentinel
            return scoped
        else:  # AUTO
            return collections_scope_from_context(context)  # may be None (all) or set

    def execute(self, context):
        # Preferences
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

        # Decide scope
        scope_colls = self._compute_scope(context)
        if scope_colls == "CANCEL":
            return {'CANCELLED'}

        # Build scene collection hierarchy map
        parent_map = build_parent_map_from_scene(context.scene)

        # Load existing catalogs
        cdf_entries = read_cdf(cdf_path)
        coll_to_catalog = {}

        # Exclude master collection and generated *_asset collections from being mirrored
        excluded = {master_col.name}

        # -------------------------
        # Pass 1: mirror Collections -> Catalogs (respect scope)
        # -------------------------
        iter_colls = (scope_colls if scope_colls is not None else bpy.data.collections)
        for coll in iter_colls:
            if coll.name in excluded or coll.name.endswith(asset_suffix):
                continue
            path_parts = collection_path(coll, parent_map) if coll in parent_map else [coll.name]
            cat_path = normalize_catalog_path(path_parts, catalog_root)
            uid = ensure_catalog(cdf_entries, cat_path, path_parts[-1] if path_parts else coll.name)
            coll_to_catalog[coll] = (uid, path_parts[-1], cat_path)

        obj_assets = []
        col_assets = []

        # -------------------------
        # Pass 2: mark OBJECTS -> Assets (respect scope)
        # -------------------------
        if scope_colls is None:
            iter_objs = bpy.data.objects
        else:
            iter_objs = [o for o in bpy.data.objects if any((c in scope_colls) for c in o.users_collection)]

        for obj in iter_objs:
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

        # -------------------------
        # Pass 3: per-parent collection assets (respect scope)
        # -------------------------
        if scope_colls is None:
            parent_objs = [o for o in bpy.data.objects if o.children]
        else:
            parent_objs = [
                o for o in bpy.data.objects
                if o.children and any((c in scope_colls) for c in o.users_collection)
            ]

        for obj in parent_objs:
            col_name = f"{obj.name}{asset_suffix}"
            col = bpy.data.collections.get(col_name)
            if not col:
                col = bpy.data.collections.new(col_name)
                try:
                    master_col.children.link(col)
                except Exception:
                    pass

            # Link descendants into the asset collection (avoid re-linking via users_collection)
            members = gather_descendants(obj)
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

            # Assign collection asset to the deepest catalog of the parent object
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

        # -------------------------
        # Persist catalogs to disk
        # -------------------------
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

        # -------------------------
        # Preview refresh (optional)
        # -------------------------
        ran = True
        if refresh_mode != 'NONE':
            ran = refresh_previews(list(obj_assets) + list(col_assets), refresh_mode)

        # -------------------------
        # Report
        # -------------------------
        if self.force_scope == 'ALL' or (self.force_scope == 'AUTO' and scope_colls is None):
            scope_msg = "All Collections"
        else:
            scope_msg = "Selected Collections"
        msg = f"{scope_msg} | Assets: {len(obj_assets)} objects, {len(col_assets)} collections | Catalogs: {len(cdf_entries)}"
        if refresh_mode != 'NONE':
            msg += " | Previews refreshed" if ran else " | Preview refresh skipped"
        self.report({'INFO'}, msg)

        return {'FINISHED'}
