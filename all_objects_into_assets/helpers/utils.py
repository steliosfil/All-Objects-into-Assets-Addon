import bpy
from pathlib import Path

def gather_descendants(obj):
    out = [obj]
    for c in obj.children:
        out.extend(gather_descendants(c))
    return out

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

def resolve_library_path(name: str) -> Path | None:
    if name == "LOCAL":
        if not bpy.data.filepath:
            return None
        return Path(bpy.path.abspath("//"))
    for lib in bpy.context.preferences.filepaths.asset_libraries:
        if lib.name == name:
            return Path(bpy.path.abspath(lib.path))
    return None
