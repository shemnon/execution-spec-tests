"""
Mutators for various targets.  The specific mutation strategies are in another file.
"""
import random
from abc import abstractmethod
from typing import Any, Dict, Generic, List, Tuple, TypeVar

from ethereum.prague.vm.eof.validation import ContainerContext, validate_eof_container

from ethereum_fuzzer_basicblocks.basicblocks import BasicBlockContainer
from ethereum_test_base_types import Account
from ethereum_test_fixtures.file import StateFixtures
from ethereum_test_fixtures.state import Fixture as StateFixture

Mutatable = TypeVar("Mutatable", BasicBlockContainer, StateFixtures, Account)


class MutateError(Exception):
    """Expected error in mutation"""

    pass


class MutationStrategy(Generic[Mutatable]):
    """
    General class of a mutator.

    data is passed in, the same or new data is passed out, along with a description.
    """

    priority: int

    def __init__(self, priority: int) -> None:
        self.priority = priority

    @abstractmethod
    def mutate(self, target: Mutatable, context: Dict[str, Any]) -> Tuple[Mutatable, str]:
        """
        Mutates the target. May return a new instance or the original value.
        Second return value is a string describing the mutation.

        """


class EOFMutator(MutationStrategy[BasicBlockContainer]):
    """Mutates an EOF contract."""

    def __init__(self, priority) -> None:
        super().__init__(priority)

    @abstractmethod
    def mutate(
        self, target: BasicBlockContainer, context: Dict[str, Any]
    ) -> Tuple[BasicBlockContainer, str]:
        """Mutates the contract. Returns the same instance and the mutation."""


class AccountMutator(MutationStrategy[Account]):
    """Mutates an account holding an EOF contract."""

    def __init__(self, eof_mutation_strategies) -> None:
        super().__init__(1)
        for strategy in eof_mutation_strategies:
            self.add_strategy(strategy())

    eof_strategies: List[EOFMutator] = []
    priorities: List[int] = []
    total_priority: int = 0

    def mutate(self, account: Account, context: Dict[str, Any]) -> Tuple[Account, str]:
        """Returns a new mutated instance of the account."""
        eof_mutator = random.choices(self.eof_strategies, weights=self.priorities, k=1)[0]
        container = BasicBlockContainer(account.code)
        new_container, mutation = eof_mutator.mutate(container, context)
        container.reconcile_bytecode()
        code = container.encode()
        try:
            validate_eof_container(code, ContainerContext.RUNTIME)
            return account.copy(code=container.encode()), mutation
        except ValueError:
            return account, ""

    def add_strategy(self, mutator: EOFMutator):
        """Adds a strategy to the list of mutation strategies."""
        self.eof_strategies.append(mutator)
        self.priorities.append(mutator.priority)
        self.total_priority += mutator.priority


class StateTestMutator(MutationStrategy[StateFixtures]):
    """Mutates a state test.  Currently it only mutates EOF contracts"""

    contract_mutator: AccountMutator

    def __init__(self, eof_mutation_strategies) -> None:
        super().__init__(1)
        self.contract_mutator = AccountMutator(eof_mutation_strategies)

    def mutate(self, target: StateFixtures, context) -> Tuple[StateFixtures, str]:
        """
        For each account in the fixture, if it is an EOF contract ,utate it

        Only contract mutations are done, but there is a future where the rest of the state test
        may need to be mutated: inputs, memory, adding/deleting accounts, etc.
        """
        test = next(iter(target.items()))
        fixture = test[1]
        info = fixture.info
        pre = {}
        mutation_log = []
        for (addr, acct) in fixture.pre.root.items():
            if acct.code.startswith(b"\xef\0"):
                new_acct, mutation = self.contract_mutator.mutate(acct, context)
                pre[addr] = new_acct
                info["mutations"] += mutation + "\n"
                mutation_log.append("account %s" % addr)
            else:
                pre[addr] = acct
        result = StateFixtures(
            root={
                test[0]: StateFixture(
                    info=info,
                    env=fixture.env,
                    pre=pre,
                    transaction=fixture.transaction,
                    post=fixture.post,
                )
            }
        )
        return result, "\n".join(mutation_log)
