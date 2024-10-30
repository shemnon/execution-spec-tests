"""
Types for EOF Fuzzing
"""
from abc import abstractmethod
from typing import Tuple

from ethereum_test_vm import Opcodes as Op
from ethereum_test_vm.opcode import valid_eof_opcodes_by_num


def concat_bytes(bytes_list: list[bytes]) -> bytes:
    """More readable form of byte concatenation"""
    return b"".join(bytes_list)


class InvalidEOFCodeError(Exception):
    """
    Invalid EOF code error raised when attempting to parse an EOF container with an invalid opcode.
    """

    def __init__(self, message):
        """Exception raised when the EOF container has invalid code"""
        super().__init__(message)


class CodePoint:
    """
    An opcode and associated metadata
    """

    opcode: Op
    immediate: bytes
    stack_min: int
    stack_max: int

    def __init__(self, opcode: Op, immediate: bytes = bytes()) -> None:
        """Create the code point, possibly with an immediate"""
        self.opcode = opcode
        self.immediate = immediate
        self.stack_min = 1025
        self.stack_max = 0

    def __str__(self) -> str:
        """A string representation that is opcode + immediate"""
        return "%02x%s[%d,%d]" % (
            bytes(self.opcode)[0],
            "" if self.immediate is None else self.immediate.hex(),
            self.stack_min,
            self.stack_max,
        )

    def immediate_signed(self) -> int:
        """Convert the immediate value to signed value"""
        return (
            0
            if self.immediate is None
            else int.from_bytes(bytes(self.immediate), byteorder="big", signed=True)
        )

    def immediate_unsigned(self) -> int:
        """Convert the immediate value to unsigned value"""
        return (
            0 if self.immediate is None else int.from_bytes(bytes(self.immediate), byteorder="big")
        )

    def enter_stack(self, stack_min: int, stack_max: int):
        """Merges the existing stack minimums with a new min and max on opcode entry"""
        self.stack_min = min(self.stack_min, stack_min)
        self.stack_max = max(self.stack_max, stack_max)

    def reset_stack(self):
        self.stack_min = 1025
        self.stack_max = 0

    def point_size(self) -> int:
        """Calculates the number of bytes this code point occupies"""
        return 1 + len(self.immediate)

    def bytecode(self) -> bytes:
        """Converts the code point into the bytecode bytes it represents"""
        return self.opcode.int().to_bytes(1, byteorder="big") + self.immediate


class CodeBlock:
    """A run of multiple code points with no branching or termination"""

    labels: str
    code_points: list[CodePoint]
    successors: list[str]
    offset: int
    _code_size: int | None

    def __init__(self, label: str):
        """Ceate a code block with a label"""
        self.label = label
        self.code_points = []
        self.successors = []
        self.offset = 0

    def append_code_point(self, code_point: CodePoint):
        """Append a code point to the code block.  Also resets the code size memento."""
        self._code_size = None
        self.code_points.append(code_point)

    def insert_code_point(self, index: int, code_point: CodePoint):
        """Inserts a code point into the code block.  Also resets the code size memento."""
        self._code_size = None
        self.code_points.insert(index, code_point)

    def remove_code_point(self, index: int):
        """Inserts a code point into the code block.  Also resets the code size memento."""
        self._code_size = None
        self.code_points.pop(index)

    def code_size(self):
        """Returns the number of bytes this code block would occupy"""
        if self._code_size is None:
            self._code_size = sum([point.point_size() for point in self.code_points])
        return self._code_size

    def bytecode(self) -> bytes:
        """Returns the opcodes as bytes for this block of code"""
        return concat_bytes([code_point.bytecode() for code_point in self.code_points])

    def __str__(self) -> str:
        """String representation of a code block"""
        return "".join([str(point) for point in self.code_points])


