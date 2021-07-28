from maya import cmds
def lock_attributes(node, attrs):
    """
    function to lock a lit of attributes at the same time
    args:
        node str
        attrs list
    return: None
    """

    def lock(attr):
        cmds.setAttr(
            "{0}.{1}".format(node, attr),
            lock=True,
            keyable=False,
            channelBox=False
            )

    for attr in attrs:
        children = cmds.attributeQuery(attr, node=node, listChildren=True)
        if children:
            for child in children:
                lock(child)
        else:
                lock(attr)


def find_root_jnt(jnt, timeout=100):
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

