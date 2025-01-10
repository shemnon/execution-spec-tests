"""A mutator that adds a PUSH0/POP pair."""

import random
from typing import Any, Dict, Tuple

from ethereum_fuzzer_basicblocks.basicblocks import BasicBlock, BasicBlockContainer, CodePoint
from ethereum_fuzzer_differential.mutator import EOFMutator, MutateError
from ethereum_fuzzer_differential.strategies.helpers import random_codepoint_index
from ethereum_test_tools import Opcodes as Op
from ethereum_test_vm.opcode import push_opcodes, valid_eof_opcodes


def flatten_block(block: BasicBlock) -> BasicBlock:
    """Remove all adjacent POP/PUSH and PUSH/POP pairs."""
    flat_block = BasicBlock(block.label)
    flat_block.successors += block.successors
    flat_block.offset = block.offset
    # add a stub "NOOP" we will delete later, eliminates
    flat_block.append_code_point(CodePoint(Op.NOOP))
    # progressively add opcodes from old block
    for cp in block.code_points:
        opcode = cp.opcode
        if (opcode in push_opcodes and flat_block.code_points[-1].opcode == Op.POP) or (
            opcode == Op.POP and flat_block.code_points[-1].opcode in push_opcodes
        ):
            # if we have a PUSH/POP or POP/PUSH pair don't insert it and pop the last one
            flat_block.pop_code_point()
            # print("poof")
        else:
            # otherwise append it
            flat_block.code_points.append(cp)
    if len(flat_block.code_points) > 1:
        flat_block.remove_code_point(0)  # remove the temporary NOOP, unless it zeros out the block
    return block if len(flat_block.code_points) == len(block.code_points) else flat_block


class DeleteOpcodeBalanced(EOFMutator):
    """Delete an opcode, and add POPs/PUSH0 as needed to balance out."""

    def __init__(self, priority: int = 1):
        """Create the strategy with a default priority of 1."""
        super().__init__(priority)

    def mutate(
        self, container: BasicBlockContainer, context: Dict[str, Any]
    ) -> Tuple[BasicBlockContainer, str]:
        """Add a PUSH0/POP at some random point in a random section."""
        section_idx, block_idx, pos = random_codepoint_index(container)
        section = container.code_sections[section_idx]
        block = section.blocks[block_idx]

        code_point = block.remove_code_point(pos)
        if len(block.code_points) <= pos and code_point.opcode.terminating:
            # if code_point.opcode.terminating:
            raise MutateError("Removing terminal opcode at end of a basic block")

        net_stack = code_point.opcode.pushed_stack_items - code_point.opcode.popped_stack_items
        if net_stack > 0:
            for _ in range(net_stack):
                block.append_code_point(CodePoint(Op.PUSH0))
        elif net_stack < 0:
            for _ in range(-net_stack):
                block.append_code_point(CodePoint(Op.POP))

        if len(block.code_points) == 0:
            # needed until we get target merging logic
            block.code_points.append(CodePoint(Op.NOOP))

        # remove unneeded push/pop pairs
        section.blocks[block_idx] = flatten_block(block)

        return container, "balanced delete section %d block %d pos %d" % (
            section_idx,
            block_idx,
            pos,
        )


