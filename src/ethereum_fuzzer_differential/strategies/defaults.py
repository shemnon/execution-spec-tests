"""
Collections of "default" strategies
"""

from typing import List, Type

from ethereum_fuzzer_differential.strategies.opcode_strategies import opcode_strategies
from ethereum_fuzzer_differential.strategies.push_strategies import push_strategies

default_strategies: List[Type] = [
    *push_strategies,
    *opcode_strategies,
]
