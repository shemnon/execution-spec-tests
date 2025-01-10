"""Mutators for various targets.  The specific mutation strategies are in another file."""

import random
from abc import abstractmethod
from typing import Any, Dict, Generic, List, Tuple, TypeVar

from ethereum.exceptions import EthereumException
from ethereum.prague.vm.eof.validation import ContainerContext, validate_eof_container

from ethereum_fuzzer_basicblocks.basicblocks import BasicBlockContainer
from ethereum_test_base_types import Account, ZeroPaddedHexNumber
from ethereum_test_fixtures.file import StateFixtures
from ethereum_test_fixtures.state import Fixture as StateFixture
from ethereum_test_fixtures.state import FixtureTransaction

Mutatable = TypeVar("Mutatable", BasicBlockContainer, StateFixtures, Account)


class MutateError(Exception):
    """Expected error in mutation."""

    pass


class MutationStrategy(Generic[Mutatable]):
    """
    General class of a mutator.

    data is passed in, the same or new data is passed out, along with a description.
    """

    priority: int

    def __init__(self, priority: int) -> None:
        """Create the strategy."""
        self.priority = priority

    @abstractmethod
    def mutate(self, target: Mutatable, context: Dict[str, Any]) -> Tuple[Mutatable, str]:
        """
        Mutates the target. May return a new instance or the original value.
        Second return value is a string describing the mutation.

        """


class EOFMutator(MutationStrategy[BasicBlockContainer]):
    """Mutate an EOF contract."""

    def __init__(self, priority) -> None:
        """Create the strategy."""
        super().__init__(priority)

    @abstractmethod
    def mutate(
        self, target: BasicBlockContainer, context: Dict[str, Any]
    ) -> Tuple[BasicBlockContainer, str]:
        """Mutate the contract. Returns the same instance and the mutation."""


class AccountMutator(MutationStrategy[Account]):
    """Mutate an account holding an EOF contract."""

    def __init__(self, eof_mutation_strategies, priority: int = 1) -> None:
        """Create the strategy with a default priority of 1."""
        super().__init__(priority)
        for strategy in eof_mutation_strategies:
            self.add_strategy(strategy())

    eof_strategies: List[EOFMutator] = []
    priorities: List[int] = []
    total_priority: int = 0

    def mutate(self, account: Account, context: Dict[str, Any]) -> Tuple[Account, str]:
        """Return a new mutated instance of the account."""
        eof_mutator = random.choices(self.eof_strategies, weights=self.priorities, k=1)[0]
        container = BasicBlockContainer(account.code)
        new_container, mutation = eof_mutator.mutate(container, context)
        container.reconcile_bytecode()
        # We need the osaka version of ethereum-execution-specs to be imported
        code = container.encode()
        try:
            # We need the osaka version of ethereum-execution-specs to be imported
            validate_eof_container(code, ContainerContext.RUNTIME)
            return account.copy(code=container.encode()), mutation
        except EthereumException:
            return account, ""

    def add_strategy(self, mutator: EOFMutator):
        """Add a strategy to the list of mutation strategies."""
        self.eof_strategies.append(mutator)
        self.priorities.append(mutator.priority)
        self.total_priority += mutator.priority


class StateTestMutator(MutationStrategy[StateFixtures]):
    """Mutates a state test.  Currently, it only mutates EOF contracts."""

    contract_mutator: AccountMutator
    max_gas: int

    def __init__(self, max_gas: int, eof_mutation_strategies, priority: int = 1) -> None:
        """Create the strategy with a default priority of 1."""
        super().__init__(priority)
        self.max_gas = max_gas
        self.contract_mutator = AccountMutator(eof_mutation_strategies)

    def mutate(self, target: StateFixtures, context) -> Tuple[StateFixtures, str]:
        """
        For each account in the fixture, if it is an EOF contract mutate it.

        Only contract mutations are done, but there is a future where the rest of the state test
        may need to be mutated: inputs, memory, adding/deleting accounts, etc.
        """
        test = next(iter(target.items()))
        fixture = test[1]
        info = fixture.info
        pre = {}
        mutation_log = []
        tx: FixtureTransaction = fixture.transaction.copy(deep=True)
        for addr, acct in fixture.pre.root.items():
            if acct.code.startswith(b"\xef\0"):
                new_acct, mutation = self.contract_mutator.mutate(acct, context)
                pre[addr] = new_acct
                info["mutations"] += mutation + "\n"
                mutation_log.append("account %s" % addr)
            else:
                pre[addr] = acct
        tx.gas_limit = [
            ZeroPaddedHexNumber(min(gas_limit, self.max_gas)) for gas_limit in tx.gas_limit
        ]
        result = StateFixtures(
            root={
                test[0]: StateFixture(
                    info=info,
                    env=fixture.env,
                    pre=pre,
                    transaction=tx,
                    post=fixture.post,
                )
            }
        )
        return result, "\n".join(mutation_log)
