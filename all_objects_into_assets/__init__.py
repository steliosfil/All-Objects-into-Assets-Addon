bl_info = {
    "name": "All Objects into Assets",
    "author": "StellArc",
    "version": (1, 0, 1),
    "blender": (4, 5, 0),
    "location": "Outliner (right-click / header button)",
    "description": "Marks all objects and generated per-parent collections as assets, mirrors Collections into Asset Catalogs (hierarchy preserved), and refreshes previews.",
    "category": "Outliner",
    "doc_url": "",
    "tracker_url": "",
    "maintainer": "StellArc",
}

import importlib
import bpy

from . import operators, ui

# Lazy-reload when running from Text Editor
def _reload():
    importlib.reload(operators)
    importlib.reload(ui)

try:
    _reloading
except NameError:
    _reloading = False
else:
    _reload()

classes = (
    operators.OUTLINER_OT_all_objects_into_assets,
    ui.AddonPrefs,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    ui.register_menus()

def unregister():
    ui.unregister_menus()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
