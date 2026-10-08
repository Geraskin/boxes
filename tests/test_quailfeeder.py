import re

from lxml import etree
import pytest

from boxes.generators.quailfeeder import QuailFeeder


def render_box(args=""):
    box = QuailFeeder()
    box.parseArgs(args.split())
    box.metadata["reproducible"] = True
    box.open()
    box.render()
    return box.close().getvalue()


def test_quailfeeder_default_renders_valid_svg():
    data = render_box()
    assert len(data) > 100
    etree.fromstring(data)


def test_quailfeeder_wall_tabs_left_renders_valid_svg():
    data = render_box(
        "--mount_style=wall_tabs --mount_side=left "
        "--mount_tab_depth=14 --mount_tab_height=9"
    )
    etree.fromstring(data)


def test_quailfeeder_rear_standoffs_renders_valid_svg():
    data = render_box(
        "--width=180 --depth=70 --front_height=35 --back_height=60 "
        "--opening_count=6 --opening_width=18 "
        "--mount_style=rear_standoffs --rear_stop_depth=15"
    )
    etree.fromstring(data)


def test_quailfeeder_without_mount_renders_valid_svg():
    data = render_box("--mount_style=none")
    etree.fromstring(data)


def test_quailfeeder_rejects_too_many_openings():
    box = QuailFeeder()
    box.parseArgs("--width=100 --opening_count=8 --opening_width=20".split())
    box.open()
    with pytest.raises(ValueError):
        box.render()


def test_quailfeeder_rejects_oversized_mount_tab():
    box = QuailFeeder()
    box.parseArgs("--mount_style=wall_tabs --mount_tab_height=30".split())
    box.open()
    with pytest.raises(ValueError):
        box.render()


_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)")
_CMD = re.compile(r"[MmLlHhVvZz]")


def _path_points(d):
    """Absolute points of a straight line SVG path (M/L/H/V/Z commands)."""
    points = []
    x = y = 0.0
    for cmd, args in zip(_CMD.findall(d), _CMD.split(d)[1:]):
        values = [float(v) for v in _NUM.findall(args)]
        if cmd in "Mm":
            for i in range(0, len(values), 2):
                x, y = values[i], values[i + 1]
                points.append((x, y))
        elif cmd in "Hh":
            x = values[-1]
            points.append((x, y))
        elif cmd in "Vv":
            y = values[-1]
            points.append((x, y))
        elif cmd in "Ll":
            x, y = values[-2], values[-1]
            points.append((x, y))
    return points


def _part_bbox(data, label):
    """Bounding box of the part whose label text contains *label*."""
    ns = "{http://www.w3.org/2000/svg}"
    root = etree.fromstring(data)
    for group in root.findall(ns + "g"):
        if not any(label in (text.text or "") for text in group.findall(ns + "text")):
            continue
        points = [point for path in group.findall(ns + "path")
                  for point in _path_points(path.get("d"))]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    raise AssertionError(f"part labelled {label!r} not found")


def test_quailfeeder_bottom_does_not_overhang():
    """The bottom sits between the front and back walls."""
    box = QuailFeeder()
    box.parseArgs("--FingerJoint_style=rectangular".split())
    box.metadata["reproducible"] = True
    box.open()
    thickness = box.thickness
    box.render()
    data = box.close().getvalue()

    _, _, bottom_width, bottom_depth = _part_bbox(data, "bottom")
    # Its finger joints protrude sideways into the side panels only. Towards
    # the front and back they fill the walls' bottom edges instead.
    assert bottom_depth == pytest.approx(box.depth)
    assert bottom_width == pytest.approx(box.width + 2 * thickness)

    _, _, side_depth, _ = _part_bbox(data, "side left")
    assert side_depth == pytest.approx(box.depth)
