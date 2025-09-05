import bpy


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
    excluded_root_collections: bpy.props.StringProperty(
        name="Also Exclude These Roots",
        description=(
            "Optional list of extra root Collections to exclude from catalog mirroring.\n"
            "Separate names with commas or new lines. Each name excludes that collection and all its children"
        ),
        default="",
        options={'MULTILINE'},
    )

    def draw(self, context):
        col = self.layout.column()
        col.label(text="Behavior", icon="TOOL_SETTINGS")
        col.prop(self, "master_collection_name")
        col.prop(self, "asset_library")
        col.prop(self, "catalog_root")
        col.prop(self, "asset_suffix")
        col.prop(self, "preview_refresh_mode")
        col.prop(self, "excluded_root_collections")


# ---------- Outliner Context Menus (always shown) ----------

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


def register_menus():
    bpy.types.OUTLINER_MT_object.append(outliner_object_menu)
    bpy.types.OUTLINER_MT_collection.append(outliner_collection_menu)
    bpy.types.OUTLINER_MT_context_menu.append(outliner_general_menu)


def unregister_menus():
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
