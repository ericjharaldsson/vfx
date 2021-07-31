from maya import cmds
from . import modules
from utilities.curve_tools import get_curve_points
from utilities.renaming import extend_name_to_node
from utilities import nodeling, renaming
import numpy as np
from rig_tools.controls import base

def create_twist(top, bottom, from_top=True, amount=4):
    jnt_name = top.split("_")[0]
    jnts = list()
    cmds.select(top)
    for i in range(amount + 1):
        jnt = cmds.joint(name="{0}{1:02}_twist".format(jnt_name, i))
        jnts.append(jnt)
    bottom_pos = cmds.getAttr("{0}.translate".format(bottom))[0]
    bottom_dist = max(bottom_pos)
    aim_axis = ["X", "Y", "Z"][bottom_pos.index(bottom_dist)]
    twist_dist = bottom_dist / amount
    for jnt in jnts[1:]:
        cmds.setAttr("{0}.translate{1}".format(jnt, aim_axis), twist_dist)
    mult = cmds.shadingNode(
        "multiplyDivide", asUtility=True, name="{0}Twist_mult".format(jnt_name)
    )
    if from_top:
        cmds.setAttr("{0}.input2X".format(mult), -1)
        cmds.connectAttr(
            "{0}.rotate{1}".format(top, aim_axis), "{0}.input1X".format(mult)
        )
        cmds.connectAttr(
            "{0}.outputX".format(mult),
            "{0}.rotate{1}".format(jnts[0], aim_axis),
        )
        cmds.connectAttr(
            "{0}.rotate{1}".format(top, aim_axis), "{0}.input1Y".format(mult)
        )
    else:
        cmds.connectAttr(
            "{0}.rotate{1}".format(bottom, aim_axis),
            "{0}.input1Y".format(mult),
        )
    cmds.setAttr("{0}.input2Y".format(mult), 1 / float(amount))

    for jnt in jnts[1:]:
        cmds.connectAttr(
            "{0}.outputY".format(mult), "{0}.rotate{1}".format(jnt, aim_axis)
        )


class Blueprint(object):
    def __init__(self):
        self._root = "Blueprint"
        self._ctrl = "{0}|scale_crv".format(self._root)
        self._ctrl_grp = "{0}|ctrl_grp".format(self._root)
        if not self._exists():
            self._create_blueprint()

    def _create_blueprint(self):
        blueprint = cmds.group(name=self._root, empty=True)
        nodeling.lock_attributes(blueprint, ["t", "r", "s"])
        shape = [
            [-12, 0.0, -12],
            [-12, 0.0, 12],
            [12, 0.0, 12],
            [12, 0.0, -12],
            [-12, 0.0, -12],
        ]
        ctrl = self._ctrl.split("|")[-1]
        cmds.curve(name="scale_crv", degree=1, editPoint=shape)
        cmds.parent(ctrl, "Blueprint")
        nodeling.lock_attributes(self._ctrl, ["t", "r"])
        ctrl_grp = cmds.group(name="ctrl_grp", empty=True)
        cmds.parent(ctrl_grp, "Blueprint")
        nodeling.lock_attributes(self._ctrl_grp, ["t", "r", "s"])
        cmds.setAttr(
            "{0}.sx".format(self._ctrl), channelBox=False, keyable=False
        )
        cmds.setAttr(
            "{0}.sy".format(self._ctrl), channelBox=False, keyable=False
        )
        cmds.setAttr(
            "{0}.sz".format(self._ctrl), channelBox=False, keyable=False
        )
        cmds.setAttr(
            "{0}.v".format(self._ctrl), channelBox=False, keyable=False
        )
        cmds.addAttr(
            self._ctrl,
            ln="rigScale",
            at="float",
        )
        cmds.setAttr(
            "{0}.rigScale".format(self._ctrl),
            1,
            edit=True,
            channelBox=True,
        )
        cmds.connectAttr(
            "{0}.rigScale".format(self._ctrl), "{0}.sx".format(self._ctrl)
        )
        cmds.connectAttr(
            "{0}.rigScale".format(self._ctrl), "{0}.sy".format(self._ctrl)
        )
        cmds.connectAttr(
            "{0}.rigScale".format(self._ctrl), "{0}.sz".format(self._ctrl)
        )
        cmds.select(self._ctrl)

    def generate_skeleton(self):
        cmds.setAttr("{0}.v".format(self.root), False)
        base.base(scale=self.scale)
        for module_name in self.modules:
            module = Module(module_name)
            module.build_joints()
        for module_name in self.modules:
            module = Module(module_name)
            if module.parent:
                parent_jnt = Joint(self, module.parent).jnt_name
                nodeling.parent(parent_jnt, module.top_jnt)
            else:
                nodeling.parent("joints_grp", module.top_jnt)

    def _exists(self):
        return cmds.ls("|{0}".format(self._root))

    @property
    def root(self):
        return self._root

    @property
    def ctrl(self):
        return self._ctrl

    @property
    def ctrl_grp(self):
        return self._ctrl_grp

    @property
    def modules(self):
        return cmds.listRelatives(
            self._ctrl_grp, children=True, type="transform"
        )

    @property
    def scale(self):
        return cmds.getAttr("{0}.rigScale".format(self._ctrl))


class Module(object):
    def __init__(self, name, template=None, axis="YZX"):
        self.name = name
        self.blueprint = Blueprint()
        self.long_name = "{0}|{1}".format(self.blueprint.ctrl_grp, self.name)
        self._custom_template_items = ["BASE"]
        self._module = dict()
        self.joints = list()
        self._axis = axis
        self._side = renaming.find_side(self.name)
        self.top_jnt = None
        if self.exists:
            self._update_module()
        else:
            self._init_module(template)
        cmds.select(self.long_name)

    def __str__(self):
        return self.name

    def _init_module(self, template):
        if isinstance(template, dict):
            self._module = template
        elif isinstance(template, str):
            templates = modules.Modules()
            if template in templates.list:
                self._module = templates.get(template)
        else:
            return
        if self._side:
            self._module = modules.add_side_prefix(self._module, self._side)

        self._base_nodes()
        joints = dict()
        for item in self._module["JOINTS"]:
            joints[item] = self._create_joint_handle(item)

        for item in joints:
            self._connect_joint_handle(joints, item)
            if not joints[item].parent:
                self.top_jnt = joints[item].jnt_name

    def _base_nodes(self):
        crv_shape = np.array(self._module["BASE"]["shape"])
        scale = self.blueprint.scale
        crv_shape *= scale
        crv = cmds.curve(d=1, p=crv_shape, name=self.name)
        cmds.parent(crv, self.blueprint.ctrl_grp)
        cmds.addAttr(
            self.long_name, longName="parent", attributeType="message"
        )
        self.parent = self._module["BASE"]["parent"]
        matrix = np.reshape(self._module["BASE"]["matrix"], (1, -1)).tolist()
        cmds.xform(
            self.long_name,
            matrix=matrix[0],
            absolute=True,
            worldSpace=True,
        )
        pos = np.array(cmds.getAttr("{0}.translate.".format(self.long_name)))
        pos = (pos * scale).tolist()[0]
        cmds.setAttr("{0}.translate".format(self.long_name), *pos)

    def _create_joint_handle(self, item):

        """
        creates all the nodes needed for a joint control
        :param item: dict, containing the attributes for a joint.
        :return: class object, controlling the joint control
        """
        template_jnt = self._module["JOINTS"][item]
        jnt = Joint(self, item)
        jnt.build_joint_control()
        jnt.radius = template_jnt["radius"] * self.blueprint.scale
        offset = np.array(template_jnt["transform"]) * self.blueprint.scale
        jnt.transform_offset = offset[0]
        jnt.transform = template_jnt["transform"][1]
        jnt.rotation = template_jnt["rotation"]
        jnt.mirrored = self._module["BASE"]["mirrored"]
        jnt.axis = self._axis
        return jnt

    def _connect_joint_handle(self, joints, jnt):
        """
        connects the joint controls to each other
        :param joints: dict, containing all joint classes
        :param jnt: class object, that controls the joint
        :return: None
        """

        tmpl = self._module["JOINTS"][jnt]
        world_up = tmpl["world_up"]
        aim = tmpl["aim"]
        parent = tmpl["parent"]
        if world_up in joints:
            world_up = joints[world_up]
        elif world_up:
            world_up = world_up
        else:
            world_up = self.long_name
        joints[jnt].world_up = world_up
        if aim:
            # joints[aim].transform_jnt
            joints[jnt].aim = joints[aim].transform_jnt
        if parent:
            joints[jnt].parent = parent

    def _update_module(self):

        """
        reads the settings from the scene and updates the template dict
        :return: None
        """

        self.joints = list()
        inverse_scale = 1.0 / self.blueprint.scale
        matrix_scale = np.full((4, 4), 1.0)
        matrix_scale[-1, :-1] = inverse_scale
        flat_matrix = cmds.xform(
            self.long_name, matrix=True, query=True, worldSpace=True
        )
        matrix = np.reshape(flat_matrix, (-1, 4))
        matrix = (matrix * matrix_scale).tolist()
        shape = get_curve_points(self.long_name)
        shape = (np.array(shape) * inverse_scale).tolist()
        self._module["BASE"] = {
            "matrix": matrix,
            "shape": shape,
            "parent": self.parent,
        }
        joints = cmds.listRelatives(
            self.long_name, children=True, type="transform", fullPath=True
        )
        if not joints:
            return
        mod_jnts = dict()
        for jnt in joints:
            jnt = Joint(self, jnt.split("|")[-1])
            transform = [jnt.transform_offset, jnt.transform]
            transform = (np.array(transform) * inverse_scale).tolist()
            world_up = None
            if cmds.ls(jnt.world_up, long=True)[0] in joints:
                world_up = jnt.world_up
            mod_jnts.setdefault(jnt.name, dict())
            mod_jnt = mod_jnts[jnt.name]
            mod_jnt["aim"] = jnt.aim
            mod_jnt["world_up"] = world_up
            mod_jnt["transform"] = transform
            mod_jnt["parent"] = jnt.parent
            mod_jnt["rotation"] = jnt.rotation
            mod_jnt["radius"] = jnt.radius * inverse_scale
            self.joints.append(jnt)
            if not jnt.parent:
                self.top_jnt = jnt.jnt_name
        self._module["JOINTS"] = mod_jnts
        self._axis = jnt.axis
        self._module["BASE"]["mirrored"] = jnt.mirrored

    @property
    def template(self):
        """
        :return: dict, module data from scene
        """
        self._update_module()
        return self._module

    @property
    def exists(self):
        """
        Checks if module exists in scene
        :return: bool, if module top folder exists in rig hierarchy
        """
        return bool(cmds.ls(self.long_name))

    def build_joints(self):
        cmds.select(clear=True)
        for jnt in self.joints:
            jnt.update_jnt()
        for jnt in self.joints:
            if not jnt.parent:
                continue
            parent_name = jnt.parent.split("|")[-1]
            parent = [x for x in self.joints if x.name == parent_name][0]
            nodeling.parent(parent.jnt_name, jnt.jnt_name)

    @property
    def parent(self):
        node = cmds.listConnections(
            "{0}.parent".format(self.long_name), d=False, s=True
        )
        if node:
            return node[0]

    @parent.setter
    def parent(self, parent):
        if parent:
            jnt = Joint(self, parent)
            cmds.connectAttr(
                "{0}.children".format(jnt.name),
                "{0}.parent".format(self.long_name),
                force=True,
            )
        else:
            attr = cmds.listConnections(
                "scale_crv.sx", destination=False, source=True, plugs=True
            )
            if attr:
                cmds.disconnectAttr(attr[0], "scale_crv.sx")

    @property
    def axis(self):
        return self._axis


