from maya import cmds
from .foundation import Module
import json
import os

root = "Rig"
jnt_grp = "skeleton"
ctrl_grp = "Ctrl"
base_ctrl = "baseCtrl{0}"


def _load_shapes():
    shape_dir = os.path.dirname(os.path.abspath(__file__))
    shape_file = os.path.join(shape_dir, "shapes.json")
    with open(shape_file) as f:
        shapes = json.load(f)
    return shapes


def generate_base(offsets):
    shapes = _load_shapes()
    if not cmds.ls(root):
        cmds.group(name=root, empty=True)
    old_mult = None
    if not cmds.ls(ctrl_grp):
        for ofs in range(offsets, 0, -1):
            ctrl = cmds.curve(
                name=base_ctrl.format(ofs), d=1, p=shapes["base"][ofs]
            )
            ctrl_shape = cmds.listRelatives(ctrl, children=True)[0]
            cmds.setAttr(
                    "{0}.visibility".format(ctrl),
                    lock=True,
                    keyable=False,
                    channelBox=False
            )
            if ofs == offsets:
                old_ctrl = ctrl
                old_ctrl_shape = ctrl_shape
                continue
            cmds.addAttr(ctrl, longName="offs", attributeType="bool")
            cmds.setAttr("{0}.offs".format(ctrl), edit=True, keyable=True, channelBox=False)
            cmds.parent(old_ctrl, ctrl)
            mult = cmds.shadingNode("multiplyDivide", asUtility=True)
            cmds.connectAttr(
                "{0}.outputX".format(mult),
                "{0}.visibility".format(old_ctrl_shape)
            )
            cmds.connectAttr("{0}.offs".format(ctrl), "{0}.input1X".format(mult))
            if old_mult:
                cmds.connectAttr("{0}.outputX".format(mult), "{0}.input2X".format(old_mult))
            old_ctrl = ctrl
            old_ctrl_shape = ctrl_shape
            old_mult = mult
        cmds.group(name=ctrl_grp, empty=True)
        cmds.addAttr(
                ctrl, longName="joints",
                attributeType="enum",
                enumName="normal:off:reference"
        )
        cmds.setAttr(
                "{0}.joints".format(ctrl),
                edit=True,
                keyable=True,
                channelBox=True
        )
        cmds.setAttr("{0}.joints".format(ctrl), 2)
        cond = cmds.shadingNode("condition", asUtility=True)
        cmds.connectAttr("{0}.joints".format(ctrl), "{0}.firstTerm".format(cond))
        cmds.setAttr("{0}.secondTerm".format(cond), 1)
        cmds.parent(ctrl, ctrl_grp)
        cmds.parent(ctrl_grp, root)
    else:
        ctrl = cmds.listRelatives(ctrl_grp, children=True, type="transform",)[0]
        cond = cmds.listConnections(
                "{0}.joints".format(ctrl),
                destination=True,
                source=False,
                type="condition"
        )[0]
    if not cmds.ls(jnt_grp):
        cmds.group(name=jnt_grp, empty=True)
        cmds.parent(jnt_grp, root)
        cmds.setAttr("{0}.overrideEnabled".format(jnt_grp), 1)
    cmds.connectAttr(
            "{0}.outColorR".format(cond),
            "{0}.visibility".format(jnt_grp),
            force=True
    )
    cmds.connectAttr(
            "{0}.joints".format(ctrl),
            "{0}.overrideDisplayType".format(jnt_grp),
            force=True
    )


def generate(base=4):
    modules = list()
    generate_base(base)
    for mod in cmds.listRelatives("Foundation", children=True, type="transform"):
        module = Module(mod)
        modules.append(module)
        top_jnt = module.build_joints()
        cmds.parent(top_jnt, jnt_grp)
