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
    from . import operators, ui        
    importlib.reload(operators)
    importlib.reload(ui)
else:
    from . import operators, ui
    
__all__ = ("register", "unregister")

# Classes to register from submodules
classes = (
    operators.OUTLINER_OT_all_objects_into_assets,
    ui.AddonPrefs,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Menus are appended separately
    ui.register_menus()

def unregister():
    ui.unregister_menus()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
