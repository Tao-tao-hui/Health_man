from build123d import (
    BuildPart,
    Box,
    Solid,
)


def gen_step() -> Solid:
    """Generate a simple cube for testing."""
    with BuildPart() as part:
        Box(100.0, 60.0, 8.0)

    return part.part
