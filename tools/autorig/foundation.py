from utilities.renaming import extend_name_to_node
from utilities.curve_tools import get_curve_points
from utilities.nodeling import lock_attributes, unlock_attributes
from maya import cmds
import json
import os


class Module(object):
    """
    Args:
        @param name:
        @param foundation_grp:
        @property template:
        @property exisits:
    """

    def __init__(self, name):
        self.name = name
        self.__joints = dict()
        self.foundation_grp = "Foundation"
        self.__long_name = "{0}|{1}".format(self.foundation_grp, self.name)
        self.__custom_template_items = ["BASE"]
        self.__module = None

    def __str__(self):
        return self.name

    @property
    def template(self):
        return self.__update_module()

    @template.setter
    def template(self, template):
        if self.exists:
            return
        self.__module = template
        if not cmds.ls(self.foundation_grp):
            cmds.group(name=self.foundation_grp, empty=True)
        crv = cmds.curve(d=1, p=template["BASE"]["shape"], name=self.name)
        cmds.xform(
            crv, matrix=template["BASE"]["matrix"], absolute=True, worldSpace=True
        )
        crv = cmds.parent(crv, self.foundation_grp)[0]
        self.__joints = dict()
        for item in template:
            if item in self.__custom_template_items:
                continue
            jnt = Joint(self, item)
            jnt.build()
            jnt.radius = template[item]["radius"]
            jnt.transform_offset = template[item]["transform"][0]
            jnt.transform = template[item]["transform"][1]
            jnt.rotation = template[item]["rotation"]
            self.__joints[item] = jnt
        for jnt in self.__joints:
            world_up = template[jnt]["world_up"]
            aim = template[jnt]["aim"]
            prnt = template[jnt]["parent"]
            if world_up:
                self.__joints[jnt].world_up = self.__joints[world_up]
            else:
                self.__joints[jnt].world_up = crv
            if aim:
                self.__joints[jnt].aim = self.__joints[aim]
            if prnt:
                self.__joints[jnt].set_parent = self.__joints[prnt]
        cmds.select(crv)

    @property
    def exists(self):
        return bool(cmds.ls(self.__long_name))

    def __update_module(self):
        matrix = cmds.getAttr("{0}.worldMatrix[0]".format(self.long_name))
        shape = get_curve_points(self.long_name)
        self.__module["BASE"] = {"matrix": matrix, "shape": shape}
        joints = cmds.listRelatives(
            self.long_name, children=True, type="transform", fullPath=True
        )
        if not joints:
            return
        for jnt in joints:
            jnt = Joint(self, jnt.split("|")[-1])
            self.module.setdefault(jnt.name, dict())
            self.module[jnt.name]["aim"] = jnt.aim
            self.module[jnt.name]["world_up"] = jnt.world_up
            self.module[jnt.name]["transform"] = [
                jnt.transform_offset,
                jnt.transform,
            ]
            self.module[jnt.name]["parent"] = jnt.parent
            self.module[jnt.name]["rotation"] = jnt.rotation
            self.module[jnt.name]["radius"] = jnt.radius