class CodeBlockSection:
    """A Code Section composed of multiple code blocks"""

    blocks: list[CodeBlock]
    inputs: int
    outputs: int
    max_stack: int

    def __init__(self, inputs, outputs, max_stack):
        """Create the code sesction with inputs, outputs and maxStack"""
        self.blocks = []
        self.inputs = inputs
        self.outputs = outputs
        self.max_stack = max_stack

    def fill_blocks(self, code: bytes):
        """Fill the blocks of the code section with the provided byecode"""
        index = 0
        opcodes: list[CodePoint | None] = [None] * len(code)
        breaks = {0}

        # Fill the code points with the opcodes
        while index < len(code):
            opNum = code[index]
            op = valid_eof_opcodes_by_num[opNum]
            if op is None:
                raise InvalidEOFCodeError("Unexpected OP Num %x" % opNum)

            codePoint: CodePoint
            this_index = index
            if op == Op.RJUMPV:
                jumps = code[index + 1] + 1
                codePoint = CodePoint(op, code[index + 1 : index + 2 + jumps * 2])
                index += 1 + jumps * 2
            elif op.data_portion_length > 0:
                codePoint = CodePoint(op, code[index + 1 : index + 1 + op.data_portion_length])
                index += op.data_portion_length
            else:
                codePoint = CodePoint(op)
            index += 1
            opcodes[this_index] = codePoint

            if op == Op.RJUMPI or op == Op.RJUMP:
                breaks.add(index)
                breaks.add(index + codePoint.immediate_signed())
            elif op == Op.RJUMPV:
                pass  # //FIXME
            elif op.terminating:
                breaks.add(index)

        # Calculate the stack heights
        stack_min = self.inputs
        stack_max = self.inputs
        for i, code_point in enumerate(opcodes):
            if code_point is None:
                continue
            op = code_point.opcode
            code_point.enter_stack(stack_min, stack_max)
            # We are presuming valid eof, otherwise we would check depth here
            delta = op.pushed_stack_items - op.popped_stack_items
            stack_min += delta
            stack_max += delta
            next_op = i + 1 + op.data_portion_length

            if op == Op.RJUMP or op == Op.RJUMPI:
                target = opcodes[i + 3 + code_point.immediate_signed()]
                if target is not None:
                    target.enter_stack(stack_min, stack_max)
            elif op == Op.RJUMPV:
                next_i = i + 4 + code_point.immediate[0] * 2
                for j in range(code_point.immediate[0]):
                    offset = 1 + j * 2
                    delta = int.from_bytes(
                        code_point.immediate[offset : offset + 2], byteorder="big", signed=True
                    )
                    target = opcodes[next_i + delta]
                    if target is not None:
                        target.enter_stack(stack_min, stack_max)
            elif op == Op.CALLF:
                pass
                # //FIXME

            if not op.terminating and next_op < len(opcodes):
                opcode = opcodes[next_op]
                if opcode is not None:
                    # next opcode must be a jump target
                    stack_min = opcode.stack_min
                    stack_max = opcode.stack_max

        # split into blocks
        code_block = None
        for i, code_point in enumerate(opcodes):
            if i in breaks and code_block is not None:
                self.blocks.append(code_block)
                code_block = None
            if code_point is None:
                continue
            if code_block is None:
                code_block = CodeBlock("i%d" % i)
            op = code_point.opcode
            if op is Op.RJUMP or op is Op.RJUMPI:
                code_block.successors = ["i%d"%(i+3), "i%d"%(i+3+code_point.immediate_signed())]
            code_block.append_code_point(code_point)
        if code_block is not None:
            self.blocks.append(code_block)  # needed?

    def reconcile_bytecode(self, code_sections):
        """Reconcile the bytecode.  `code_sections` is needed for CALLF and JUMPF"""
        # First update the "offset" so jumps can be re-coded
        offset = 0
        for block in self.blocks:
            block.offset = offset
            offset += block.code_size()

        # update jumps
        offset_by_id = {b.label: b.offset for b in self.blocks}
        offset = 0
        for block in self.blocks:
            offset += block.code_size()
            # if a jump exists they are the last code point in each block
            code_point = block.code_points[-1]
            opcode = code_point.opcode
            if opcode == Op.RJUMP or opcode == Op.RJUMPI:
                code_point.immediate = (offset_by_id[block.successors[1]] - offset).to_bytes(
                    2, byteorder="big", signed=True
                )

        # re-calculate the min/max stack
        for block in self.blocks:
            for code_point in block.code_points:
                code_point.reset_stack()

        prior: CodePoint | None = None
        stack_max = self.inputs
        for block in self.blocks:
            for code_point in block.code_points:
                prior_op = None if prior is None else prior.opcode
                if prior_op is not None:
                    if prior_op == Op.CALLF:
                        target = code_sections[prior.immediate_unsigned()]
                        delta = target.outputs - target.inputs
                    else:
                        delta = prior_op.pushed_stack_items - prior_op.popped_stack_items
                    code_point.enter_stack(
                        prior.stack_min + delta, prior.stack_max + delta
                    )
                else :
                    code_point.enter_stack(stack_max, stack_max)
                stack_max = max(stack_max, code_point.stack_max)
                prior = code_point
        self.max_stack = stack_max

    def bytecode(self) -> bytes:
        """Returns the bytes that represents the opcodes of this code section"""
        return concat_bytes([block.bytecode() for block in self.blocks])

    def type_data(self) -> bytes:
        """The bytes that represent this code section's type data (input/output/max stack)."""
        return (
            self.inputs.to_bytes(1, byteorder="big")
            + self.outputs.to_bytes(1, byteorder="big", signed=False)
            + self.max_stack.to_bytes(2, byteorder="big", signed=False)
        )

    def __str__(self) -> str:
        """String representation of a code block as equals joined blocks"""
        return "=".join([str(block) for block in self.blocks])


