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

    def immediate_byte(self) -> int:
        """Converts the first byte of the immediate value to unsigned value"""
        return int(self.immediate[0])

    def rjump_vector(self) -> list[int]:
        """Calculate the RJUMP vectors from the immediate data"""
        result = []
        for i in range(self.immediate_byte() + 1):
            result.append(
                int.from_bytes(self.immediate[i * 2 + 1 : i * 2 + 3], byteorder="big", signed=True)
            )
        return result

    def enter_stack(self, stack_min: int, stack_max: int):
        """Merges the existing stack minimums with a new min and max on opcode entry"""
        self.stack_min = min(self.stack_min, stack_min)
        self.stack_max = max(self.stack_max, stack_max)

    def reset_stack(self):
        """Set the stacka s though no calculations have been done"""
        self.stack_min = 1025
        self.stack_max = 0

    def point_size(self) -> int:
        """Calculates the number of bytes this code point occupies"""
        return 1 + len(self.immediate)

    def bytecode(self) -> bytes:
        """Converts the code point into the bytecode bytes it represents"""
        return self.opcode.int().to_bytes(1, byteorder="big") + self.immediate


class BasicBlock:
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
        return (
            self.label
            + "/"
            + "".join([str(point) for point in self.code_points])
            + ("->" + ",".join(self.successors) if self.successors else "")
        )


