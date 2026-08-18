def normalize_username(value: str) -> str:
    data = value.encode("ascii")
    return data.decode().lower()
