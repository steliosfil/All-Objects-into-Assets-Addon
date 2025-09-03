import bpy
from .helpers.utils import collections_scope_from_context  # for dynamic label


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
        name="Show Button in Outliner Header",
        default=False,  # Default OFF per review feedback
        description="Optional: show a button in the Outliner header that runs the operator",
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


# ---------- Context Menu helpers ----------

def _draw_blocked_operator(layout, context):
    """
    Draw our operator in its own separated block at the bottom.
    Label reflects whether the operator will process Selected Collections or All Collections.
    """
    prefs = bpy.context.preferences.addons[__package__].preferences
    if not prefs.enable_context_menu:
        return

    scope = collections_scope_from_context(context)
    label = "All Objects into Assets (Selected Collections)" if scope else "All Objects into Assets (All Collections)"

    layout.separator()  # visual divider (the "thin white line" section break)
    layout.operator("outliner.all_objects_into_assets", text=label, icon='ASSET_MANAGER')


def outliner_object_menu(self, context):
    _draw_blocked_operator(self.layout, context)


def outliner_collection_menu(self, context):
    _draw_blocked_operator(self.layout, context)


def outliner_general_menu(self, context):
    _draw_blocked_operator(self.layout, context)


# ---------- Outliner Header (opt-in) ----------

def outliner_header_button(self, context):
    prefs = bpy.context.preferences.addons[__package__].preferences
    if not prefs.enable_outliner_header_button:
        return
    # Button label can also reflect scope when clicked from Outliner area
    scope = collections_scope_from_context(context)
    txt = "Assets + Catalogs (Selected)" if scope else "Assets + Catalogs (All)"
    row = self.layout.row(align=True)
    row.separator()
    row.operator(
        "outliner.all_objects_into_assets",
        text=txt,
        icon='ASSET_MANAGER'
    )


# ---------- Register / Unregister ----------

def register_menus():
    bpy.types.OUTLINER_MT_object.append(outliner_object_menu)
    bpy.types.OUTLINER_MT_collection.append(outliner_collection_menu)
    bpy.types.OUTLINER_MT_context_menu.append(outliner_general_menu)

    # Only register the header button if user enabled it (opt-in)
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        if prefs.enable_outliner_header_button:
            bpy.types.OUTLINER_HT_header.append(outliner_header_button)
    except Exception:
        # Preferences might not be initialized yet on first register; that's fine
        pass


def unregister_menus():
    # Remove header button if present
    try:
        bpy.types.OUTLINER_HT_header.remove(outliner_header_button)
    except Exception:
        pass
    # Remove context menu hooks
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