def short_at(b: bytes, index: int) -> int:
    """Helper function that gets a 2 byte unsigned value"""
    return int.from_bytes(b[index : index + 2], byteorder="big")


def read_header(b: bytes, index: int) -> Tuple[int, int, int]:
    """Helper function that reads a 3 byte EOF header"""
    return (b[index], short_at(b, index + 1), index + 3)


def read_multi_header(b: bytes, index: int) -> Tuple[int, list[int], int]:
    """Helper function that reads a list-form EOF header"""
    length = short_at(b, index + 1)
    return (
        b[index],
        [short_at(b, index + 3 + x * 2) for x in range(length)],
        index + 3 + length * 2,
    )


class AbstractContainer:
    """Abstract container to make typing less cranky"""

    @abstractmethod
    def encode(self):
        """Gets the byte representation of the container"""
        pass


class CodeBlockContainer(AbstractContainer):
    """An EOF container in code block form"""

    sections: list[CodeBlockSection]
    data: bytes
    data_length: int
    containers: list[AbstractContainer]  # type games to prevent self-typed reference

    def __init__(self, data: bytes):
        self.sections = []
        self.data_length = 0
        self.containers = []
        self.decode(data, None)

    def decode(self, data: bytes, parent: AbstractContainer | None = None):
        """
        Extracts the container in the bytes and stores it in this CodeBlockContainer.
        If a container was held in this object,it will be completely overwriten.
        """
        if not data.startswith(b"\xef\0\x01\x01"):
            raise InvalidEOFCodeError("Bad magic bytes")

        (header, types_sizes, index) = read_header(data, 3)
        if header != 1:
            raise InvalidEOFCodeError("expected section 1")
        (header, section_sizes, index) = read_multi_header(data, index)
        if header != 2:
            raise InvalidEOFCodeError("expected section 2")
        if data[index] == 3:
            (header, container_sizes, index) = read_multi_header(data, index)
        else:
            container_sizes = []
            header = 3
        (header, data_size, index) = read_header(data, index)
        if header != 4:
            raise InvalidEOFCodeError("expected section 4")

        if data[index] != 0:
            raise InvalidEOFCodeError("expected section terminator")
        else:
            index = index + 1

        num_sections = len(section_sizes)
        self.code_sections = [
            CodeBlockSection(
                data[index + x * 4], data[index + 1 + x * 4], short_at(data, index + 2 + x * 4)
            )
            for x in range(num_sections)
        ]
        index = index + 4 * num_sections
        for i in range(num_sections):
            self.code_sections[i].fill_blocks(data[index : index + section_sizes[i]])
            index += section_sizes[i]

        # //TODO this will not handle deepest recursion and will need to be re-written linearly
        num_containers = len(container_sizes)
        self.containers = []
        for i in range(num_containers):
            self.containers.append(CodeBlockContainer(data[index : index + container_sizes[i]]))
            index += container_sizes[i]

        self.data_length = data_size
        self.data = data[index:]

    def encode(self) -> bytes:
        """Encodes the entire container into the bytes of a complete EOF container"""
        section_bytecode = [section.bytecode() for section in self.code_sections]
        containers = [container.encode() for container in self.containers]

        result = b""
        result += b"\xef\0\x01"

        result += b"\x01" + (len(section_bytecode) * 4).to_bytes(2, byteorder="big")

        result += b"\x02" + (len(section_bytecode)).to_bytes(2, byteorder="big")
        for bytecode in section_bytecode:
            result += len(bytecode).to_bytes(2, byteorder="big")

        if len(containers) > 0:
            result += b"\x03" + (len(containers)).to_bytes(2, byteorder="big")
            for container in containers:
                result += len(container).to_bytes(2, byteorder="big")

        result += b"\x04" + self.data_length.to_bytes(2, byteorder="big")

        result += b"\0"

        for section in self.code_sections:
            result += section.type_data()

        for bytecode in section_bytecode:
            result += bytecode

        for container in containers:
            result += container

        result += self.data

        return result

    def reconcile_bytecode(self):
        """
        Updates values like stack and relative offsets for jumps for the whole container.
        After modifying any of the code points or code sections this should be called to ensure
        that the bytecode produced is valid
        """
        for code_section in self.code_sections:
            code_section.reconcile_bytecode(self.code_sections)

    def __str__(self):
        """String representation of a code block as joined blocks"""
        return "{\n code sections: [\n  %s\n ],\n containers: %s,\n data: %s\n}" % (
            "\n  ".join(str(section) for section in self.code_sections),
            "\n  ".join(str(container) for container in self.containers),
            self.data,
        )
