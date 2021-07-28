from maya import cmds
import json
import os


def skin_from_geo(geo):
    for node in cmds.listHistory(geo):
        if cmds.nodeType(node) == "skinCluster":
            return node
    return None


def skin_from_joint(jnt):
    skinclusters = list()
    for connection in cmds.listConnections(
        "{0}.worldMatrix".format(jnt), 
        destination=True
    ):
        if cmds.nodeType(connection) == "skinCluster":
            skinclusters.append(connection)
    return skinclusters


class SkinCluster:
    """
    wip
    """
    def __init__(self, skin_cluster):
        self.meshes = dict()
        self.skin = skin_cluster
        self.get_weights()
        self.get_joints()

        meshes = cmds.skinCluster(self.skin, geometry=True, query=True)
        for mesh in meshes:
            self.weights[mesh] = dict()
            for index in range(cmds.polyEvaluate(mesh, vertex=True)):
                vertex = "{0}.vtx[{1}]".format(mesh, index)
                percent = cmds.skinPercent(self.skin, vertex, value=True, query=True)
                joints = cmds.skinPercent(self.skin, vertex, transform=None, query=True)
                self.weights[mesh][index] = zip(joints, percent)

    def get_joints(self):
        self.joints = cmds.skinCluster(self.skin, influence=True, query=True)

    def set_weights(self):
        for mesh in self.weights:
            for index in shape:
                vertex = "{0}.vtx[{1}]".format(mesh, index)
                cmds.skinPercent(self.skin, vertex, transformvalue=shape[index])


    def save_to_file(self, url=None):
        self.get_weights()
        if not url:
            projectpath = cmds.workspace(query=True, rootDirectory=True)
            url = os.path.join(projectpath, "data", "{0}.json".format(self.skin))
        with open(url, "w") as f:
            json.dump(self.weights, f)
        print "{0} saved to {1}".format(self.skin, url)

    def load_from_file(self, url=None):
        if not url:
            projectpath = cmds.workspace(query=True, rootDirectory=True)
            url = os.path.join(projectpath, "data", "{0}.json".format(self.skin))
        with open(url, "r") as f:
            self.skin = json.load(f)


def lock_influences(joints):
    for jnt in joints:
        if cmds.nodeType(jnt) == "joint":
            cmds.setAttr("{0}.liw".format(jnt), True)


def unlock_influences(joints):
    for jnt in joints:
        if cmds.nodeType(jnt) == "joint":
            cmds.setAttr("{0}.liw".format(jnt), False)
