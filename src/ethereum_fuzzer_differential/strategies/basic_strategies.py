"""
A mutator that adds a PUSH0/POP pair.
"""

import random
from argparse import ArgumentError
from typing import Any, Dict, Tuple

from ethereum_fuzzer_basicblocks.basicblocks import (
    BasicBlock,
    BasicBlockContainer,
    BasicBlockSection,
    CodePoint,
)
from ethereum_fuzzer_differential.mutator import EOFMutator, MutateError
from ethereum_test_tools import Opcodes as Op
from ethereum_test_vm.opcode import push_opcodes, valid_eof_opcodes_by_num


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


def optimize_push(code_point: CodePoint) -> CodePoint:
    """Ensures all push opcodes have enough size for the immediate they contain"""
    op_num = code_point.opcode.int()
    immediate_size = len(code_point.immediate)
    if immediate_size > 32:
        raise ArgumentError(None, "Push Immediate too large" + str(immediate_size))
    if Op.PUSH0.int() <= op_num <= Op.PUSH32.int():
        new_opcode_num = Op.PUSH0.int() + immediate_size
        new_opcode = valid_eof_opcodes_by_num[new_opcode_num]
        return code_point if new_opcode is None else CodePoint(new_opcode, code_point.immediate)
    return code_point


class PushPopMutation(EOFMutator):
    """Adds PUSH0/POP at some random point in a random section"""

    def __init__(self):
        super().__init__(1)

    def mutate(
        self, container: BasicBlockContainer, context: Dict[str, Any]
    ) -> Tuple[BasicBlockContainer, str]:
        """Adds PUSH0/POP at some random point in a random section"""
        section_idx, block_idx, pos = random_codepoint_index(container)
        section = container.code_sections[section_idx]
        block = section.blocks[block_idx]

        block.insert_code_point(pos, CodePoint(Op.POP))
        block.insert_code_point(pos, CodePoint(Op.PUSH0))

        return container, "Add PUSH0/POP section %d block %d pos %d" % (
            section_idx,
            block_idx,
            pos,
        )


class ReplacePushWithAddress(EOFMutator):
    """Adds PUSH0/POP at some random point in a random section"""

    def __init__(self):
        super().__init__(1)

    def mutate(
        self, container: BasicBlockContainer, context: Dict[str, Any]
    ) -> Tuple[BasicBlockContainer, str]:
        """Adds PUSH0/POP at some random point in a random section"""
        section_idx, block_idx, pos = find_random_opcode(container, push_opcodes)
        address = random.choice(context["addresses"])

        if section_idx == -1:
            raise MutateError("No section found")

        try:
            code_point = container.code_sections[section_idx].blocks[block_idx].code_points[pos]
            code_point.immediate = address

            container.code_sections[section_idx].blocks[block_idx].code_points[
                pos
            ] = optimize_push(code_point)
        except IndexError:
            print(section_idx, block_idx, pos)
            print(
                len(container.code_sections),
                len(container.code_sections[section_idx].blocks),
                len(container.code_sections[section_idx].blocks[block_idx].code_points),
            )

        return container, "set address section %d block %d pos %d" % (
            section_idx,
            block_idx,
            pos,
        )


default_strategies = [PushPopMutation, ReplacePushWithAddress]
