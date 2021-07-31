from maya import cmds
import json
from rig_tools.autorig import foundation
reload(foundation)
"""
shape_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "shapes.json"
    )
 """
shape_file = "/mnt/shared/vfx/pipe/rig_tools/autorig/shapes.json"
with open(shape_file) as f:
    shapes = json.load(f)
cmds.setAttr("Foundation.visibility", False)
offsets = 4
root = cmds.group(name="Rig", empty=True)
old_mult = None
for ofs in range(offsets, 0, -1):
    ctrl = cmds.curve(name="World{0}".format(ofs), d=1, p=shapes["base"][ofs])
    cmds.setAttr("{0}.visibility".format(ctrl), lock=True, keyable=False, channelBox=False) 
    ctrl_shape = cmds.listRelatives(ctrl, children=True)[0] 
    if ofs == offsets:
        old_ctrl = ctrl
        old_ctrl_shape = ctrl_shape
        cmds.parent(ctrl, root)
        continue
    cmds.addAttr(ctrl, longName="offs", attributeType="bool")
    cmds.setAttr("{0}.offs".format(ctrl), edit=True, keyable=True, channelBox=True)
    cmds.parent(ctrl, old_ctrl)
    mult = cmds.shadingNode("multiplyDivide", asUtility=True)
    cmds.connectAttr("{0}.outputX".format(mult), "{0}.visibility".format(old_ctrl_shape))
    cmds.connectAttr("{0}.offs".format(ctrl), "{0}.input1X".format(mult))
    if old_mult:
        cmds.connectAttr("{0}.outputX".format(mult), "{0}.input2X".format(old_mult))
    old_ctrl = ctrl
    old_ctrl_shape = ctrl_shape
    old_mult = mult
cmds.group(name="Skeleton", empty=True)                                                        
cmds.parent("Skeleton", "Rig")
cmds.addAttr("World1", longName="joints", attributeType="enum", enumName="normal:off:reference")
cmds.setAttr("World1.joints", edit=True, keyable=True, channelBox=True)
cmds.setAttr("World1.joints", 2)
cmds.setAttr("Skeleton.overrideEnabled", 1)
cmds.connectAttr("World1.joints", "Skeleton.overrideDisplayType")
cond = cmds.shadingNode("condition", asUtility=True)
cmds.connectAttr("World1.joints", "{0}.firstTerm".format(cond))
cmds.connectAttr("{0}.outColorR".format(cond), "Skeleton.visibility")
cmds.setAttr("{0}.secondTerm".format(cond), 1)

cmds.group(name="Ctrl", empty=True)
cmds.parent("Ctrl", "World1")


reload(foundation)
modules = list()
for module in cmds.listRelatives("Foundation", children=True, type="transform"):
    module_data = foundation.Module(module)
    mod_parent = module_data.parent
    if mod_parent:
        parent_module = cmds.listRelatives(mod_parent, parent=True)[0]
        mod_parent = "{0}_{1}".format(parent_module, mod_parent.split("|")[-1])
        
    else:
        mod_parent = "Skeleton"
        print mod_parent
    print
    joints = list()
    for jnt in cmds.listRelatives("Foundation|{0}".format(module), children=True, type="transform"):
        jnt_data = foundation.Joint(module_data, jnt)
        jnt_pos = jnt_data.world_transkate
        joint_orient = jnt_data.world_rotate
        jnt_parent = jnt_data.parent
        cmds.select(clear=True)
        jnt = cmds.joint(name="{0}_{1}".format(module, jnt), position=jnt_pos)
        cmds.setAttr("{0}.jointOrient".format(jnt), *joint_orient)
        if jnt_parent:
            joints.append([jnt, "{0}_{1}".format(module, jnt_parent.split("|")[-1])])
        else:
            modules.append([jnt, mod_parent])
            
    for jnt in joints:
        cmds.parent(*jnt)
for mod in modules:
    cmds.parent(*mod)
