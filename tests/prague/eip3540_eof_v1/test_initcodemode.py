"""
EOF Classes example use
"""
from typing import List, Tuple

import pytest

from ethereum_test_tools import EOFTestFiller
from ethereum_test_tools import Opcodes as Op
from ethereum_test_tools.eof.v1 import (
    BytesConvertible,
    Container,
    EOFException,
    Section,
)
from ethereum_test_tools.eof.v1.constants import NON_RETURNING_SECTION

from .spec import EOF_FORK_NAME

REFERENCE_SPEC_GIT_PATH = "EIPS/eip-7420.md"
REFERENCE_SPEC_VERSION = "0000000000000000000000000000000000000000"

pytestmark = pytest.mark.valid_from(EOF_FORK_NAME)

test_cases = [
    ("top_initmode", [(Op.RETURNCONTRACT(1, 0, 0), 2)], None),
    ("top_runtime", [(Op.EOFCREATE(0, 0, 0, 0, 0) + Op.STOP, 4)], None),
    (
        "returncontract_wrong_container",
        [(Op.RETURNCONTRACT(0, 0, 0), 2)],
        EOFException.UNDEFINED_EXCEPTION,
    ),
    (
        "eofcreate_wrong_container",
        [(Op.EOFCREATE(1, 0, 0, 0, 0) + Op.STOP, 4)],
        EOFException.UNDEFINED_EXCEPTION,
    ),
    (
        "eofcreate_returncontract_mixed",
        [(Op.EOFCREATE(1, 0, 0, 0, 0) + Op.RETURNCONTRACT(0, 0, 0), 4)],
        EOFException.UNDEFINED_EXCEPTION,
    ),
    (
        "eofcreate_returncontract_mixed_sections",
        [(Op.EOFCREATE(1, 0, 0, 0, 0) + Op.STOP, 4), (Op.RETURNCONTRACT(0, 0, 0), 2)],
        EOFException.UNDEFINED_EXCEPTION,
    ),
]


@pytest.mark.parametrize(
    ["code_section_code", "exception"],
    [(x[1], x[2]) for x in test_cases],
    ids=[x[0] for x in test_cases],
)
def test_initcode_mode(
    eof_test: EOFTestFiller,
    code_section_code: List[Tuple[BytesConvertible, int]],
    exception: EOFException,
):
    """
    Validate initcode validation rules
    """
    runtime_subcontainer = Container(
        name="Runtime Subcontainer",
        sections=[
            Section.Code(
                code=Op.STOP,
                code_inputs=0,
                code_outputs=NON_RETURNING_SECTION,
                max_stack_height=0,
            )
        ],
    )

    initcode_subcontainer = Container(
        name="Initcode Subcontainer",
        sections=[
            Section.Code(
                code=Op.RETURNCONTRACT(0, 0, 0),
                code_inputs=0,
                code_outputs=NON_RETURNING_SECTION,
                max_stack_height=2,
            ),
            Section.Container(container=runtime_subcontainer),
        ],
    )

    eof_code = Container(
        name="initcode_validaiton",
        sections=[
            *[
                Section.Code(
                    code=c[0],
                    code_inputs=0,
                    code_outputs=NON_RETURNING_SECTION,
                    max_stack_height=c[1],
                )
                for c in code_section_code
            ],
            Section.Container(container=initcode_subcontainer),
            Section.Container(container=runtime_subcontainer),
        ],
        validity_error=exception,
    )

    eof_test(
        data=eof_code,
        expect_exception=eof_code.validity_error,
    )


def test_eof_invalid_subcontainer(
    eof_test: EOFTestFiller,
):
    """
    Validate initcode validation rules
    """
    eof_code = Container(
        name="initcode_validaiton",
        sections=[
            Section.Code(
                code=Op.RETURNCONTRACT(0, 0, 0),
                code_inputs=0,
                code_outputs=NON_RETURNING_SECTION,
                max_stack_height=2,
            ),
            Section.Container(
                container=Container(
                    name="Runtime Subcontainer",
                    sections=[
                        Section.Code(
                            code=Op.PUSH0 + Op.STOP,
                            code_inputs=0,
                            code_outputs=NON_RETURNING_SECTION,
                            max_stack_height=0,
                        )
                    ],
                )
            ),
        ],
        validity_error=EOFException.DEFAULT_EXCEPTION,
    )

    eof_test(
        data=eof_code,
        expect_exception=eof_code.validity_error,
    )