class BasicBlockSection:
    """A Code Section composed of multiple code blocks"""

    blocks: list[BasicBlock]
    inputs: int
    outputs: int
    max_stack: int

    def __init__(self, inputs, outputs, max_stack):
        """Create the code sesction with inputs, outputs and maxStack"""
        self.blocks = []
        self.inputs = inputs
        self.outputs = outputs
        self.max_stack = max_stack

    def fill_blocks(self, code: bytes, container):
        """Fill the blocks of the code section with the provided byecode"""
        opcodes: list[CodePoint | None] = [None] * len(code)

        breaks = self.calculate_block_breaks(code, opcodes)
        self.calculate_stack_heights(opcodes, container)
        self.create_code_blocks(breaks, opcodes)

    def calculate_block_breaks(self, code, opcodes) -> set[int]:
        """Calculate where the code block breaks occur"""
        index = 0
        breaks = {0}
        # Fill the code points with the opcodes
        while index < len(code):
            opNum = code[index]
            op = valid_eof_opcodes_by_num[opNum]
            if op is None:
                raise InvalidEOFCodeError("Unexpected OP Num %x" % opNum)

            code_point: CodePoint
            this_index = index
            if op == Op.RJUMPV:
                jumps = code[index + 1] + 1
                code_point = CodePoint(op, code[index + 1 : index + 2 + jumps * 2])
                index += 1 + jumps * 2
            elif op.data_portion_length > 0:
                code_point = CodePoint(op, code[index + 1 : index + 1 + op.data_portion_length])
                index += op.data_portion_length
            else:
                code_point = CodePoint(op)
            index += 1
            opcodes[this_index] = code_point

            if op == Op.RJUMPI or op == Op.RJUMP:
                breaks.add(index)
                breaks.add(index + code_point.immediate_signed())
            elif op == Op.RJUMPV:
                breaks.add(index)
                for dest in code_point.rjump_vector():
                    breaks.add(index + dest)
            elif op.terminating:
                breaks.add(index)
        return breaks

    def calculate_stack_heights(self, opcodes, container):
        """Calculate the stack heights of the code blocks"""
        # Calculate the stack heights
        stack_min = self.inputs
        stack_max = self.inputs
        for i, code_point in enumerate(opcodes):
            if code_point is None:
                continue
            op = code_point.opcode
            code_point.enter_stack(stack_min, stack_max)
            # We are presuming valid eof, otherwise we would check depth here
            if op == Op.CALLF:
                target_section = container.code_sections[code_point.immediate_signed()]
                delta = target_section.outputs - target_section.inputs
            else:
                delta = op.pushed_stack_items - op.popped_stack_items
            stack_min += delta
            stack_max += delta
            next_op = i + 1 + op.data_portion_length

            if op == Op.RJUMP or op == Op.RJUMPI:
                offset = code_point.immediate_signed()
                target = opcodes[next_op + offset]
                if target is not None and offset > 0:
                    target.enter_stack(stack_min, stack_max)
                # else validate back jump, but we are not validating
            elif op == Op.RJUMPV:
                next_op = i + 4 + code_point.immediate[0] * 2
                for j in range(code_point.immediate[0]):
                    index = 1 + j * 2
                    offset = int.from_bytes(
                        code_point.immediate[index : index + 2], byteorder="big", signed=True
                    )
                    target = opcodes[next_op + offset]
                    if target is not None and offset > 0:
                        target.enter_stack(stack_min, stack_max)

            if op.terminating and next_op < len(opcodes):
                opcode = opcodes[next_op]
                if opcode is not None:
                    # next opcode must be a jump target
                    stack_min = opcode.stack_min
                    stack_max = opcode.stack_max

    def create_code_blocks(self, breaks, opcodes):
        """From the block breaks and codepoints, calculate the code points."""
        # split into blocks
        code_block = None
        for i, code_point in enumerate(opcodes):
            if i in breaks and code_block is not None:
                self.blocks.append(code_block)
                code_block = None
            if code_point is None:
                continue
            if code_block is None:
                code_block = BasicBlock("i%d" % i)
            op = code_point.opcode
            if op is Op.RJUMP or op is Op.RJUMPI:
                code_block.successors = [
                    "i%d" % (i + 3),
                    "i%d" % (i + 3 + code_point.immediate_signed()),
                ]
            elif op is Op.RJUMPV:
                count_offset = i + 4 + code_point.immediate_byte() * 2
                code_block.successors = [
                    "i%d" % (i + count_offset),
                    *["i%d" % (j + count_offset) for j in code_point.rjump_vector()],
                ]
            code_block.append_code_point(code_point)
        if code_block is not None:
            self.blocks.append(code_block)  # needed?

    def reconcile_bytecode(self, code_sections):
        """Reconcile the bytecode.  `code_sections` is needed for CALLF and JUMPF"""
        blocks_by_id = {b.label: b for b in self.blocks}

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
            elif opcode == Op.RJUMPV:
                new_table = bytearray(code_point.immediate)
                for i in range(len(block.successors) - 1):
                    target_bytes = (offset_by_id[block.successors[i + 1]] - offset).to_bytes(
                        2, byteorder="big", signed=True
                    )
                    new_table[i * 2 + 1] = target_bytes[0]
                    new_table[i * 2 + 2] = target_bytes[1]
                code_point.immediate = bytes(new_table)

        # re-calculate the min/max stack
        for block in self.blocks:
            for code_point in block.code_points:
                code_point.reset_stack()

        section_max = self.inputs
        self.blocks[0].code_points[0].stack_min = section_max
        self.blocks[0].code_points[0].stack_max = section_max
        next_min = 0
        next_max = 0
        continuing = False
        for block in self.blocks:
            for code_point in block.code_points:
                if continuing:
                    code_point.enter_stack(next_min, next_max)
                section_max = max(section_max, code_point.stack_max)

                # stack height adjustment for what we just processed
                point_opcode = code_point.opcode
                if point_opcode == Op.CALLF:
                    target = code_sections[code_point.immediate_unsigned()]
                    delta = target.outputs - target.inputs
                else:
                    delta = point_opcode.pushed_stack_items - point_opcode.popped_stack_items

                # apply to next operation, lots of jump cases
                next_min = code_point.stack_min + delta
                next_max = code_point.stack_max + delta
                continuing = point_opcode.terminating is False

            # end of block, update all non-next successors, i.e. RJUMPI and RJUMPV targets
            for name in block.successors[1:]:
                blocks_by_id[name].code_points[0].enter_stack(next_min, next_max)
        self.max_stack = section_max

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


class BasicBlockContainer(AbstractContainer):
    """An EOF container in code block form"""

    sections: list[BasicBlockSection]
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
        Extracts the container in the bytes and stores it in this BasicBlockContainer.
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
            BasicBlockSection(
                data[index + x * 4], data[index + 1 + x * 4], short_at(data, index + 2 + x * 4)
            )
            for x in range(num_sections)
        ]
        index = index + 4 * num_sections
        for i in range(num_sections):
            self.code_sections[i].fill_blocks(data[index : index + section_sizes[i]], self)
            index += section_sizes[i]

        num_containers = len(container_sizes)
        self.containers = []
        for i in range(num_containers):
            self.containers.append(BasicBlockContainer(data[index : index + container_sizes[i]]))
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
