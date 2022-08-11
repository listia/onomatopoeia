#   Y
#   |
#   |
#   |
#   /\
#  /  \
# /    \
#X      Z


NODE_SIZE = 24
NODES_PER_BLOCK = 16
BLOCK_SIZE = 16 * NODE_SIZE
CHUNK_HEIGHT = 16 * BLOCK_SIZE//2 + BLOCK_SIZE//2
BLOCKS_PER_CHUNK = 16

# XY Project specific stuff - move later
MAX_XY_WORLD_SIZE = 8192
MAX_XY_SIZE = 128
NODES_PER_XY = 128

# East is positive
def xToBlockCoordinate(coord):
    return ((coord * NODES_PER_XY) - MAX_XY_WORLD_SIZE + (NODES_PER_BLOCK // 2)) // NODES_PER_BLOCK

# North is positive
def yToBlockCoordinate(coord):
    #the imported world is a bit off from the base coordinates (by approx 4y)
    return (MAX_XY_WORLD_SIZE - (coord * NODES_PER_XY) + (4 * NODES_PER_XY - 1) - (NODES_PER_BLOCK // 2)) // NODES_PER_BLOCK
