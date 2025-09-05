import bpy

# ---------- PropertyGroup & UIList for excluded roots ----------

class AOIA_ExcludedRoot(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Collection Name",
        description="Root Collection to exclude (the whole subtree will be ignored)"
    )

class AOIA_UL_excluded_roots(bpy.types.UIList):
    """UI list that shows excluded root collection names"""
    bl_idname = "AOIA_UL_excluded_roots"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # item is AOIA_ExcludedRoot
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=True, icon='OUTLINER_COLLECTION')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.name)

class AOIA_OT_excluded_add(bpy.types.Operator):
    bl_idname = "aoia.excluded_add"
    bl_label = "Add"
    bl_description = "Add a root Collection name to exclude"

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__package__].preferences
        new = prefs.excluded_roots.add()
        new.name = ""
        prefs.excluded_roots_index = len(prefs.excluded_roots) - 1
        return {'FINISHED'}

class AOIA_OT_excluded_remove(bpy.types.Operator):
    bl_idname = "aoia.excluded_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected excluded root"

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__package__].preferences
        idx = prefs.excluded_roots_index
        if 0 <= idx < len(prefs.excluded_roots):
            prefs.excluded_roots.remove(idx)
            prefs.excluded_roots_index = min(idx, len(prefs.excluded_roots) - 1)
        return {'FINISHED'}


# ---------- Preferences ----------

def _asset_lib_items(self, context):
    items = [("LOCAL", "Current File (LOCAL)", "Use the current .blend's folder (requires saved file)")]
    for lib in bpy.context.preferences.filepaths.asset_libraries:
        items.append((lib.name, lib.name, lib.path))
    return items


class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

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
        description="Optional prefix folder for all catalog paths, e.g. 'Pack01' → Pack01/Buildings/Doors",
    )
    asset_suffix: bpy.props.StringProperty(
        name="Asset Collection Suffix",
        default="_asset",
        description="Suffix for collections created from parent objects with children",
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

    # New: multi-line list of extra excluded root collections
    excluded_roots: bpy.props.CollectionProperty(type=AOIA_ExcludedRoot)
    excluded_roots_index: bpy.props.IntProperty(default=0)

    def draw(self, context):
        col = self.layout.column()
        col.label(text="Behavior", icon="TOOL_SETTINGS")
        col.prop(self, "master_collection_name")
        col.prop(self, "asset_library")
        col.prop(self, "catalog_root")
        col.prop(self, "asset_suffix")
        col.prop(self, "preview_refresh_mode")

        col.separator()
        col.label(text="Also Exclude These Roots", icon="OUTLINER_COLLECTION")
        row = col.row()
        row.template_list(
            listtype_name="AOIA_UL_excluded_roots",
            list_id="",
            dataptr=self,
            propname="excluded_roots",
            active_dataptr=self,
            active_propname="excluded_roots_index",
            rows=4,
        )
        buttons = row.column(align=True)
        buttons.operator("aoia.excluded_add", icon='ADD', text="")
        buttons.operator("aoia.excluded_remove", icon='REMOVE', text="")


# ---------- Outliner context menus (always present) ----------

def _draw_block(layout):
    layout.separator()
    col = layout.column(align=True)
    op = col.operator(
        "outliner.all_objects_into_assets",
        text="All Objects into Assets — Selected Collections",
        icon='ASSET_MANAGER'
    )
    op.force_scope = 'SELECTED'
    op = col.operator(
        "outliner.all_objects_into_assets",
        text="All Objects into Assets — All Collections",
        icon='ASSET_MANAGER'
    )
    op.force_scope = 'ALL'


def outliner_object_menu(self, context):
    _draw_block(self.layout)


def outliner_collection_menu(self, context):
    _draw_block(self.layout)


def outliner_general_menu(self, context):
    _draw_block(self.layout)


# We register UI-related classes here so __init__.py can keep its simple class list.
_EXTRA_UI_CLASSES = (
    AOIA_ExcludedRoot,
    AOIA_UL_excluded_roots,
    AOIA_OT_excluded_add,
    AOIA_OT_excluded_remove,
)

def register_menus():
    # Ensure our UI helper classes are registered (safe on reloads)
    for cls in _EXTRA_UI_CLASSES:
        try:
            bpy.utils.register_class(cls)
        except RuntimeError:
            # already registered
            pass

    bpy.types.OUTLINER_MT_object.append(outliner_object_menu)
    bpy.types.OUTLINER_MT_collection.append(outliner_collection_menu)
    bpy.types.OUTLINER_MT_context_menu.append(outliner_general_menu)


def unregister_menus():
    # Remove menus
    try:
        bpy.types.OUTLINER_MT_context_menu.remove(outliner_general_menu)
    except Exception:
        pass
    try:
        bpy.types.OUTLINER_MT_collection.remove(outliner_collection_menu)
    except Exception:
        pass
    try:
        bpy.types.OUTLINER_MT_object.remove(outliner_object_menu)
    except Exception:
        pass

    # Unregister UI helper classes (reverse order)
    for cls in reversed(_EXTRA_UI_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
