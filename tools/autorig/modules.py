import json
import os
from utilities.renaming import flip_side, find_side
import numpy as np

class Modules(object):
    def __init__(self):
        self._module_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "modules.json"
        )
        self._modules = None
        self.load_modules()

    def load_modules(self):
        with open(self._module_file) as f:
            self._modules = json.load(f)

    @property
    def module_file(self):
        return self._module_file

    @module_file.setter
    def module_file(self, file_path):
        self._module_file = file_path
        self.load_modules()

    @property
    def list(self):
        modules = list(self._modules)
        modules.sort()
        return modules

    def get(self, module):
        if module in self._modules:
            return self._modules[module]


def add_side_prefix(old_module, side):
    new_module = dict()
    new_module["BASE"] = old_module["BASE"]
    new_module["JOINTS"] = dict()
    for old_key in old_module["JOINTS"]:
        jnt = old_module["JOINTS"][old_key]
        for attr in "aim", "world_up", "parent":
            if jnt[attr]:
                if not find_side(jnt[attr]):
                    jnt[attr] = "{0}_{1}".format(side, jnt[attr])
        if find_side(old_key):
            key = old_key
        else:
            key = "{0}_{1}".format(side, old_key)
        new_module["JOINTS"][key] = jnt
    return new_module

def _get_children(joints, world_up, y_index, p=None):
    jnts = dict()
    for x_index, jnt_child in enumerate(joints):
        if world_up:
            world_up = p
        else:
            world_up = None
        if joints[jnt_child]:
            aim = list(joints[jnt_child])[0]
        else:
            aim = None
        jnts[jnt_child] = {
            "world_up": world_up,
            "rotation": 0.0,
            "transform": [[x_index, y_index, 0.0], [0.0, 0.0, 0.0]],
            "parent": p,
            "aim": aim,
            "radius": 1.0,
        }
        jnts.update(
            _get_children(joints[jnt_child], world_up, y_index + 2, jnt_child)
        )
    return jnts


def fk_module(joints, world_up_parent=True):
    module = {
        "BASE": {
            "matrix": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            "shape": [
                [0.0, 0.0, -5.0],
                [3.5, 0.0, -3.54],
                [5.0, 0.0, 0.0],
                [3.5, 0.0, 3.5],
                [0.0, 0.0, 5.0],
                [-3.5, 0.0, 3.5],
                [-5.0, 0.0, 0.0],
                [-3.5, 0.0, -3.5],
                [0.0, 0.0, -5.0],
            ],
            "mirrored": False,
            "parent": None,
        },
        "JOINTS": {}
    }
    module["JOINTS"].update(_get_children(joints, world_up_parent, 0))
    return module


def mirror(old_module, axis="x"):
    module = {"BASE": {}, "JOINTS": {}}
    base = old_module["BASE"]
    matrix = base["matrix"]
    offset = np.array([
        [1.0, -1.0, -1.0, 1.0],
        [1.0, -1.0, -1.0, 1.0],
        [1.0, -1.0, -1.0, 1.0],
        [-1.0, 1.0, 1.0, 1.0]])
    if axis == "y":
        offset = offset[:, [1, 0, 2, 3]]
    if axis == "z":
        offset = offset[:, [2, 1, 0, 3]]
    new_matrix = np.reshape(matrix * offset, (1, -1)).tolist()
    module["BASE"]["matrix"] = new_matrix
    module["BASE"]["mirrored"] = not base["mirrored"]
    if base["parent"]:
        module["BASE"]["parent"] = flip_side(base["parent"])
    else:
        module["BASE"]["parent"] = None
    module["BASE"]["shape"] = base["shape"]
    for old_key in old_module["JOINTS"]:
        jnt = old_module["JOINTS"][old_key]
        key = flip_side(old_key)
        transform = np.array(jnt["transform"])
        transform *= -1
        module["JOINTS"][key] = dict()
        module["JOINTS"][key]["transform"] = transform.tolist()
        if jnt["parent"]:
            module["JOINTS"][key]["parent"] = flip_side(jnt["parent"])
        else:
            module["JOINTS"][key]["parent"] = None
        module["JOINTS"][key]["rotation"] = jnt["rotation"]*-1
        if jnt["aim"]:
            module["JOINTS"][key]["aim"] = flip_side(jnt["aim"])
        else:
            module["JOINTS"][key]["aim"] = None
        if jnt["world_up"]:
            module["JOINTS"][key]["world_up"] = flip_side(jnt["world_up"])
        else:
            module["JOINTS"][key]["world_up"] = None
        module["JOINTS"][key]["radius"] = jnt["radius"]
    return module
