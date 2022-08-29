#!/usr/bin/env python3
import os.path
import os
import sys
import argparse
import time

from PIL import Image, ImageDraw

from map import Map
from blocks import build_block, build_full_block, build_sprite, build_billboard, alpha_over, build_full_transparent_block
from constants import *
from util import *
import node_definitions


class Mapper:
    def __init__(self, map):
        self.map = map
        self.cnt = 0
        self.available_tiles = set()
        self.set_up_images()

    def set_up_images(self):
        """Generate an image for each node and load the mask"""
        self.node_images = {}
        self.masks = {}
        textures = node_definitions.NODE_TEXTURES
        default_mask = Image.open("mask.png").convert("1")
        for node_name, (texture_top, texture_side, texture_bottom) in textures.items():
            top = Image.open(os.path.join("textures", texture_top)).convert("RGBA") if texture_top != "" else None
            side = Image.open(os.path.join("textures", texture_side)).convert("RGBA") if texture_side != "" else None
            bottom = Image.open(os.path.join("textures", texture_bottom)).convert("RGBA") if texture_bottom != "" else None
            # only bottom texture, means it is a flat block, like lily pads
            if bottom != None and top == None and side == None:
                self.node_images[str.encode(node_name, "ascii")] = build_full_block(None, None, None, None, None, bottom)
                self.masks[str.encode(node_name, "ascii")] = None
            # only side texture, means it is a sprite, like flowers
            elif side != None and top == None and bottom == None:
                self.node_images[str.encode(node_name, "ascii")] = build_sprite(side)
                self.masks[str.encode(node_name, "ascii")] = None
            # only top texture, means it is a billboard block, like reeds
            elif top != None and side == None and bottom == None:
                self.node_images[str.encode(node_name, "ascii")] = build_billboard(top)
                self.masks[str.encode(node_name, "ascii")] = None
            # all textures, means it is a full block but designed to be transparent, like water
            elif top != None and side != None and bottom != None:
                # leave out the back sides for now, to make it appear even more transparent
                self.node_images[str.encode(node_name, "ascii")] = build_full_transparent_block(top, None, None, side, side, bottom)
                self.masks[str.encode(node_name, "ascii")] = None
            # otherwise, build a regular block
            else:
                self.node_images[str.encode(node_name, "ascii")] = build_block(top, side)
                self.masks[str.encode(node_name, "ascii")] = None # or default_mask if you don't want to use alpha channel from the textures

    def drawNode(self, canvas, x, y, z, block, start, mask):
        """Draw the three sides of a single node"""
        if mask == None:
            mask = block
        #canvas.paste(
        alpha_over(
            canvas,
            block,
            (
                start[0] + NODE_SIZE // 2 * (z - x),
                start[1] + NODE_SIZE // 4 * (x + z - 2 * y),
            ),
            mask,
        )

    def drawBlock(self, canvas, bx, by, bz, start):
        return self.drawBlockAt(canvas, bx, by, bz, bx, by, bz, start, 3)

    def drawBlockAt(self, canvas, bx, by, bz, dx, dy, dz, start, orientation):
        """ returns max y of visible node """
        map_block = self.map.getBlock(bx, by, bz)
        maxy = -1
        for y in range(NODES_PER_BLOCK):
            for z in range(NODES_PER_BLOCK):
                for x in range(NODES_PER_BLOCK):
                    node_name = ""
                    if orientation == 1:
                        node_name = map_block.get((NODES_PER_BLOCK-x-1), y, (NODES_PER_BLOCK-z-1))
                    elif orientation == 2:
                        node_name = map_block.get(x, y, (NODES_PER_BLOCK-z-1))
                    elif orientation == 4:
                        node_name = map_block.get((NODES_PER_BLOCK-x-1), y, z)
                    else:
                        node_name = map_block.get(x, y, z)
                    if node_name in node_definitions.INVISIBLE_NODES:
                        continue
                    node_image = (
                        self.node_images[node_name]
                        if node_name in self.node_images
                        else self.node_images[b"UNKNOWN_NODE"]
                    )



                    if not (node_name in self.node_images):
                        print(node_name)
                    elif node_name == b"UNKNOWN_NODE":
                        print(node_name)



                    mask = (
                        self.masks[node_name]
                        if node_name in self.masks
                        else None
                    )
                    if orientation == 2 or orientation == 4:
                        self.drawNode(
                            canvas,
                            z + dx * NODES_PER_BLOCK,
                            y + dy * NODES_PER_BLOCK,
                            x + dz * NODES_PER_BLOCK,
                            node_image,
                            start,
                            mask
                        )
                    else:
                        self.drawNode(
                            canvas,
                            x + dx * NODES_PER_BLOCK,
                            y + dy * NODES_PER_BLOCK,
                            z + dz * NODES_PER_BLOCK,
                            node_image,
                            start,
                            mask
                        )
                    maxy = max(maxy, y + dy * NODES_PER_BLOCK)
        return maxy

    def makeChunk(self, cx, cz):
        maxy = -1
        canvas = Image.new("RGBA", (BLOCK_SIZE, CHUNK_HEIGHT))
        for by in range(-8, 8):
            maxy = max(
                maxy,
                self.drawBlock(
                    canvas,
                    cx,
                    by,
                    cz,
                    (
                        BLOCK_SIZE // 2 * (cx - cz + 1) - NODE_SIZE // 2,
                        BLOCK_SIZE // 4 * (BLOCKS_PER_CHUNK - cz - cx) - NODE_SIZE // 2,
                    ),
                ),
            )
        return canvas, maxy

    def fullMap(self):
         canvas = Image.new("RGBA", (5000, 5000))
         start = (3000, 3000)
         for y in range(-1, 10):
             print(y)
             for z in range(-5, 5):
                 for x in range(-5, 5):
                     self.drawBlock(canvas, x, y, z, start)
         canvas.save("map.png")

    # orientation can be 1-4
    def mapAtXYWorldPlot(self, xy_x, xy_y, orientation):
        print("mapping x=%d and y=%d" % (xy_x, xy_y))
        cx = xToBlockCoordinate(xy_x)
        cz = yToBlockCoordinate(xy_y)
        canvas = Image.new("RGBA", (5000, 5000))
        # center the image in the canvas (based on calculcations from makeChunk)
        start = ((2500 + (BLOCK_SIZE * 3)) + (BLOCK_SIZE // 2 * (cx - cz + 1) - NODE_SIZE // 2),
                 1000 + (BLOCK_SIZE // 4 * (BLOCKS_PER_CHUNK - cz - cx) - NODE_SIZE // 2))
        for y in range(-2, 10):
            print("Mapping y=%d" % y)
            for z in range(8):
                for x in range(8):
                    # rotate the map based on orientation
                    if orientation == 1:
                        self.drawBlockAt(canvas, cx+(7-x), y, cz-z, cx+x, y, cz-(7-z), start, orientation)
                    elif orientation == 2:
                        self.drawBlockAt(canvas, cx+z, y, cz-x, cx+x, y, cz-(7-z), start, orientation)
                    elif orientation == 3:
                        self.drawBlockAt(canvas, cx+x, y, cz-(7-z), cx+x, y, cz-(7-z), start, orientation)
                    else:
                        self.drawBlockAt(canvas, cx+(7-z), y, cz-(7-x), cx+x, y, cz-(7-z), start, orientation)        
        """ another way to write the code, kept here in case it helps with clarity
        for y in range(-2, 10):
            print("Mapping y=%d" % y)
            reverse_z = cz - 7
            xprime = cx + 7
            reverse_xprime = cx
            for z in range(cz, cz-8, -1):
                reverse_x = cx
                zprime = cz
                reverse_zprime = cz - 7
                for x in range(cx+7, cx-1, -1):
                    if orientation == 1:
                        self.drawBlockAt(canvas, x, y, z, reverse_x, y, reverse_z, start, orientation)
                    elif orientation == 2:
                        self.drawBlockAt(canvas, reverse_xprime, y, zprime, reverse_x, y, reverse_z, start, orientation)
                    elif orientation == 3:
                        self.drawBlockAt(canvas, reverse_x, y, reverse_z, reverse_x, y, reverse_z, start, orientation)
                    else:
                        self.drawBlockAt(canvas, xprime, y, reverse_zprime, reverse_x, y, reverse_z, start, orientation)
                    reverse_x = reverse_x + 1
                    zprime = zprime - 1
                    reverse_zprime = reverse_zprime + 1
                reverse_z = reverse_z + 1
                xprime = xprime - 1
                reverse_xprime = reverse_xprime + 1
        """
        canvas.save("mapxy-%d-%d-%d.png" % (xy_x, xy_y, orientation))

    def mapPieceCenteredAtBlock(self, cx, cz):
        canvas = Image.new("RGBA", (5000, 5000))
        # center the image in the canvas (based on calculcations from makeChunk)
        start = ((2500 - (BLOCK_SIZE // 2)) + (BLOCK_SIZE // 2 * (cx - cz + 1) - NODE_SIZE // 2),
                 1250 + (BLOCK_SIZE // 4 * (BLOCKS_PER_CHUNK - cz - cx) - NODE_SIZE // 2))
        for y in range(-3, 10):
            print("Mapping y=%d" % y)
            for z in range(cz-5, cz+5):
                for x in range(cx-5, cx+5):
                    self.drawBlock(canvas, x, y, z, start)
        canvas.save("mapPiece.png")

    def chunks3(self, canvas, x, z, step):
        maxy = -1
        chunk, y = self.makeChunk(x, z)
        maxy = max(maxy, y)
        canvas.paste(chunk, (0, step * BLOCK_SIZE // 2), chunk)
        del chunk
        chunk, y = self.makeChunk(x + 1, z)
        maxy = max(maxy, y)
        canvas.paste(
            chunk, (-BLOCK_SIZE // 2, step * BLOCK_SIZE // 2 + BLOCK_SIZE // 4), chunk
        )
        del chunk
        chunk, y = self.makeChunk(x, z + 1)
        maxy = max(maxy, y)
        canvas.paste(
            chunk, (BLOCK_SIZE // 2, step * BLOCK_SIZE // 2 + BLOCK_SIZE // 4), chunk
        )
        del chunk
        return maxy

    # row = x + z
    # col = z - x
    # x = (row - col) / 2
    # z = (row + col) / 2
    """
    def dummyMakeTile(row, col):
        x, z = gridToCoords(row, col)
        canvas = Image.new("RGBA", (BLOCK_SIZE, 18 * BLOCK_SIZE/2))
        for i in range(-16, 2):
            self.chunks3(canvas, x, z, 16 + i)
        tile = canvas.crop((0, 16 * BLOCK_SIZE/2, BLOCK_SIZE, 18 * BLOCK_SIZE/2))
        del canvas
        return tile
    """

    @staticmethod
    def saveTile(tile, row, col, zoom=5):
        path = os.path.join("data", str(zoom), str(row))
        if not os.path.exists(path):
            os.makedirs(path)
        tile.save(os.path.join(path, "%d.png" % col))

    # assume it's safe to start with (x, z)
    def stupidMakeTiles(self, x, z):
        # TODO:                                  v
        canvas = Image.new("RGBA", (BLOCK_SIZE, 100 * BLOCK_SIZE))
        step = 0
        last = 0
        while True:
            # print("tiling %d %d" % (x + step, z + step))
            row, col = coordsToGrid(x + step, z + step)
            y = self.chunks3(canvas, x + step, z + step, step)
            # canvas.save("step_{}.png".format(step))
            if row % 4 == 0:
                tile = canvas.crop((0, last, BLOCK_SIZE, last + BLOCK_SIZE))
                last += BLOCK_SIZE
                self.saveTile(tile, row // 4, col // 2)
                del tile
                self.cnt += 1
            self.available_tiles.add((x + step, z + step))
            step += 1
            # print("y is %d" % y)
            if y == -1:
                break

    def get_available_tiles(self):
        return self.available_tiles

    def get_cnt(self):
        return self.cnt


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--map_folder", help="Path to the folder with the map.sqlite file", default="."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    map = Map(args.map_folder)
    mapper = Mapper(map)
    
    # test just print out a sample map
    mapper.mapAtXYWorldPlot(106, 36, 1)
    mapper.mapAtXYWorldPlot(100, 35, 1)
    mapper.mapAtXYWorldPlot(70, 59, 1)
    mapper.mapAtXYWorldPlot(16, 10, 1)
    mapper.mapAtXYWorldPlot(24, 10, 1)
    mapper.mapAtXYWorldPlot(45, 5, 1)
    mapper.mapAtXYWorldPlot(104, 6, 1)
    mapper.mapAtXYWorldPlot(111, 17, 1)
    mapper.mapAtXYWorldPlot(122, 23, 1)
    mapper.mapAtXYWorldPlot(120, 25, 1)
    mapper.mapAtXYWorldPlot(114, 54, 1)
    mapper.mapAtXYWorldPlot(104, 46, 1)
    return;

    raw_coords = list(map.getCoordinatesToDraw())
    coords = []
    for row, col in raw_coords:
        if row % 4 != 0 or col % 2 != 0:
            continue
        coords.append(gridToCoords(row, col))
    coords.sort()

    time_last_message = time.perf_counter()
    last_available_tiles = set()
    for coord in coords:
        finished_tiles = mapper.get_available_tiles()
        if coord in finished_tiles:
            continue
        time_current = time.perf_counter()
        if time_current - time_last_message > 1.0:
            print(
                f"{100.0 * mapper.get_cnt() / len(coords):.2f}% done, added tiles: {finished_tiles - last_available_tiles}"
            )
            last_available_tiles = finished_tiles.copy()
            time_last_message = time_current
        mapper.stupidMakeTiles(*coord)

    """
    step = 0
    for row, col in coords:
        step += 1
        print("[{}%]".format(100.0 * step / len(coords)))
        if row % 4 != 0 or col % 2 != 0:
            continue
        path = os.path.join("data", "5", "{}".format(row / 4 ))
        if not os.path.exists(path):
            os.makedirs(path)
        dummyMakeTile(row, col).save(os.path.join(path, "{}.png".format(col / 2)))
    """

    # zoom 4 ---> 0

    to_join = raw_coords

    for zoom in range(4, -1, -1):
        new_join = set()
        for row, col in to_join:
            if zoom == 4:
                if row % 4 != 0 or col % 2 != 0:
                    continue
                row //= 4
                col //= 2
            if row % 2 == 1:
                row -= 1
            if col % 2 == 1:
                col -= 1
            new_join.add((row, col))
        to_join = new_join

        for row, col in to_join:
            # print("join {} {}".format(row, col))
            R = row // 2
            C = col // 2
            path = os.path.join("data", str(zoom), str(R))
            if not os.path.exists(path):
                os.makedirs(path)
            canvas = Image.new("RGBA", (BLOCK_SIZE, BLOCK_SIZE))
            for dx in range(0, 2):
                for dz in range(0, 2):
                    try:
                        tile = Image.open(
                            os.path.join(
                                "data",
                                str(zoom + 1),
                                str(row + dx),
                                "%d.png" % (col + dz),
                            )
                        ).convert("RGBA")
                    except IOError:
                        tile = Image.new("RGBA", (BLOCK_SIZE, BLOCK_SIZE))
                    tile = tile.resize((BLOCK_SIZE // 2, BLOCK_SIZE // 2))
                    canvas.paste(
                        tile, (dz * BLOCK_SIZE // 2, dx * BLOCK_SIZE // 2), tile
                    )
            canvas.save(os.path.join(path, "%d.png" % C))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
