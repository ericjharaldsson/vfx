import maya.cmds as cmds

def find_root(jnt, timeout=100):                                                      
     """                                                                                   
     Find top joint from anywhere in hierartchy                                            
     args:                                                                                 
         jnt str: name of a joint in a joint chain                                         
         timeout int: timeout before it gives up the search. default 100                   
     return:                                                                               
         top joint of the chain                                                            
     """                                                                                   
                                                                                           
     for i in range(timeout):                                                              
         parent_jnt = cmds.listRelatives(jnt, parent=True, type='joint')                   
         if parent_jnt:                                                                    
             jnt = parent_jnt[0]                                                           
         else:                                                                             
             return jnt 


def extend_joint_name(top_joint, extention, place="end"):
    """
    extend name of children of a copied joint
    @param topJoint: str, joint to get listed with its joint hierarchy
    @param extention: str, text that will be added to the prefix
    @param place: str, where to place the extention end (of suffix), beginning (of suffix)
    """
    joints = cmds.listRelatives(top_joint, type="joint", allDescendents=True)
    for jnt in joints:
        cmds.rename(joints[jnt], name.extend_name(extention, names[jnt]))


def shorten_joint_name(topJoint, extention):
    """
    delete part of names of joint chain
    @param topJoint: str, joint to get listed with its joint hierarchy
    @param extention: str, text that will be added to the prefix
    """
    joints = cmds.listRelatives(topJoint, type="joint", ad=1, f=1)
    names = cmds.listRelatives(
        topJoint,
        type="joint",
        ad=1,
    )
    for jnt in range(len(joints)):
        cmds.rename(joints[jnt], names[jnt].replace(extention, ""))


def joint_chain(startJnt, endJnt):
    """
    creates a list of the joint chain between two joints
    @param startJnt: str, the top joint of the list
    @param endJnt: str, the bottom joint of the list
    @return: str, list of joints between startJnt and endJnt
    """
    jnt = cmds.ls(endJnt, l=1)[0].split("|")
    return jnt[jnt.index(startJnt) :]
