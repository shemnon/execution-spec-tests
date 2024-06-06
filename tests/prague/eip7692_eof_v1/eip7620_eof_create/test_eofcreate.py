"""
Test good and bad EOFCREATE cases
"""

import pytest

from ethereum_test_tools import (
    Account,
    Environment,
    StateTestFiller,
    TestAddress,
    compute_eofcreate_address,
)
from ethereum_test_tools.eof.v1 import Container, Section
from ethereum_test_tools.vm.opcode import Opcodes as Op

from .. import EOF_FORK_NAME
from .helpers import (
    default_address,
    fixed_address,
    simple_transaction,
    slot_call_result,
    slot_calldata,
    slot_code_worked,
    slot_create_address,
    slot_last_slot,
    slot_returndata_size,
    smallest_initcode_subcontainer,
    smallest_runtime_subcontainer,
    value_call_result_success,
    value_canary_to_be_overwritten,
    value_code_worked,
    value_create_failed,
)

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-7620.md"
REFERENCE_SPEC_VERSION = "52ddbcdddcf72dd72427c319f2beddeb468e1737"

pytestmark = pytest.mark.valid_from(EOF_FORK_NAME)


def test_simple_eofcreate(
    state_test: StateTestFiller,
):
    """
    Verifies a simple EOFCREATE case
    """
    env = Environment()
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(0, Op.EOFCREATE[0](0, 0, 0, 0)) + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=smallest_initcode_subcontainer),
                ],
                data=b"abcdef",
            ),
            storage={0: 0xB17D},  # a canary to be overwritten
        ),
    }
    # Storage in 0 should have the address,
    post = {
        default_address: Account(
            storage={
                0: compute_eofcreate_address(default_address, 0, smallest_initcode_subcontainer)
            }
        )
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


def test_eofcreate_then_call(
    state_test: StateTestFiller,
):
    """
    Verifies a simple EOFCREATE case, and then calls the deployed contract
    """
    env = Environment()
    callable_contract = Container(
        sections=[
            Section.Code(
                code=Op.SSTORE(slot_code_worked, value_code_worked) + Op.STOP,
                max_stack_height=2,
            ),
        ]
    )
    callable_contract_initcode = Container(
        sections=[
            Section.Code(
                code=Op.RETURNCONTRACT[0](0, 0),
                max_stack_height=2,
            ),
            Section.Container(container=callable_contract),
        ]
    )

    callable_address = compute_eofcreate_address(default_address, 0, callable_contract_initcode)
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                        + Op.EXTCALL(Op.SLOAD(slot_create_address), 0, 0, 0)
                        + Op.SSTORE(slot_code_worked, value_code_worked)
                        + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=callable_contract_initcode),
                ],
            )
        ),
    }
    # Storage in 0 should have the address,
    #
    post = {
        default_address: Account(
            storage={slot_create_address: callable_address, slot_code_worked: value_code_worked}
        ),
        callable_address: Account(storage={slot_code_worked: value_code_worked}),
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


@pytest.mark.parametrize(
    "auxdata_bytes",
    [
        pytest.param(b"", id="zero"),
        pytest.param(b"aabbcc", id="short"),
        pytest.param(b"aabbccddeef", id="one_byte_short"),
        pytest.param(b"aabbccddeeff", id="exact"),
        pytest.param(b"aabbccddeeffg", id="one_byte_long"),
        pytest.param(b"aabbccddeeffgghhii", id="extra"),
    ],
)
def test_auxdata_variations(state_test: StateTestFiller, auxdata_bytes: bytes):
    """
    Verifies that auxdata bytes are correctly handled in RETURNCONTRACT
    """
    env = Environment()
    auxdata_size = len(auxdata_bytes)
    pre_deploy_header_data_size = 18
    pre_deploy_data = b"AABBCC"
    deploy_success = len(auxdata_bytes) + len(pre_deploy_data) >= pre_deploy_header_data_size

    runtime_subcontainer = Container(
        name="Runtime Subcontainer with truncated data",
        sections=[
            Section.Code(code=Op.STOP),
            Section.Data(data=pre_deploy_data, custom_size=pre_deploy_header_data_size),
        ],
    )

    initcode_subcontainer = Container(
        name="Initcode Subcontainer",
        sections=[
            Section.Code(
                code=Op.MSTORE(0, Op.PUSH32(auxdata_bytes.ljust(32, b"\0")))
                + Op.RETURNCONTRACT[0](0, auxdata_size),
                max_stack_height=2,
            ),
            Section.Container(container=runtime_subcontainer),
        ],
    )

    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0)) + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=initcode_subcontainer),
                ]
            ),
            storage={slot_create_address: value_canary_to_be_overwritten},
        ),
    }

    # Storage in 0 should have the address,
    post = {
        default_address: Account(
            storage={
                slot_create_address: compute_eofcreate_address(
                    default_address, 0, initcode_subcontainer
                )
                if deploy_success
                else b"\0"
            }
        )
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


def test_calldata(state_test: StateTestFiller):
    """
    Verifies CALLDATA passing through EOFCREATE
    """
    env = Environment()

    initcode_subcontainer = Container(
        name="Initcode Subcontainer",
        sections=[
            Section.Code(
                code=Op.CALLDATACOPY(0, 0, Op.CALLDATASIZE)
                + Op.SSTORE(slot_calldata, Op.MLOAD(0))
                + Op.RETURNCONTRACT[0](0, Op.CALLDATASIZE),
                max_stack_height=3,
            ),
            Section.Container(container=smallest_runtime_subcontainer),
        ],
    )

    calldata_size = 32
    calldata = b"\x45" * calldata_size
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.MSTORE(0, Op.PUSH32(calldata))
                        + Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, calldata_size))
                        + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=initcode_subcontainer),
                ]
            )
        ),
    }

    # deployed contract is smallest plus data
    deployed_contract = Container(
        name="deployed contract",
        sections=[
            *smallest_runtime_subcontainer.sections,
            Section.Data(data=calldata),
        ],
    )
    # factory contract Storage in 0 should have the created address,
    # created contract storage in 0 should have the calldata
    created_address = compute_eofcreate_address(default_address, 0, initcode_subcontainer)
    post = {
        default_address: Account(storage={slot_create_address: created_address}),
        created_address: Account(code=deployed_contract, storage={slot_calldata: calldata}),
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


def test_eofcreate_in_initcode(
    state_test: StateTestFiller,
):
    """
    Verifies an EOFCREATE occuring within initcode creates that contract
    """
    nested_initcode_subcontainer = Container(
        sections=[
            Section.Code(
                code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                + Op.SSTORE(slot_code_worked, value_code_worked)
                + Op.RETURNCONTRACT[1](0, 0),
                max_stack_height=4,
            ),
            Section.Container(container=smallest_initcode_subcontainer),
            Section.Container(container=smallest_runtime_subcontainer),
        ]
    )

    env = Environment()
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                        + Op.SSTORE(slot_code_worked, value_code_worked)
                        + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=nested_initcode_subcontainer),
                ]
            )
        ),
    }

    outer_address = compute_eofcreate_address(default_address, 0, nested_initcode_subcontainer)
    inner_address = compute_eofcreate_address(outer_address, 0, smallest_initcode_subcontainer)
    post = {
        default_address: Account(
            storage={slot_create_address: outer_address, slot_code_worked: value_code_worked}
        ),
        outer_address: Account(
            storage={slot_create_address: inner_address, slot_code_worked: value_code_worked}
        ),
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


def test_eofcreate_in_initcode_reverts(
    state_test: StateTestFiller,
):
    """
    Verifies an EOFCREATE occuring in an initcode is rolled back when the initcode reverts
    """
    nested_initcode_subcontainer = Container(
        sections=[
            Section.Code(
                code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                + Op.SSTORE(slot_code_worked, value_code_worked)
                + Op.REVERT(0, 0),
                max_stack_height=4,
            ),
            Section.Container(container=smallest_initcode_subcontainer),
            Section.Container(container=smallest_runtime_subcontainer),
        ]
    )

    env = Environment()
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                        + Op.SSTORE(slot_code_worked, value_code_worked)
                        + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=nested_initcode_subcontainer),
                ]
            ),
            storage={slot_create_address: value_canary_to_be_overwritten},
        ),
    }

    outer_address = compute_eofcreate_address(default_address, 0, nested_initcode_subcontainer)
    inner_address = compute_eofcreate_address(outer_address, 0, smallest_initcode_subcontainer)
    post = {
        default_address: Account(
            storage={
                slot_create_address: 0,
                slot_code_worked: value_code_worked,
            }
        ),
        outer_address: Account.NONEXISTENT,
        inner_address: Account.NONEXISTENT,
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


def test_return_data_cleared(
    state_test: StateTestFiller,
):
    """
    Verifies the return data is not re-used from a extcall but is cleared upon eofcreate
    """
    env = Environment()
    callable_address = fixed_address(1)
    value_return_canary = 0x4158675309
    value_return_canary_size = 5
    callable_contract = Container(
        sections=[
            Section.Code(
                code=Op.MSTORE(0, value_return_canary) + Op.RETURN(0, value_return_canary_size),
                max_stack_height=2,
            )
        ]
    )

    slot_returndata_size_2 = slot_last_slot * 2 + slot_returndata_size
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(slot_call_result, Op.EXTCALL(callable_address, 0, 0, 0))
                        + Op.SSTORE(slot_returndata_size, Op.RETURNDATASIZE)
                        + Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                        + Op.SSTORE(slot_returndata_size_2, Op.RETURNDATASIZE)
                        + Op.SSTORE(slot_code_worked, value_code_worked)
                        + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=smallest_initcode_subcontainer),
                ],
            )
        ),
        callable_address: Account(code=callable_contract, nonce=1),
    }

    new_contract_address = compute_eofcreate_address(
        default_address, 0, smallest_initcode_subcontainer
    )
    post = {
        default_address: Account(
            storage={
                slot_call_result: value_call_result_success,
                slot_returndata_size: value_return_canary_size,
                slot_create_address: new_contract_address,
                slot_returndata_size_2: 0,
                slot_code_worked: value_code_worked,
            },
            nonce=1,
        ),
        callable_address: Account(nonce=1),
        new_contract_address: Account(nonce=1),
    }

    state_test(env=env, pre=pre, post=post, tx=simple_transaction())


