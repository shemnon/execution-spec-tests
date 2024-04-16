"""
abstract: Tests BLS12_G2MUL precompile of [EIP-2537: Precompile for BLS12-381 curve operations](https://eips.ethereum.org/EIPS/eip-2537)
    Tests BLS12_G2MUL precompile of [EIP-2537: Precompile for BLS12-381 curve operations](https://eips.ethereum.org/EIPS/eip-2537).
"""  # noqa: E501

import pytest

from ethereum_test_tools import Environment
from ethereum_test_tools import Opcodes as Op
from ethereum_test_tools import StateTestFiller, Transaction

from .helpers import vectors_from_file
from .spec import FORK, PointG2, Scalar, Spec, ref_spec_2537

REFERENCE_SPEC_GIT_PATH = ref_spec_2537.git_path
REFERENCE_SPEC_VERSION = ref_spec_2537.version

pytestmark = [
    pytest.mark.valid_from(str(FORK)),
    pytest.mark.parametrize("precompile_address", [Spec.G2MUL], ids=[""]),
]


@pytest.mark.parametrize(
    "input,expected_output",
    vectors_from_file("mul_G2_bls.json")
    + [
        pytest.param(
            Spec.INF_G2 + Scalar(0),
            Spec.INF_G2,
            id="bls_g2mul_(0*inf=inf)",
        ),
        pytest.param(
            Spec.INF_G2 + Scalar(2**256 - 1),
            Spec.INF_G2,
            id="bls_g2mul_(2**256-1*inf=inf)",
        ),
        pytest.param(
            Spec.P2 + Scalar(2**256 - 1),
            PointG2(
                (
                    0x2663E1C3431E174CA80E5A84489569462E13B52DA27E7720AF5567941603475F1F9BC0102E13B92A0A21D96B94E9B22,  # noqa: E501
                    0x6A80D056486365020A6B53E2680B2D72D8A93561FC2F72B960936BB16F509C1A39C4E4174A7C9219E3D7EF130317C05,  # noqa: E501
                ),
                (
                    0xC49EAD39E9EB7E36E8BC25824299661D5B6D0E200BBC527ECCB946134726BF5DBD861E8E6EC946260B82ED26AFE15FB,  # noqa: E501
                    0x5397DAD1357CF8333189821B737172B18099ECF7EE8BDB4B3F05EBCCDF40E1782A6C71436D5ACE0843D7F361CBC6DB2,  # noqa: E501
                ),
            ),
            id="bls_g2mul_(2**256-1*P2)",
        ),
        pytest.param(
            Spec.P2 + Scalar(Spec.Q - 1),
            -Spec.P2,  # negated P2
            id="bls_g2mul_(q-1*P2)",
        ),
        pytest.param(
            Spec.P2 + Scalar(Spec.Q),
            Spec.INF_G2,
            id="bls_g2mul_(q*P2)",
        ),
        pytest.param(
            Spec.G2 + Scalar(Spec.Q),
            Spec.INF_G2,
            id="bls_g2mul_(q*G2)",
        ),
        pytest.param(
            Spec.P2 + Scalar(Spec.Q + 1),
            Spec.P2,
            id="bls_g2mul_(q+1*P2)",
        ),
        pytest.param(
            Spec.P2 + Scalar(2 * Spec.Q),
            Spec.INF_G2,
            id="bls_g2mul_(2q*P2)",
        ),
        pytest.param(
            Spec.P2 + Scalar((2**256 // Spec.Q) * Spec.Q),
            Spec.INF_G2,
            id="bls_g2mul_(Nq*P2)",
        ),
        pytest.param(
            PointG2(
                (1, 1),
                (
                    0x17FAA6201231304F270B858DAD9462089F2A5B83388E4B10773ABC1EEF6D193B9FCE4E8EA2D9D28E3C3A315AA7DE14CA,  # noqa: E501
                    0xCC12449BE6AC4E7F367E7242250427C4FB4C39325D3164AD397C1837A90F0EA1A534757DF374DD6569345EB41ED76E,  # noqa: E501
                ),
            )
            + Scalar(1),
            PointG2(
                (1, 1),
                (
                    0x17FAA6201231304F270B858DAD9462089F2A5B83388E4B10773ABC1EEF6D193B9FCE4E8EA2D9D28E3C3A315AA7DE14CA,  # noqa: E501
                    0xCC12449BE6AC4E7F367E7242250427C4FB4C39325D3164AD397C1837A90F0EA1A534757DF374DD6569345EB41ED76E,  # noqa: E501
                ),
            ),
            id="bls_g2mul_not_in_subgroup",
        ),
        pytest.param(
            PointG2(
                (1, 1),
                (
                    0x17FAA6201231304F270B858DAD9462089F2A5B83388E4B10773ABC1EEF6D193B9FCE4E8EA2D9D28E3C3A315AA7DE14CA,  # noqa: E501
                    0xCC12449BE6AC4E7F367E7242250427C4FB4C39325D3164AD397C1837A90F0EA1A534757DF374DD6569345EB41ED76E,  # noqa: E501
                ),
            )
            + Scalar(2),
            PointG2(
                (
                    0x919F97860ECC3E933E3477FCAC0E2E4FCC35A6E886E935C97511685232456263DEF6665F143CCCCB44C733333331553,  # noqa: E501
                    0x18B4376B50398178FA8D78ED2654B0FFD2A487BE4DBE6B69086E61B283F4E9D58389CCCB8EDC99995718A66666661555,  # noqa: E501
                ),
                (
                    0x26898F699C4B07A405AB4183A10B47F923D1C0FDA1018682DD2CCC88968C1B90D44534D6B9270CF57F8DC6D4891678A,  # noqa: E501
                    0x3270414330EAD5EC92219A03A24DFA059DBCBE610868BE1851CC13DAC447F60B40D41113FD007D3307B19ADD4B0F061,  # noqa: E501
                ),
            ),
            id="bls_g2mul_not_in_subgroup_times_2",
        ),
        pytest.param(
            PointG2(
                (1, 1),
                (
                    0x17FAA6201231304F270B858DAD9462089F2A5B83388E4B10773ABC1EEF6D193B9FCE4E8EA2D9D28E3C3A315AA7DE14CA,  # noqa: E501
                    0xCC12449BE6AC4E7F367E7242250427C4FB4C39325D3164AD397C1837A90F0EA1A534757DF374DD6569345EB41ED76E,  # noqa: E501
                ),
            )
            + Scalar(Spec.Q),
            PointG2(
                (
                    0x1C3ABBB8255E4DE6225C5A5710816BB5767D9B3188472867BB5D09144DFACC2E192C24E58C70BDBAC987BE8F61F15F8,  # noqa: E501
                    0x589CCBFA3E0C6D625634EA3849EFD0FA7E0119F9212000B76B36F7FEEB588AD22082825973F083B86D13A518445B7D7,  # noqa: E501
                ),
                (
                    0x129F217E324727C793050627706BAA9780D222AB9F341CB5E4A37F760F50BD735C5B88EF152C2DB753697DE223B2F6DB,  # noqa: E501
                    0x15CE502692A7B6AEA9DEA60BB0A6EECE5215228A10229FAAB4AD082CA802E8BE46745ED2D7192C15C776718A631EA0F3,  # noqa: E501
                ),
            ),
            id="bls_g2mul_not_in_subgroup_times_q",
        ),
    ],
)
def test_valid(
    state_test: StateTestFiller,
    pre: dict,
    post: dict,
    tx: Transaction,
):
    """
    Test the BLS12_G2MUL precompile.
    """
    state_test(
        env=Environment(),
        pre=pre,
        tx=tx,
        post=post,
    )


@pytest.mark.parametrize(
    "input",
    [
        pytest.param(
            PointG2((1, 0), (0, 0)) + Scalar(0),
            id="invalid_point_a_1",
        ),
        pytest.param(
            PointG2((0, 1), (0, 0)) + Scalar(0),
            id="invalid_point_a_2",
        ),
        pytest.param(
            PointG2((0, 0), (1, 0)) + Scalar(0),
            id="invalid_point_a_3",
        ),
        pytest.param(
            PointG2((0, 0), (0, 1)) + Scalar(0),
            id="invalid_point_a_4",
        ),
        pytest.param(
            PointG2((Spec.P, 0), (0, 0)) + Scalar(0),
            id="x_1_equal_to_p",
        ),
        pytest.param(
            PointG2((0, Spec.P), (0, 0)) + Scalar(0),
            id="x_2_equal_to_p",
        ),
        pytest.param(
            PointG2((0, 0), (Spec.P, 0)) + Scalar(0),
            id="y_1_equal_to_p",
        ),
        pytest.param(
            PointG2((0, 0), (0, Spec.P)) + Scalar(0),
            id="y_2_equal_to_p",
        ),
        pytest.param(
            b"\x80" + bytes(Spec.INF_G2)[1:] + Scalar(0),
            id="invalid_encoding",
        ),
        pytest.param(
            (Spec.INF_G2 + Scalar(0))[:-1],
            id="input_too_short",
        ),
        pytest.param(
            b"\x00" + (Spec.INF_G2 + Scalar(0)),
            id="input_too_long",
        ),
        pytest.param(
            b"",
            id="zero_length_input",
        ),
    ],
)
@pytest.mark.parametrize("expected_output", [Spec.INVALID], ids=[""])
def test_invalid(
    state_test: StateTestFiller,
    pre: dict,
    post: dict,
    tx: Transaction,
):
    """
    Negative tests for the BLS12_G2MUL precompile.
    """
    state_test(
        env=Environment(),
        pre=pre,
        tx=tx,
        post=post,
    )


@pytest.mark.parametrize(
    "input,expected_output,precompile_gas_modifier",
    [
        pytest.param(
            Spec.INF_G2 + Scalar(0),
            Spec.INF_G2,
            1,
            id="extra_gas",
        ),
        pytest.param(
            Spec.INF_G2 + Scalar(0),
            Spec.INVALID,
            -1,
            id="insufficient_gas",
        ),
    ],
)
def test_gas(
    state_test: StateTestFiller,
    pre: dict,
    post: dict,
    tx: Transaction,
):
    """
    Test the BLS12_G1MUL precompile gas requirements.
    """
    state_test(
        env=Environment(),
        pre=pre,
        tx=tx,
        post=post,
    )


@pytest.mark.parametrize(
    "call_opcode",
    [
        Op.STATICCALL,
        Op.DELEGATECALL,
        Op.CALLCODE,
    ],
)
@pytest.mark.parametrize(
    "input,expected_output",
    [
        pytest.param(
            Spec.INF_G2 + Scalar(0),
            Spec.INF_G2,
            id="bls_g2mul_(0*inf=inf)",
        ),
    ],
)
def test_call_types(
    state_test: StateTestFiller,
    pre: dict,
    post: dict,
    tx: Transaction,
):
    """
    Test the BLS12_G2MUL using different call types.
    """
    state_test(
        env=Environment(),
        pre=pre,
        tx=tx,
        post=post,
    )
