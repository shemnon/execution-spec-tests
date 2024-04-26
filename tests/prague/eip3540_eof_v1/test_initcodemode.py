"""
EOF Classes example use
"""
from typing import List, Tuple

import pytest

from ethereum_test_tools import EOFTestFiller
from ethereum_test_tools import Opcodes as Op
from ethereum_test_tools.eof.v1 import (
    AutoSection,
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

# def test_eof_example(eof_test: EOFTestFiller):
#     """
#     Example of python EOF classes
#     """
#     # Lets construct an EOF container code
#     eof_code = Container(
#         name="valid_container_example",
#         sections=[
#             # TYPES section is constructed automatically based on CODE
#             # CODE section
#             Section.Code(
#                 code=Op.CALLF[1](Op.PUSH0) + Op.STOP,  # bytecode to be deployed in the body
#                 # Code: call section 1 with a single zero as input, then stop.
#                 code_inputs=0,  # define code header (in body) input bytes
#                 code_outputs=NON_RETURNING_SECTION,  # define code header (in body) output bytes
#                 max_stack_height=1,  # define code header (in body) stack size
#             ),
#             # There can be multiple code sections
#             Section.Code(
#                 # Remove input and call section 2 with no inputs, then remove output and return
#                 code=Op.POP + Op.CALLF[2]() + Op.POP + Op.RETF,
#                 code_inputs=1,
#                 code_outputs=0,
#                 max_stack_height=1,
#             ),
#             Section.Code(
#                 # Call section 3 with two inputs (address twice), return
#                 code=Op.CALLF[3](Op.DUP1, Op.ADDRESS) + Op.POP + Op.POP + Op.RETF,
#                 code_inputs=0,
#                 code_outputs=1,
#                 max_stack_height=3,
#             ),
#             Section.Code(
#                 # Duplicate one input and return
#                 code=Op.DUP1 + Op.RETF,
#                 code_inputs=2,
#                 code_outputs=3,
#                 max_stack_height=3,
#             ),
#             # DATA section
#             Section.Data("0xef"),
#         ],
#     )
#
#     # This will construct a valid EOF container with these bytes
#     assert bytes(eof_code) == bytes.fromhex(
#         "ef0001010010020004000500060008000204000100008000010100000100010003020300035fe300010050"
#         "e3000250e43080e300035050e480e4ef"
#     )
#
#     eof_test(
#         data=eof_code,
#         expect_exception=eof_code.validity_error,
#     )
#
#
# def test_eof_example_custom_fields(eof_test: EOFTestFiller):
#     """
#     Example of python EOF container class tuning
#     """
#     # if you need to overwrite certain structure bytes, you can use customization
#     # this is useful for unit testing the eof structure format, you can reorganize sections
#     # and overwrite the header bytes for testing purposes
#     # most of the combinations are covered by the unit tests
#
#     # This features are subject for development and will change in the future
#
#     eof_code = Container(
#         name="valid_container_example_2",
#         magic=b"\xef\x00",  # magic can be overwritten for test purposes, (default is 0xEF00)
#         version=b"\x01",  # version can be overwritten for testing purposes (default is 0x01)
#         header_terminator=b"\x00",  # terminator byte can be overwritten (default is 0x00)
#         extra=b"",  # extra bytes to be trailed after the container body bytes (default is None)
#         sections=[
#             # TYPES section is constructed automatically based on CODE
#             # CODE section
#             Section.Code(
#                 code=Op.PUSH1(2)
#                      + Op.STOP,  # this is the actual bytecode to be deployed in the body
#                 code_inputs=0,  # define code header (in body) input bytes
#                 code_outputs=NON_RETURNING_SECTION,  # define code header (in body) output bytes
#                 max_stack_height=1,  # define code header (in body) stack size
#             ),
#             # DATA section
#             Section.Data(
#                 data="0xef",
#                 # custom_size overrides the size bytes, so you can put only 1 byte into data
#                 # but still make the header size of 2 to produce invalid section
#                 # if custom_size != len(data), the section will be invalid
#                 custom_size=1,
#             ),
#         ],
#         # auto generate types section based on provided code sections
#         # AutoSection.ONLY_BODY - means the section will be generated only for the body bytes
#         # AutoSection.ONLY_BODY - means the section will be generated only for the header bytes
#         auto_type_section=AutoSection.AUTO,
#         # auto generate default data section (0x empty), by default is True
#         auto_data_section=True,
#         # auto sort section by order 01 02 03 04
#         # AutoSection.ONLY_BODY - means the sorting will be done only for the body bytes
#         # AutoSection.ONLY_BODY - means the section will be done only for the header bytes
#         auto_sort_sections=AutoSection.AUTO,
#     )
#
#     eof_test(
#         data=eof_code,
#         expect_exception=eof_code.validity_error,
#     )
#

# @pytest.mark.parametrize(
#     "data_section_bytes",
#     ("0x01", "0xef"),
# )

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
def test_initcodemode(
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

    # runtime_subcontainer = Container(
    #     name="Runtime Subcontainer",
    #     sections=[
    #         Section.Code(
    #             code=Op.PUSH0 + Op.STOP,
    #             code_inputs=0,
    #             code_outputs=NON_RETURNING_SECTION,
    #             max_stack_height=0,
    #         )
    #     ],
    # )

    # initcode_subcontainer = Container(
    #     name="Initcode Subcontainer",
    #     sections=[
    #         Section.Code(
    #             code=Op.RETURNCONTRACT(0, 0, 0),
    #             code_inputs=0,
    #             code_outputs=NON_RETURNING_SECTION,
    #             max_stack_height=2,
    #         ),
    #         Section.Container(
    #             container=runtime_subcontainer
    #         )
    #     ]
    # )
    #
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
