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

def walk_child_collections(col):
    """Yield 'col' and all nested child collections (depth-first)."""
    yield col
    for ch in col.children:
        yield from walk_child_collections(ch)

def outliner_selected_collections(context):
    """
    Return a set of Collections picked in the Outliner.
    - Uses context.selected_ids when available (multi-select).
    - Falls back to context.collection (active) if present.
    """
    sel = set()

    # Multi-select (Outliner)
    ids = getattr(context, "selected_ids", None)
    if ids:
        for idb in ids:
            if isinstance(idb, bpy.types.Collection):
                sel.add(idb)

    # Active collection in Outliner, if any
    active = getattr(context, "collection", None)
    if isinstance(active, bpy.types.Collection):
        sel.add(active)

    return sel

def collections_scope_from_context(context):
    """
    Decide the processing scope:
    - If one or more collections are selected in the Outliner, return all of them + their children.
    - Otherwise return None to signal 'process everything'.
    """
    picked = outliner_selected_collections(context)
    if not picked:
        return None  # process all

    scoped = set()
    for c in picked:
        for cc in walk_child_collections(c):
            scoped.add(cc)
    return scoped
