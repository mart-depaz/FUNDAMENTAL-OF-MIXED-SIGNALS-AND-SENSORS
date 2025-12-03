from django import template

register = template.Library()


def _ordinal_suffix(value: int) -> str:
    """Return the ordinal suffix for a given integer."""
    if 10 <= value % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")


@register.filter
def ordinal_year(value):
    """
    Convert a numeric year level (e.g., 1, 2) into a human-readable ordinal label
    such as '1st Year' or '2nd Year'. Returns the original value if conversion
    fails.
    """
    try:
        year_int = int(value)
    except (TypeError, ValueError):
        return value

    suffix = _ordinal_suffix(year_int)
    return f"{year_int}{suffix} Year"

