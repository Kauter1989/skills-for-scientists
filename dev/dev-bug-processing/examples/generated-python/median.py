def median(values):
    """Вернуть медиану списка чисел."""
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle]