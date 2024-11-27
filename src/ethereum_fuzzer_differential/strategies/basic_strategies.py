"""
A mutator that adds a PUSH0/POP pair.
"""

import random
from typing import Tuple

from ethereum_fuzzer_basicblocks.basicblocks import BasicBlockContainer, CodePoint
from ethereum_fuzzer_differential.mutator import EOFMutator
from ethereum_test_tools import Opcodes as Op


class PushPopMutation(EOFMutator):
    """Adds PUSH0/POP at some random point in a random section"""

    def __init__(self):
        super().__init__(1)

    def mutate(self, container: BasicBlockContainer) -> Tuple[BasicBlockContainer, str]:
        """Adds PUSH0/POP at some random point in a random section"""
        section = random.choice(container.code_sections)
        block = random.choice(section.blocks)
        pos = random.randint(0, block.opcode_count() - 1)

        block.insert_code_point(pos, CodePoint(Op.POP))
        block.insert_code_point(pos, CodePoint(Op.PUSH0))

        return container, "Add PUSH0/POP pos %d" % (pos)


default_strategies = [PushPopMutation]
