"""
Helper functions for mutation stragegies
"""


import random
from typing import Tuple

from ethereum_fuzzer_basicblocks.basicblocks import (
    BasicBlock,
    BasicBlockContainer,
    BasicBlockSection,
    CodePoint,
)
from ethereum_test_tools import Opcodes as Op


def random_codepoint_index(container: BasicBlockContainer) -> Tuple[int, int, int]:
    """Returns a section/block/pos tuple of a randomish code point. Nota  perfect distribution."""
    section = random.randint(0, len(container.code_sections) - 1)
    block = random.randint(0, len(container.code_sections[section].blocks) - 1)
    pos = random.randint(0, len(container.code_sections[section].blocks[block].code_points) - 1)
    return section, block, pos


def find_random_opcode(container: BasicBlockContainer, opcodes: list[Op]) -> Tuple[int, int, int]:
    """Pick a section/block/pos tuple containing one of the set of opcodes, or -1/-1/-1"""
    # pick point
    section, block, pos = random_codepoint_index(container)
    current_section: BasicBlockSection = container.code_sections[section]
    current_block: BasicBlock = current_section.blocks[block]
    # first search from point to end of block
    for next_pos in range(pos, len(current_block.code_points)):
        current_point: CodePoint = current_block.code_points[next_pos]
        if current_point.opcode in opcodes:
            return section, block, next_pos
    #  next search following block to end of section
    for next_block in range(block + 1, len(current_section.blocks)):
        current_block = current_section.blocks[next_block]
        for next_pos in range(pos, len(current_block.code_points)):
            current_point = current_block.code_points[next_pos]
            if current_point.opcode in opcodes:
                return section, next_block, next_pos
    # next search following sections to end of container
    for next_section in range(section + 1, len(container.code_sections)):
        current_section = container.code_sections[next_section]
        for next_block in range(block + 1, len(current_section.blocks)):
            current_block = current_section.blocks[next_block]
            for next_pos in range(pos, len(current_block.code_points)):
                current_point = current_block.code_points[next_pos]
                if current_point.opcode in opcodes:
                    return next_section, next_block, next_pos
    # search from start to section we started at, inclusive.
    # there may be some overlap with initial search area, but that will only occur if we
    # fail to find, then we will just double search part of a section and fail to find.
    for next_section in range(0, section + 1):
        current_section = container.code_sections[next_section]
        for next_block in range(0, len(current_section.blocks)):
            current_block = current_section.blocks[next_block]
            for next_pos in range(0, len(current_block.code_points)):
                current_point = current_block.code_points[next_pos]
                if current_point.opcode in opcodes:
                    return next_section, next_block, next_pos
    # no matching codes
    return -1, -1, -1