def test_address_collision(
    state_test: StateTestFiller,
):
    """
    Verifies a simple EOFCREATE case
    """
    env = Environment()

    salt_zero_address = compute_eofcreate_address(
        default_address, 0, smallest_initcode_subcontainer
    )
    salt_one_address = compute_eofcreate_address(
        default_address, 1, smallest_initcode_subcontainer
    )

    slot_create_address_2 = slot_last_slot * 2 + slot_create_address
    slot_create_address_3 = slot_last_slot * 3 + slot_create_address
    pre = {
        TestAddress: Account(balance=10**21, nonce=1),
        default_address: Account(
            code=Container(
                sections=[
                    Section.Code(
                        code=Op.SSTORE(slot_create_address, Op.EOFCREATE[0](0, 0, 0, 0))
                        + Op.SSTORE(slot_create_address_2, Op.EOFCREATE[0](0, 0, 0, 0))
                        + Op.SSTORE(slot_create_address_3, Op.EOFCREATE[0](0, 1, 0, 0))
                        + Op.SSTORE(slot_code_worked, value_code_worked)
                        + Op.STOP,
                        max_stack_height=4,
                    ),
                    Section.Container(container=smallest_initcode_subcontainer),
                ],
            )
        ),
        salt_one_address: Account(balance=1, nonce=1),
    }
    post = {
        default_address: Account(
            storage={
                slot_create_address: salt_zero_address,
                slot_create_address_2: value_create_failed,  # had an in-transaction collision
                slot_create_address_3: value_create_failed,  # had a pre-existing collision
                slot_code_worked: value_code_worked,
            }
        )
    }

    # Multiple create fails is expensive, use an absurd amount of gas
    state_test(env=env, pre=pre, post=post, tx=simple_transaction(gas_limit=300_000_000_000))
