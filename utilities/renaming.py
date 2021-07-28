import maya.cmds as cmds

def remove_suffix(name):
 
    """
    remove suffix from given name string
    @param name: str, given name sting to process
    @return: str, name without suffix
    """
    edits = name.split('_')
    if len(edits) < 2:
        return name
    no_suffix = "_".join(edits[:-1])
    return no_suffix


def remove_prefix(name):
    """
    remove suffix from given name string
    @param name: str, given name sting to process
    @return: str, name without suffix
    """
    edits = name.split('_')
    if len(edits) < 2:
        return name
    no_prefix = "_".join(splitted[1:])
    return no_prefix

def remove_namespace(name):
    """
    deletes namespace from node and return it's new name
    @param name: str, name with namespace
    @return: str, new name
    """
    
    if not ':' in name:
        return name
    edits = name.split(':')
    no_namespace = edits[-1]
    return no_namespace


def flip_side(node):
    pairs = [
            ["l", "r"],
            ["L", "R"],
            ["left", "right"], 
            ["Left", "Right"], 
            ["LEFT", "RIGHT"]
    ]
    full_new_name = list()

    for part in node.split("|"):
        splits = part.split("_")
        new_name = list() 
        for split in splits:
            for pair in pairs:
                if split in pair:
                    split = pair[not pair.index(split)]
                    break
            new_name.append(split) 
        full_new_name.append("_".join(new_name))

    return "|".join(full_new_name)


def replace_name(node, old, new):
    result = str()
    for part in node.split("|"): 
        new_part = str()
        for mod in part.split("_"):
            if mod == old:
                new_part+=new
            else:
                new_part+=mod
            new_part+="_"
        result+=new_part[:-1]+"|"
    return result[:-1]