class Joint(object):
    def __init__(self, module, name):
        self.name = name
        self.jnt_name = "{0}_jnt".format(self.name)
        self.module = module
        form_list = [self.module, self.name]
        self._offset = "{0}|{1}".format(*form_list)
        self._transform_jnt = "{0}|{1}|transform".format(*form_list)
        self._aim_jnt = "{0}|aim".format(self._transform_jnt)
        self._rotation_jnt = "{0}|rotation".format(self._aim_jnt)
        self._handle_jnt = "{0}|handle".format(self._rotation_jnt)
        self._display_jnt = "{0}|display".format(self._aim_jnt)
        self._aim_constraint = "{0}_{1}_aimCnst".format(*form_list)
        self._data_container = "{0}_{1}_container".format(*form_list)
        self._point_constraint = "{0}_{1}_pointCnst".format(*form_list)
        self._display_mult = "{0}_{1}_rotDispMult".format(*form_list)
        self._radius = 1.0
        self._mirrored = False
        self._axis = "YZX"

    def __str__(self):
        return self._transform_jnt

    def __repr__(self):
        return self._transform_jnt

    def _create_base(self):
        """
        creates the joint control nodes
        :return: None
        """
        cmds.container(
            name=self._data_container,
            type="dagContainer",
            includeTransform=True,
        )
        split = self._offset.split("|")
        cmds.group(
            name="|{0}".format(split[-1]),
            empty=True,
            parent="{0}|{1}".format(self.module.blueprint.ctrl_grp, split[-2]),
        )
        nodeling.parent(self._offset, self._data_container)
        cmds.addAttr(self._offset, longName="parent", attributeType="message")
        cmds.addAttr(
            self._offset, longName="children", attributeType="message"
        )

    def _create_joints(self, jnt):
        """
        creates the joint control nodes
        :return: None
        """
        cmds.select(clear=True)
        split = jnt.split("|")
        if len(split) == 1:
            jnt_name = jnt
            parent = None
        else:
            jnt_name = split[-1]
            parent = "|".join(split[:-1])
        new_jnt = cmds.joint(name=jnt_name, radius=self._radius)
        nodeling.parent(parent, new_jnt)

    def _primary_axis(self):
        if self._mirrored:
            normal = -1
        else:
            normal = 1
        aim, rotate, spread = self._axis.upper()
        for attr in ["aimVector", "worldUpVector", "upVector"]:
            cmds.setAttr("{0}.{1}".format(self._aim_constraint, attr), 0, 0, 0)

        cmds.setAttr(
            "{0}.aimVector{1}".format(self._aim_constraint, aim), normal
        )
        cmds.setAttr(
            "{0}.upVector{1}".format(self._aim_constraint, rotate), normal
        )
        cmds.setAttr(
            "{0}.worldUpVector{1}".format(self._aim_constraint, rotate), 1
        )

    def build_joint_control(self):
        """
        builds a joint control
        :return: None
        """
        self._create_base()
        for jnt in [
            self._transform_jnt,
            self._aim_jnt,
            self._rotation_jnt,
            self._handle_jnt,
            self._display_jnt,
        ]:
            self._create_joints(jnt)

        for node_type, name in [
            ["aimConstraint", self._aim_constraint],
            ["pointConstraint", self._point_constraint],
            ["multiplyDivide", self._display_mult],
        ]:
            cmds.shadingNode(node_type, asUtility=True, name=name)
            cmds.container(self._data_container, edit=True, addNode=name)

        # Connect nodes
        for source, destination in [
            [[self._handle_jnt, "translate"], [self._display_mult, "input1"]],
            [[self._display_mult, "output"], [self._display_jnt, "translate"]],
            [[self._rotation_jnt, "rotate"], [self._display_jnt, "rotate"]],
            [
                [self._transform_jnt, "rotatePivotTranslate"],
                [self._aim_constraint, "constraintRotateTranslate"],
            ],
            [
                [self._transform_jnt, "translate"],
                [self._aim_constraint, "constraintTranslate"],
            ],
            [
                [self._offset, "worldInverseMatrix[0]"],
                [self._aim_constraint, "constraintParentInverseMatrix"],
            ],
            [
                [self._transform_jnt, "rotatePivot"],
                [self._aim_constraint, "constraintRotatePivot"],
            ],
            [
                [self._aim_constraint, "constraintRotate"],
                [self._aim_jnt, "rotate"],
            ],
            [
                [self._point_constraint, "constraintTranslate"],
                [self._handle_jnt, "translate"],
            ],
            [
                [self._rotation_jnt, "parentInverseMatrix[0]"],
                [self._point_constraint, "constraintParentInverseMatrix"],
            ],
            [
                [self._rotation_jnt, "rotatePivot"],
                [self._point_constraint, "constraintRotatePivot"],
            ],
            [
                [self._rotation_jnt, "rotatePivotTranslate"],
                [self._point_constraint, "constraintRotateTranslate"],
            ],
        ]:
            cmds.connectAttr(".".join(source), ".".join(destination))

        # Set Attributes
        for node, attr, value in [
            [self._transform_jnt, "overrideEnabled", [1]],
            [self._transform_jnt, "overrideEnabled", [1]],
            [self._transform_jnt, "overrideRGBColors", [1]],
            [self._transform_jnt, "overrideColorR", [0.333]],
            [self._transform_jnt, "overrideColorG", [0.667]],
            [self._transform_jnt, "overrideColorB", [0.392]],
            [self._transform_jnt, "jointOrient", [0, 0, 0]],
            [self._rotation_jnt, "overrideEnabled", [1]],
            [self._rotation_jnt, "radius", [0]],
            [self._aim_jnt, "overrideEnabled", [1]],
            [self._aim_jnt, "overrideDisplayType", [2]],
            [self._aim_jnt, "radius", [0]],
            [self._aim_jnt, "jointOrient", [0, 0, 0]],
            [self._handle_jnt, "overrideEnabled", [1]],
            [self._handle_jnt, "overrideDisplayType", [2]],
            [self._handle_jnt, "radius", [0]],
            [self._display_jnt, "overrideEnabled", [1]],
            [self._display_jnt, "overrideDisplayType", [2]],
            [self._display_jnt, "displayLocalAxis", [1]],
            [self._display_jnt, "radius", [0]],
            [self._display_mult, "input2", [0.5, 0.5, 0.5]],
            [self._aim_constraint, "worldUpType", [0]],
            [self._aim_constraint, "translate", [0, 0, 0]],
            [self._point_constraint, "translate", [0, 0, 0]],
            [self._data_container, "translate", [0, 0, 0]],
            [self._data_container, "translate", [0, 0, 0]],
        ]:
            cmds.setAttr("{0}.{1}".format(node, attr), *value)

        # Lock and hide unused attributes
        nodeling.lock_attributes(
            self._transform_jnt, ["r", "s", "v", "radius"]
        )
        nodeling.lock_attributes(self._offset, ["t", "r", "s", "v"])
        nodeling.lock_attributes(self._aim_jnt, ["t", "r", "s", "v", "radius"])
        nodeling.lock_attributes(
            self._rotation_jnt, ["t", "rx", "rz", "s", "v", "radius"]
        )
        nodeling.lock_attributes(
            self._handle_jnt, ["t", "r", "s", "v", "radius"]
        )
        nodeling.lock_attributes(
            self._display_jnt, ["t", "r", "s", "v", "radius"]
        )
        self._transform_jnt = extend_name_to_node(
            self._transform_jnt, str(self.module)
        )
        self._primary_axis()

    def update_jnt(self):
        if not cmds.ls(self.jnt_name):
            cmds.select(clear=True)
            cmds.joint(name=self.jnt_name)
        cmds.xform(
            self.jnt_name, absolute=True, matrix=self.matrix, worldSpace=True
        )
        cmds.makeIdentity(self.jnt_name, apply=True, t=0, r=1, s=0, n=0, pn=1)

    @staticmethod
    def axis_from_vector(v):
        vector = [abs(x) for x in v]
        axes = "xyz"
        return axes[vector.index(max(vector))]

    @property
    def exists(self):
        """
        check if joint control exists
        :return: bool, True if control exists
        """
        return bool(cmds.ls(self.jnt_name))

    @property
    def aim(self):
        parent = None
        connected = cmds.listConnections(
            "{0}.target[0].targetTranslate".format(self._aim_constraint),
            d=False,
            s=True,
        )
        if connected:
            parent = cmds.listRelatives(connected, parent=True)[0]
        return parent

    @aim.setter
    def aim(self, jnt):
        for source, destination in [
            [
                [jnt, "translate"],
                [self._aim_constraint, "target[0].targetTranslate"],
            ],
            [
                [jnt, "parentMatrix[0]"],
                [self._aim_constraint, "target[0].targetParentMatrix"],
            ],
            [
                [jnt, "rotatePivotTranslate"],
                [self._aim_constraint, "target[0].targetRotateTranslate"],
            ],
            [
                [jnt, "translate"],
                [self._point_constraint, "target[0].targetTranslate"],
            ],
            [
                [jnt, "parentMatrix"],
                [self._point_constraint, "target[0].targetParentMatrix"],
            ],
            [
                [jnt, "rotatePivot"],
                [self._point_constraint, "target[0].targetRotatePivot"],
            ],
            [
                [jnt, "rotatePivotTranslate"],
                [self._point_constraint, "target[0].targetRotateTranslate"],
            ],
        ]:
            cmds.connectAttr(
                ".".join(source), ".".join(destination), force=True
            )

    @property
    def world_up(self):
        parent = None
        connected = cmds.listConnections(
            "{0}.worldUpMatrix".format(self._aim_constraint), d=False, s=True
        )
        if connected:
            if connected != str(self.module):
                parent = cmds.listRelatives(connected, parent=True)
                if parent:
                    parent = parent[0]
        return parent

    @world_up.setter
    def world_up(self, jnt):
        jnt = str(jnt)
        cmds.setAttr("{0}.worldUpType".format(self._aim_constraint), 1)
        cmds.connectAttr(
            "{0}.worldMatrix[0]".format(jnt),
            "{0}.worldUpMatrix".format(self._aim_constraint),
            force=True,
        )

    @property
    def parent(self):
        node = cmds.listConnections(
            "{0}.parent".format(self._offset), d=False, s=True
        )
        if node:
            return extend_name_to_node(node[0], str(self.module))

    @parent.setter
    def parent(self, parent):
        cmds.connectAttr(
            "{0}.children".format(parent),
            "{0}.parent".format(self._offset),
        )

    @property
    def children(self):
        return cmds.listConnections(
            "{0}.children".format(self._offset), d=False, s=True
        )

    @property
    def transform(self):
        return list(
            cmds.getAttr("{0}.translate".format(self._transform_jnt))[0]
        )

    @transform.setter
    def transform(self, amount):
        cmds.setAttr("{0}.translate".format(self._transform_jnt), *amount)

    @property
    def rotation(self):
        return cmds.getAttr("{0}.rotateY".format(self._rotation_jnt))

    @rotation.setter
    def rotation(self, amount):
        cmds.setAttr("{0}.rotateY".format(self._rotation_jnt), amount)

    @property
    def transform_jnt(self):
        return self._transform_jnt

    @property
    def transform_offset(self):
        return list(cmds.getAttr("{0}.translate".format(self._offset))[0])

    @transform_offset.setter
    def transform_offset(self, amount):
        nodeling.unlock_attributes(self._offset, ["translate"])
        cmds.setAttr("{0}.translate".format(self._offset), *amount)
        nodeling.lock_attributes(self._offset, ["translate"])

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, radius):
        if cmds.ls(self._transform_jnt):
            cmds.setAttr("{0}.radius".format(self._transform_jnt), lock=False)
            cmds.setAttr("{0}.radius".format(self._transform_jnt), radius)
            cmds.setAttr("{0}.radius".format(self._transform_jnt), lock=True)
            self._radius = radius

    @property
    def matrix(self):
        return cmds.xform(
            self._rotation_jnt,
            absolute=True,
            matrix=True,
            query=True,
            worldSpace=True,
        )

    @property
    def mirrored(self):
        return self._mirrored

    @mirrored.setter
    def mirrored(self, value):
        self._mirrored = value
        self._primary_axis()

    @property
    def axis(self):
        last = "xyz"
        axis = ""
        for attr in "aimVector", "upVector":
            vector = cmds.getAttr("{0}.{1}".format(self._aim_constraint, attr))
            x = self.axis_from_vector(vector[0])
            axis += x
            last = last.replace(x, "")

        axis += last
        return axis

    @axis.setter
    def axis(self, axis):
        self._axis = axis
        self._primary_axis()


