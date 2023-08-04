INT_NULL_VAL = 0


def serialize_int(value: int, size: int):
    return value.to_bytes(size, "big") if value else INT_NULL_VAL.to_bytes(size, "big")


def deserialize_int(value: bytes):
    deserialize_value = int.from_bytes(value, "big")

    return deserialize_value if deserialize_value != INT_NULL_VAL else deserialize_value
