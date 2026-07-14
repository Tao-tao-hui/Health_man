from build123d import *
from cadpy.assembly import AssemblyHelper

BODY_LENGTH = 150.0
BODY_WIDTH = 72.0
BODY_HEIGHT = 36.0
CORNER_RADIUS = 12.0
BODY_FILLET = 6.0

ELECTRODE_WIDTH = 38.0
ELECTRODE_HEIGHT = 52.0
ELECTRODE_THICK = 1.5
ELECTRODE_CORNER = 6.0

PPG_DIAMETER = 14.0
PPG_HEIGHT = 2.5
PPG_RING_DIAMETER = 19.0
PPG_RING_HEIGHT = 1.2

LED_LENGTH = 30.0
LED_WIDTH = 2.5


def make_body():
    """Organic body — smooth pebble form on XY plane, extruded +Z"""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            RectangleRounded(BODY_LENGTH, BODY_WIDTH, CORNER_RADIUS)
        extrude(amount=BODY_HEIGHT)
        fillet(bp.edges(), radius=BODY_FILLET)
    return bp.part


def make_electrode():
    """Electrode plate on YZ plane, extruded +X, center at origin"""
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            RectangleRounded(ELECTRODE_WIDTH, ELECTRODE_HEIGHT, ELECTRODE_CORNER)
        extrude(amount=ELECTRODE_THICK)
    return bp.part


def make_ppg_window():
    """PPG optical sensor window"""
    return Cylinder(radius=PPG_DIAMETER / 2, height=PPG_HEIGHT)


def make_ppg_ring():
    """Accent ring around PPG sensor"""
    outer = Cylinder(radius=PPG_RING_DIAMETER / 2, height=PPG_RING_HEIGHT)
    inner = Cylinder(radius=PPG_DIAMETER / 2, height=PPG_RING_HEIGHT)
    return outer - inner


def make_led_strip():
    """LED ambient light strip"""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            RectangleRounded(LED_LENGTH, LED_WIDTH, 1.2)
        extrude(amount=1.0)
    return bp.part


def gen_step():
    body = make_body()
    asm = AssemblyHelper("flowform_health_scanner")
    asm.add(body, "body")

    left_el = make_electrode()
    left_el = left_el.moved(Location(
        (-BODY_LENGTH / 2 - ELECTRODE_THICK, 0, BODY_HEIGHT / 2 - 2)
    ))
    asm.add(left_el, "electrode_left")

    right_el = make_electrode()
    right_el = right_el.moved(Location(
        (BODY_LENGTH / 2, 0, BODY_HEIGHT / 2 - 2)
    ))
    asm.add(right_el, "electrode_right")

    ppg = make_ppg_window()
    ppg = ppg.moved(Location((0, 0, BODY_HEIGHT)))
    asm.add(ppg, "ppg_window")

    ring = make_ppg_ring()
    ring = ring.moved(Location((0, 0, BODY_HEIGHT)))
    asm.add(ring, "ppg_ring")

    led = make_led_strip()
    led = led.moved(Location((0, BODY_WIDTH / 2 - 4, BODY_HEIGHT)))
    asm.add(led, "led_strip")

    return asm.build()


if __name__ == "__main__":
    compound = gen_step()
    export_step(compound, "E:\\个人用\项目开发\大健康\\cad\\health_scanner.step")
    print("Health Scanner STEP exported OK")
