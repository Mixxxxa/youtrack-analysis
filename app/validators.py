from youtrack.utils.others import is_valid_iso8601_date


def host_validator(value: str) -> str:
    if value.startswith('https://') or value.startswith('http://'):
        raise ValueError(f"Host should contain only host-name (without 'http:// or https://'). Example: 'myhost.myjetbrains.com'")
    return value


def api_key_validator(value: str) -> str:
    if value.startswith('Bearer perm:'):
        return value
    raise ValueError("YouTrack API key should start with 'Bearer perm:'")


def iso8601_date_validator(value: str) -> str:
    value = value.strip()
    if is_valid_iso8601_date(value):
        return value
    raise ValueError("Incorrect date format. Expected format is ISO8601, eg. 2025-12-24")