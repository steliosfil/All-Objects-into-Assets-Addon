import bpy
from .helpers.utils import collections_scope_from_context  # optional for header label nuance


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
        description="Optional prefix folder for all catalog paths, e.g. 'Pack01' -> Pack01/Buildings/Doors",
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
    # UI placement
    enable_context_menu: bpy.props.BoolProperty(
        name="Show in Outliner Right-Click",
        default=True,
        description="Show the operator in the Outliner context (right-click) menus",
    )
    enable_outliner_header_button: bpy.props.BoolProperty(
        name="Show Buttons in Outliner Header",
        default=False,  # default OFF per review feedback
        description="Optional: show buttons in the Outliner header that run the operator",
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


# ---------- Context Menus (separate block, two entries) ----------

def _draw_block(layout, *, show=True):
    if not show:
        return
    layout.separator()
    col = layout.column(align=True)
    col.operator(
        "outliner.all_objects_into_assets",
        text="All Objects into Assets — Selected Collections",
        icon='ASSET_MANAGER'
    ).force_scope = 'SELECTED'
    col.operator(
        "outliner.all_objects_into_assets",
        text="All Objects into Assets — All Collections",
        icon='ASSET_MANAGER'
    ).force_scope = 'ALL'

def outliner_object_menu(self, context):
    prefs = bpy.context.preferences.addons[__package__].preferences
    _draw_block(self.layout, show=prefs.enable_context_menu)

def outliner_collection_menu(self, context):
    prefs = bpy.context.preferences.addons[__package__].preferences
    _draw_block(self.layout, show=prefs.enable_context_menu)

def outliner_general_menu(self, context):
    prefs = bpy.context.preferences.addons[__package__].preferences
    _draw_block(self.layout, show=prefs.enable_context_menu)


# ---------- Outliner Header (opt-in, two buttons) ----------

def outliner_header_button(self, context):
    prefs = bpy.context.preferences.addons[__package__].preferences
    if not prefs.enable_outliner_header_button:
        return
    row = self.layout.row(align=True)
    row.separator()
    r1 = row.operator("outliner.all_objects_into_assets", text="Selected", icon='ASSET_MANAGER')
    r1.force_scope = 'SELECTED'
    r2 = row.operator("outliner.all_objects_into_assets", text="All", icon='ASSET_MANAGER')
    r2.force_scope = 'ALL'


# ---------- Register / Unregister ----------

def register_menus():
    bpy.types.OUTLINER_MT_object.append(outliner_object_menu)
    bpy.types.OUTLINER_MT_collection.append(outliner_collection_menu)
    bpy.types.OUTLINER_MT_context_menu.append(outliner_general_menu)
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        if prefs.enable_outliner_header_button:
            bpy.types.OUTLINER_HT_header.append(outliner_header_button)
    except Exception:
        pass

def unregister_menus():
    # header
    try:
        bpy.types.OUTLINER_HT_header.remove(outliner_header_button)
    except Exception:
        pass
    # context menus
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
