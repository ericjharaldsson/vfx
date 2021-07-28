from maya import cmds
import json
import os


class Modules(object):
    """
    Attr:
        @property module_file:

    Functions:
        module:

    """

    def __init__(self):
        self.__module_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "modules.json"
        )
        self.load_modules()

    def load_modules(self):
        with open(self.__module_file) as f:
            self.__modules = json.load(f)

    @property
    def module_file(self):
        return self.__module_file

    @module_file.setter
    def module_file(self, file_path):
        self.__module_file = file_path
        self.load_modules()

    @property
    def list(self):
        modules = list(self.__modules)
        modules.sort()
        return modules

    def get(self, module):
        if module in self.__modules:
            return self.__modules[module]


def _get_children(jnt, world_up, y_index, p=None):
    jnts = dict()
    for x_index, jnt_child in enumerate(jnt):
        if world_up:
            world_up = p
        else:
            world_up = None
        jnts[jnt_child] = {
            "world_up": world_up,
            "rotation": 0.0,
            "transform": [[x_index, y_index, 0.0], [0.0, 0.0, 0.0]],
            "parent": p,
            "aim": p,
            "radius": 1.0,
        }
        jnts.update(_get_children(jnt[jnt_child], world_up, y_index + 1, jnt_child))
    return jnts


def fk_module(name, joints, world_up_parent=True):
    module = {
        "BASE": {
            "matrix": [
                1.0, 0.0, 0.0, 0.0, 
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ],
            "shape": [
                [0.0, 0.0, -1.0],
                [0.707107, 0.0, -0.707107],
                [1.0, 0.0, 0.0],
                [0.707107, 0.0, 0.707107],
                [0.0, 0.0, 1.0],
                [-0.707107, 0.0, 0.707107],
                [-1.0, 0.0, 0.0],
                [-0.707107, 0.0, -0.707107],
                [0.0, 0.0, -1.0],
            ],
        }
    }
    old_jnt_name = None
    module.update(_get_children(joints, world_up_parent, 0))
    return module


def mirror(module):
    matrix = module["BASE"]["matrix"]
    for index in [1, 2, 5, 6, 9, 10, 12]:
        matrix[index] *= -1
    module["BASE"]["matrix"] = matrix
    for jnt in module:
        if jnt == "BASE":
            continue
        for space_index in range(2):
            for axis_index in range(3):
                module[jnt]["transform"][space_index][axis_index] *= -1
        module[jnt]["rotation"] *= -1
    return module
