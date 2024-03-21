import datetime


def timestamp_to_datetime(unix_time):
    """
    Convert a Unix timestamp to a formatted string representing time in hours, minutes, and seconds.

    Parameters:
    - unix_time (int or float): Unix timestamp representing the number of seconds since the epoch (00:00:00 UTC on January 1, 1970).

    Returns:
    - str: A formatted string representing time in hours, minutes, and seconds in the format 'HH:MM:SS'.

    Example:
    >>> timestamp_to_datetime(1616382427)
    '03:40:27'
    """
    return datetime.datetime.fromtimestamp(unix_time).strftime(
        "%H:%M%:%S"
    )