eof_insertion_opcodes = list(
    valid_eof_opcodes
    - {
        Op.BLOCKHASH,  # This is its own special hot mess, pre and post EIP-2935
        Op.STOP,
        Op.POP,
        Op.PUSH0,
        Op.PUSH1,
        Op.PUSH2,
        Op.PUSH3,
        Op.PUSH4,
        Op.PUSH5,
        Op.PUSH6,
        Op.PUSH7,
        Op.PUSH8,
        Op.PUSH9,
        Op.PUSH10,
        Op.PUSH11,
        Op.PUSH12,
        Op.PUSH13,
        Op.PUSH14,
        Op.PUSH15,
        Op.PUSH16,
        Op.PUSH17,
        Op.PUSH18,
        Op.PUSH19,
        Op.PUSH20,
        Op.PUSH21,
        Op.PUSH22,
        Op.PUSH23,
        Op.PUSH24,
        Op.PUSH25,
        Op.PUSH26,
        Op.PUSH27,
        Op.PUSH28,
        Op.PUSH29,
        Op.PUSH30,
        Op.PUSH31,
        Op.PUSH32,
        Op.DATALOAD,
        Op.DATALOADN,
        Op.DATASIZE,
        Op.DATACOPY,
        Op.RJUMP,
        Op.RJUMPI,
        Op.RJUMPV,
        Op.CALLF,
        Op.RETF,
        Op.JUMPF,
        Op.DUPN,
        Op.SWAPN,
        Op.EXCHANGE,
        Op.EOFCREATE,
        Op.RETURNCONTRACT,
        Op.RETURN,
        Op.EXTCALL,
        Op.EXTDELEGATECALL,
        Op.EXTSTATICCALL,
        Op.REVERT,
        Op.INVALID,
    }
)


class InsertSimpleOpcodeBalanced(EOFMutator):
    """Insert a simple opcode.  Pushing and popping as needed."""

    def __init__(self, priority: int = 1):
        """Create the strategy with a default priority of 1."""
        super().__init__(priority)

    def mutate(
        self, container: BasicBlockContainer, context: Dict[str, Any]
    ) -> Tuple[BasicBlockContainer, str]:
        """Insert a simple opcode, Pushing and popping as needed."""
        section_idx, block_idx, pos = random_codepoint_index(
            container, for_code_point_insertion=True
        )
        section = container.code_sections[section_idx]
        block = section.blocks[block_idx]

        opcode = random.choice(eof_insertion_opcodes)
        opcode_pushed = opcode.pushed_stack_items
        opcode_popped = opcode.popped_stack_items

        pre_cp = (
            block.code_points[pos - 1] if pos > 0 else CodePoint(Op.NOOP, stack_min=0, stack_max=0)
        )
        pre_height = (
            pre_cp.stack_min + pre_cp.opcode.pushed_stack_items - pre_cp.opcode.popped_stack_items
        )

        post_height = (
            block.code_points[pos].stack_min if pos < len(block.code_points) else pre_height
        )

        pre_push = max(
            0,
            max(opcode.min_stack_height, opcode_popped) - pre_height,
        )
        delta = post_height - pre_height - opcode_pushed + opcode_popped - pre_push

        # delta is the difference between what is produced by the pre-push and op execution
        # and what the next op had before.  Bring it back to expectation to make it "balanced"
        for _ in range(delta):
            block.code_points.insert(pos, CodePoint(Op.PUSH0))
        for _ in range(0, delta, -1):
            block.code_points.insert(pos, CodePoint(Op.POP))
        # The actual operation we are inserting
        # print(pre_height, "->", post_height, opcode)
        block.code_points.insert(pos, CodePoint(opcode))
        for _ in range(pre_push):
            # if we need a deeper stack that what is available (such as for PUSH15) we push it here
            block.code_points.insert(pos, CodePoint(Op.PUSH0))

        # remove unneeded push/pop pairs
        section.blocks[block_idx] = flatten_block(block)

        return container, "balanced simple insert section %d block %d pos %d" % (
            section_idx,
            block_idx,
            pos,
        )


# TODO DATALOAD opcodes
#  Determine the load scope
#  make sure mandatoy data is there (DATALOADN)
#  maybe add non-mandatory data

# TODO JUMP Opcodes ;P

# TODO code section delete/add/call/jump

# TODO DUPN/SWAPN/EXCHANGE (like insert balanced, but with immediate values)

# TODO contract calls

# TODO CREATE / RETURNCONTRACT :P

# TODO swap (no insert?) terminal opcodes (STOP, RETURN, REVERT, INVALID)

opcode_strategies = [
    InsertSimpleOpcodeBalanced,
    DeleteOpcodeBalanced,
]
