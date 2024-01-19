from anytree import Node
from settings import MAXIMUM_RANDOM_DEPTH, MAXIMUM_PARENT_LIMIT

def limit_random_depth(node: Node):
    global MAXIMUM_RANDOM_DEPTH

    assert MAXIMUM_RANDOM_DEPTH > 0
    if node.parent and 'depth' in node.parent.name:
        parent_depth = node.parent.name['depth']
        assert parent_depth < MAXIMUM_RANDOM_DEPTH
        node.name['depth'] = parent_depth + 1
    else:
        node.name['depth'] = 1

def limit_depth(node: Node):
    global MAXIMUM_PARENT_LIMIT

    assert MAXIMUM_PARENT_LIMIT > 0
    parent_count = 0
    temp_node = node.parent
    while temp_node:
        temp_node = temp_node.parent
        parent_count += 1
        assert parent_count < MAXIMUM_PARENT_LIMIT