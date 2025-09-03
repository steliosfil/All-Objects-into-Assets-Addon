bl_info = {
    "name": "All Objects into Assets",
    "author": "StellArc",
    "version": (1, 0, 2),
    "blender": (4, 5, 0),
    "location": "Outliner → Right-click",
    "description": "Marks objects and per-parent collections as assets; mirrors collections into catalogs; optional preview refresh.",
    "category": "Outliner",
    "maintainer": "StellArc",
    "doc_url": "",
    "tracker_url": "",
}

import bpy

if "bpy" in locals():
    import importlib
    if "operators" in locals():
        importlib.reload(operators)
    if "ui" in locals():
        importlib.reload(ui)
else:
    from . import operators, ui

__all__ = ("register", "unregister")

classes = (
    operators.OUTLINER_OT_all_objects_into_assets,
    ui.AddonPrefs,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    ui.register_menus()

def unregister():
    ui.unregister_menus()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