class FootRoll(object):
    def __init__(
            self,
            name=None,
            ancle=None,
            toe=None,
            tip=None,
            heel="heel",
            bank_out="bankOut",
            bank_in="bankIn",
            foot_tip="footTip",
            ik_handle=None
    ):
        self.heel_ctrl = None
        self.bank_out_ctrl = None
        self.bank_in_ctrl = None
        self.tip_ctrl = None
        self.aim_helper = None
        self.toe_ctrl = None
        self.heel = heel
        self.bank_out = bank_out
        self.bank_in = bank_in
        self.foot_tip = foot_tip
        self._ancle = ancle
        self.toe = toe
        self.tip = tip
        self.parent = None
        self.ik_handle = ik_handle
        if name == None:
            self.name = ancle
        else:
            self.name = name

    @property
    def ancle(self):
        return self._ancle

    @ancle.setter
    def ancle(self, ancle):
        self._ancle = ancle
        if self.name == None:
            self.name = ancle

    @staticmethod
    def zero_out(node):
        cmds.xform(
            node,
            translation=(0, 0, 0),
            rotation=(0, 0, 0),
            scale=(1, 1, 1))

    @staticmethod
    def match(child, parent):
        cmds.matchTransform(
            child, parent, position=True, rotation=False, scale=False
        )

    def create_markers(self):
        ancle_pos = np.array(cmds.xform(
            self.ancle,
            translation=True,
            query=True,
            worldSpace=True
        ))
        tip_pos = np.array(cmds.xform(
            self.tip,
            translation=True,
            query=True,
            worldSpace=True
        ))

        dist = abs(ancle_pos[2] - tip_pos[2])
        thicknes = dist * 0.25

        tip_pos = tip_pos * np.array([1, 0, 1])
        if not cmds.ls(self.foot_tip):
            cmds.spaceLocator(name=self.foot_tip)
        cmds.xform(self.foot_tip, translation=tip_pos, worldSpace=True, absolute=True)
        if not cmds.ls(self.heel):
            cmds.spaceLocator(name=self.heel)
        heel_pos = ancle_pos * np.array([1, 0, 1])
        heel_pos += np.array([0, 0, -thicknes])
        cmds.xform(self.heel, translation=heel_pos, worldSpace=True, absolute=True)

        bank_out_pos = ((tip_pos + heel_pos) / 2) + np.array([thicknes, 0, 0])
        if not cmds.ls(self.bank_out):
            cmds.spaceLocator(name=self.bank_out)
        cmds.xform(self.bank_out, translation=bank_out_pos, worldSpace=True, absolute=True)

        bank_in_pos = ((tip_pos + heel_pos) / 2) + np.array([-thicknes, 0, 0])
        if not cmds.ls(self.bank_in):
            cmds.spaceLocator(name=self.bank_in)
        cmds.xform(self.bank_in, translation=bank_in_pos, worldSpace=True, absolute=True)

    def create_groups(self):
        if cmds.ls("{0}_ctrl".format(self.name)):
            self.main_ctrl = "{0}_ctrl".format(self.name)
        else:
            self.main_ctrl = base.control(
                prefix=self.name,
                point_match=self.ancle,
                scale=2.5,
                offsets=3,
                rotate_match=None,
                scale_match=None,
                parent=self.parent,
                point_constraint=None,
                orient_constraint=None,
                scale_constraint=None,
                aim_constraint=None,
                pole_constraint=None,
                shape="box",
                direction="x",
                lock=[],
                follow=[],
            )
        cmds.addAttr(self.main_ctrl, longName="footRoll", keyable=True)
        cmds.addAttr(self.main_ctrl, longName="toeRotate", keyable=True)
        cmds.addAttr(self.main_ctrl, longName="banking", keyable=True)
        cmds.addAttr(self.main_ctrl, longName="tipRotate", keyable=True)
        cmds.addAttr(self.main_ctrl, longName="heelRotate", keyable=True)

        heel_grp = cmds.group(name="{0}_heelRoll_grp".format(self.name), empty=True)
        cmds.parent(heel_grp, self.main_ctrl)
        self.match(heel_grp, self.heel)
        cmds.xform(heel_grp, rotation=(180, 0, 0))
        self.heel_ctrl = cmds.group(name="{0}_heelRoll_ctrl".format(self.name), empty=True)
        cmds.parent(self.heel_ctrl, heel_grp)
        self.zero_out(self.heel_ctrl)

        bank_out_grp = cmds.group(name="{0}_bankOutRoll_grp".format(self.name), empty=True)
        cmds.parent(bank_out_grp, self.heel_ctrl)
        self.match(bank_out_grp, self.bank_out)
        cmds.xform(bank_out_grp, rotation=(0, 0, 0))
        self.bank_out_ctrl = cmds.group(name="{0}_bankOutRoll_ctrl".format(self.name), empty=True)
        cmds.parent(self.bank_out_ctrl, bank_out_grp)
        self.zero_out(self.bank_out_ctrl)

        bank_in_grp = cmds.group(name="{0}_bankInRoll_grp".format(self.name), empty=True)
        cmds.parent(bank_in_grp, self.bank_out_ctrl)
        self.match(bank_in_grp, self.bank_in)
        cmds.xform(bank_in_grp, rotation=(0, 0, 0))
        self.bank_in_ctrl = cmds.group(name="{0}_bankInRoll_ctrl".format(self.name), empty=True)
        cmds.parent(self.bank_in_ctrl, bank_in_grp)
        self.zero_out(self.bank_in_ctrl)

        tip_grp = cmds.group(name="{0}_tipRoll_grp".format(self.name), empty=True)
        cmds.parent(tip_grp, self.bank_in_ctrl)
        self.match(tip_grp, self.foot_tip)
        cmds.xform(tip_grp, rotation=(-180, -90, 0))
        self.tip_ctrl = cmds.group(name="{0}_tipRoll_ctrl".format(self.name), empty=True)
        cmds.parent(self.tip_ctrl, tip_grp)
        self.zero_out(self.tip_ctrl)
        self.aim_helper = cmds.group(name="{0}_aimHelp_grp".format(self.name), empty=True)
        cmds.parent(self.aim_helper, tip_grp)
        self.match(self.aim_helper, self.heel)

        toe_grp = cmds.group(name="{0}_toeRotate_grp".format(self.name), empty=True)
        cmds.parent(toe_grp, self.tip_ctrl)
        self.match(toe_grp, self.toe)
        cmds.xform(toe_grp, rotation=(0, 0, -180))
        self.toe_ctrl = cmds.group(name="{0}_toeRotate_ctrl".format(self.name), empty=True)
        cmds.parent(self.toe_ctrl, toe_grp)
        self.zero_out(self.toe_ctrl)

        cmds.aimConstraint(
            self.toe_ctrl,
            self._ancle,
            worldUpObject=self.aim_helper,
            upVector=(0, -1, 0),
            worldUpType="object",
            aimVector=(1, 0, 0)
        )
        cmds.aimConstraint(
            self.tip_ctrl,
            self.toe,
            worldUpObject=self.aim_helper,
            upVector=(0, -1, 0),
            worldUpType="object",
            aimVector=(1, 0, 0)
        )
        if self.ik_handle:
            cmds.pointConstraint(self.toe_ctrl, self.ik_handle, mo=True)
        self._sdk()

    def _sdk(self):
        drive_base = 10
        driven_base = 60
        for driven, driver, driver_value, driven_value in [
            [
                "{0}.rx".format(self.heel_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                drive_base,
                driven_base
            ],
            [
                "{0}.rx".format(self.heel_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.ry".format(self.heel_ctrl),
                "{0}.heelRotate".format(self.main_ctrl),
                -drive_base, -driven_base],
            [
                "{0}.ry".format(self.heel_ctrl),
                "{0}.heelRotate".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.ry".format(self.heel_ctrl),
                "{0}.heelRotate".format(self.main_ctrl),
                drive_base,
                driven_base
            ],
            [
                "{0}.rz".format(self.bank_out_ctrl),
                "{0}.banking".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.rz".format(self.bank_out_ctrl),
                "{0}.banking".format(self.main_ctrl),
                drive_base,
                driven_base
            ],
            [
                "{0}.rz".format(self.bank_in_ctrl),
                "{0}.banking".format(self.main_ctrl),
                -drive_base,
                -driven_base
            ],
            [
                "{0}.rz".format(self.bank_in_ctrl),
                "{0}.banking".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.rx".format(self.tip_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.rx".format(self.tip_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                drive_base * 0.5,
                0
            ],
            [
                "{0}.rx".format(self.tip_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                drive_base,
                driven_base * 1.5
            ],
            [
                "{0}.ry".format(self.tip_ctrl),
                "{0}.tipRotate".format(self.main_ctrl),
                -drive_base,
                driven_base
            ],
            [
                "{0}.ry".format(self.tip_ctrl),
                "{0}.tipRotate".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.ry".format(self.tip_ctrl),
                "{0}.tipRotate".format(self.main_ctrl),
                drive_base,
                -driven_base
            ],
            [
                "{0}.rz".format(self.toe_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                0,
                0
            ],
            [
                "{0}.rz".format(self.toe_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                drive_base * 0.5,
                -driven_base
            ],
            [
                "{0}.rz".format(self.toe_ctrl),
                "{0}.footRoll".format(self.main_ctrl),
                drive_base,
                0
            ]
        ]:
            cmds.setDrivenKeyframe(
                driven,
                currentDriver=driver,
                driverValue=driver_value,
                value=driven_value
            )