class Joint(object):
    """
    Args:
        @param name:
        @param module:
        @property up_vector:
        @property aim:
        @property world_up:
        @property parent:
        @property children:
        @property transform:
        @property rotation:
        @property transform_offset:
        @property radius:
    """

    def __init__(self, module, name):
        self.name = name
        self.module = module
        self.__offset = self.name
        self.__transform_jnt = "{0}|transform".format(self.name)
        self.__aim_jnt = "{0}|aim".format(self.__transform_jnt)
        self.__rotation_jnt = "{0}|rotation".format(self.__aim_jnt)
        self.__handle_jnt = "{0}|handle".format(self.__rotation_jnt)
        self.__display_jnt = "{0}|display".format(self.__aim_jnt)
        self.__aim_constraint = "{0}_{1}_aimCnst".format(self.module.name, self.name)
        self.__point_constraint = "{0}_{1}_pointCnst".format(
            self.module.name, self.name
        )
        self.__radius = 1.0

    def __str__(self):
        return self.__transform_jnt

    def build(self):
        # Create all nodes
        data_container = cmds.container(
            name="{0}_{1}_container".format(self.module.name, self.name),
            type="dagContainer",
            includeTransform=True,
        )
        self.__offset = cmds.group(name=self.name, empty=True, parent=self.module.name)
        self.__transform_jnt = cmds.joint(name="transform", radius=self.__radius)
        self.__aim_jnt = cmds.joint(name="aim", radius=0)
        self.__rotation_jnt = cmds.joint(name="rotation", radius=0)
        self.__handle_jnt = cmds.joint(name="handle", radius=0)
        self.__display_jnt = cmds.joint(name="display", radius=0)
        cmds.shadingNode("aimConstraint", asUtility=True, name=self.__aim_constraint)
        cmds.container(data_container, edit=True, addNode=self.__aim_constraint)
        cmds.shadingNode(
            "pointConstraint", asUtility=True, name=self.__point_constraint
        )
        cmds.container(data_container, edit=True, addNode=self.__point_constraint)
        display_mult = cmds.shadingNode(
            "multiplyDivide",
            asUtility=True,
            name="{0}_{1}_rotDispMult".format(self.module.name, self.name),
        )
        cmds.container(data_container, edit=True, addNode=display_mult)

        # Reparent
        self.__display_jnt = cmds.parent(self.__display_jnt, self.__aim_jnt)[0]
        cmds.parent(data_container, self.__offset)
        cmds.addAttr(self.__offset, longName="parent", attributeType="message")
        cmds.addAttr(self.__offset, longName="children", attributeType="message")

        # Connect nodes
        cmds.connectAttr(
            "{0}.translate".format(self.__handle_jnt), 
            "{0}.input1".format(display_mult)
        )
        cmds.connectAttr(
            "{0}.output".format(display_mult),
            "{0}.translate".format(self.__display_jnt),
        )
        cmds.connectAttr(
            "{0}.rotate".format(self.__rotation_jnt),
            "{0}.rotate".format(self.__display_jnt),
        )
        cmds.connectAttr(
            "{0}.rotatePivotTranslate".format(self.__transform_jnt),
            "{0}.constraintRotateTranslate".format(self.__aim_constraint),
        )
        cmds.connectAttr(
            "{0}.translate".format(self.__transform_jnt),
            "{0}.constraintTranslate".format(self.__aim_constraint),
        )
        cmds.connectAttr(
            "{0}.worldInverseMatrix[0]".format(self.__offset),
            "{0}.constraintParentInverseMatrix".format(self.__aim_constraint),
        )
        cmds.connectAttr(
            "{0}.rotatePivot".format(self.__transform_jnt),
            "{0}.constraintRotatePivot".format(self.__aim_constraint),
        )
        cmds.connectAttr(
            "{0}.constraintRotate".format(self.__aim_constraint),
            "{0}.rotate".format(self.__aim_jnt),
        )
        cmds.connectAttr(
            "{0}.constraintTranslate".format(self.__point_constraint),
            "{0}.translate".format(self.__handle_jnt),
        )
        cmds.connectAttr(
            "{0}.parentInverseMatrix[0]".format(self.__rotation_jnt),
            "{0}.constraintParentInverseMatrix".format(self.__point_constraint),
        )
        cmds.connectAttr(
            "{0}.rotatePivot".format(self.__rotation_jnt),
            "{0}.constraintRotatePivot".format(self.__point_constraint),
        )
        cmds.connectAttr(
            "{0}.rotatePivotTranslate".format(self.__rotation_jnt),
            "{0}.constraintRotateTranslate".format(self.__point_constraint),
        )

        # Set Attributes
        for item in (
            self.__transform_jnt,
            self.__rotation_jnt,
            self.__aim_jnt,
            self.__handle_jnt,
            self.__display_jnt,
        ):
            cmds.setAttr("{0}.overrideEnabled".format(item), 1)
        for item in self.__display_jnt, self.__handle_jnt, self.__aim_jnt:
            cmds.setAttr("{0}.overrideDisplayType".format(item), 2)
        cmds.setAttr("{0}.displayLocalAxis".format(self.__display_jnt), 1)
        cmds.setAttr("{0}.input2".format(display_mult), 0.5, 0.5, 0.5)
        cmds.setAttr("{0}.worldUpType".format(self.__aim_constraint), 0)
        cmds.setAttr("{0}.upVector".format(self.__aim_constraint), 0, 0, 1)
        cmds.setAttr("{0}.aimVector".format(self.__aim_constraint), 0, 1, 0)
        cmds.setAttr("{0}.translate".format(self.__aim_constraint), 0, 0, 0)
        cmds.setAttr("{0}.translate".format(self.__point_constraint), 0, 0, 0)
        cmds.setAttr("{0}.translate".format(data_container), 0, 0, 0)
        cmds.setAttr("{0}.translate".format(data_container), 0, 0, 0)
        
        # Lock and hide unused attributes
        lock_attributes(self.__transform_jnt, ["r", "s", "v", "radius"])
        lock_attributes(self.__offset, ["t", "r", "s", "v"])
        lock_attributes(self.__aim_jnt, ["t", "r", "s", "v", "radius"])
        lock_attributes(self.__rotation_jnt, ["t", "rx", "rz", "s", "v", "radius"])
        lock_attributes(self.__handle_jnt, ["t", "r", "s", "v", "radius"])
        lock_attributes(self.__display_jnt, ["t", "r", "s", "v", "radius"])
        self.__transform_jnt = extend_name_to_node(
            self.__transform_jnt, self.module.name
        )
        self.__aim_jnt = extend_name_to_node(self.__aim_jnt, self.module.name)
        self.__rotation_jnt = extend_name_to_node(self.__rotation_jnt, self.module.name)
        self.__handle_jnt = extend_name_to_node(self.__handle_jnt, self.module.name)
        self.__display_jnt = extend_name_to_node(self.__display_jnt, self.module.name)

    @property
    def up_vector(self):
        cmds.getAttr("{0}.upVector".format(self.__aim_constraint))

    @up_vector.setter
    def up_vector(self, vector):
        cmds.setAttr("{0}.upVector".format(self.__aim_constraint), *vector)

    @property
    def aim(self):
        parent = None
        connected = cmds.listConnections(
            "{0}.target[0].targetTranslate".format(self.__aim_constraint),
            d=False,
            s=True,
        )
        if connected:
            parent = cmds.listRelatives(connected, parent=True)[0]
        return parent

    @aim.setter
    def aim(self, jnt):
        cmds.connectAttr(
            "{0}.translate".format(jnt),
            "{0}.target[0].targetTranslate".format(self.__aim_constraint),
            force=True,
        )
        cmds.connectAttr(
            "{0}.parentMatrix[0]".format(jnt),
            "{0}.target[0].targetParentMatrix".format(self.__aim_constraint),
            force=True,
        )
        cmds.connectAttr(
            "{0}.rotatePivotTranslate".format(jnt),
            "{0}.target[0].targetRotateTranslate".format(self.__aim_constraint),
            force=True,
        )
        cmds.connectAttr(
            "{0}.translate".format(jnt),
            "{0}.target[0].targetTranslate".format(self.__point_constraint),
            force=True,
        )
        cmds.connectAttr(
            "{0}.parentMatrix".format(jnt),
            "{0}.target[0].targetParentMatrix".format(self.__point_constraint),
            force=True,
        )
        cmds.connectAttr(
            "{0}.rotatePivot".format(jnt),
            "{0}.target[0].targetRotatePivot".format(self.__point_constraint),
            force=True,
        )
        cmds.connectAttr(
            "{0}.rotatePivotTranslate".format(jnt),
            "{0}.target[0].targetRotateTranslate".format(self.__point_constraint),
            force=True,
        )

    @property
    def world_up(self):
        parent = None
        connected = cmds.listConnections(
            "{0}.worldUpMatrix".format(self.__aim_constraint), d=False, s=True
        )
        if connected:
            parent = cmds.listRelatives(connected, parent=True)[0]
        return parent

    @world_up.setter
    def world_up(self, jnt):
        jnt = str(jnt)
        cmds.setAttr("{0}.worldUpType".format(self.__aim_constraint), 1)
        cmds.connectAttr(
            "{0}.worldMatrix[0]".format(jnt),
            "{0}.worldUpMatrix".format(self.__aim_constraint),
            force=True,
        )

    @property
    def parent(self):
        node = cmds.listConnections("{0}.parent".format(self.__offset), d=False, s=True)
        if node:
            return node[0]

    @parent.setter
    def parent(self, parent):
        cmds.connectAttr(
            "{0}.children".format(parent.__offset),
            "{0}.parent".format(self.__offset),
        )

    @property
    def children(self):
        return cmds.listConnections(
            "{0}.children".format(self.__offset), d=False, s=True
        )

    @property
    def transform(self):
        return list(cmds.getAttr("{0}.translate".format(self.__transform_jnt))[0])

    @transform.setter
    def transform(self, amount):
        cmds.setAttr("{0}.translate".format(self.__transform_jnt), *amount)

    @property
    def rotation(self):
        return cmds.getAttr("{0}.rotateY".format(self.__rotation_jnt))

    @rotation.setter
    def rotation(self, amount):
        cmds.setAttr("{0}.rotateY".format(self.__rotation_jnt), amount)

    @property
    def transform_offset(self):
        return list(cmds.getAttr("{0}.translate".format(self.__offset))[0])

    @transform_offset.setter
    def transform_offset(self, amount):
        unlock_attributes(self.__offset, ["translate"])
        cmds.setAttr("{0}.translate".format(self.__offset), *amount)
        lock_attributes(self.__offset, ["translate"])

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, radius):
        if cmds.ls(self.__transform_jnt):
            cmds.setAttr("{0}.radius".format(self.__transform_jnt), lock=False)
            cmds.setAttr("{0}.radius".format(self.__transform_jnt), radius)
            cmds.setAttr("{0}.radius".format(self.__transform_jnt), lock=True)
            self.__radius = radius
