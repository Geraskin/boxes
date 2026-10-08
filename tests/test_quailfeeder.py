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
_CMD = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


def _path_points(d):
    """Absolute points of an SVG path (line and curve end points)."""
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
        elif cmd in "LlTt":
            for i in range(0, len(values), 2):
                x, y = values[i], values[i + 1]
                points.append((x, y))
        elif cmd in "Cc":
            for i in range(0, len(values), 6):
                x, y = values[i + 4], values[i + 5]
                points.append((x, y))
        elif cmd in "SsQq":
            for i in range(0, len(values), 4):
                x, y = values[i + 2], values[i + 3]
                points.append((x, y))
        elif cmd in "Aa":
            # only the endpoint of the arc is kept
            for i in range(0, len(values), 7):
                x, y = values[i + 5], values[i + 6]
                points.append((x, y))
    return points


def _part_points(data, label):
    """All path points of the part whose label text contains *label*."""
    ns = "{http://www.w3.org/2000/svg}"
    root = etree.fromstring(data)
    for group in root.findall(ns + "g"):
        if not any(label in (text.text or "") for text in group.findall(ns + "text")):
            continue
        return [point for path in group.findall(ns + "path")
                for point in _path_points(path.get("d"))]
    raise AssertionError(f"part labelled {label!r} not found")


def _part_bbox(data, label):
    """Bounding box of the part whose label text contains *label*."""
    points = _part_points(data, label)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _edge_levels(data, label, along, offset):
    """Levels of joints along one edge of a part.

    ``along="y"`` collects the heights above the part's lowest point at
    ``x = min_x + offset``; ``along="x"`` collects the distances from the
    part's left edge at ``y = max_y - offset``.  Comparing two parts this
    way shows whether their joint patterns line up.
    """
    points = _part_points(data, label)
    min_x = min(point[0] for point in points)
    max_y = max(point[1] for point in points)
    if along == "y":
        fixed = min_x + offset
        values = [max_y - point[1] for point in points
                  if abs(point[0] - fixed) < 0.01]
    else:
        fixed = max_y - offset
        values = [point[0] - min_x for point in points
                  if abs(point[1] - fixed) < 0.01]
    return sorted({round(value, 2) for value in values})


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


def test_quailfeeder_wall_side_joints_match_side_panels():
    """The walls must be their nominal height with matching side joints.

    Using the "F" edge for their bottom edge reserved one material
    thickness, which made the walls that much taller and shifted their
    vertical joints, so they could not seat onto the side panels.
    """
    data = render_box("--FingerJoint_style=rectangular")
    thickness = 2.5

    panel = _edge_levels(data, "side left", "y", 0.0)
    front = _edge_levels(data, "front", "y", thickness)
    assert front == panel
    assert front[0] == pytest.approx(0.0)
    assert front[-1] == pytest.approx(35.0)

    back = _edge_levels(data, "back", "y", thickness)
    assert back[0] == pytest.approx(0.0)
    assert back[-1] == pytest.approx(55.0)


def test_quailfeeder_wall_bottom_notches_match_bottom_panel():
    """The notches cut into the walls' bottom edge must take the bottom's fingers."""
    data = render_box("--FingerJoint_style=rectangular")
    fingers = set(_edge_levels(data, "bottom", "x", 0.0))
    assert fingers
    for wall in ("front", "back"):
        levels = _edge_levels(data, wall, "x", 0.0)
        # the walls also carry their own side joints on that line
        assert fingers <= set(levels)
        # and the notches are one material thickness deep
        assert 2.5 in levels


def _render_removable(args):
    box = QuailFeeder()
    box.parseArgs(args.split())
    box.metadata["reproducible"] = True
    box.open()
    box.render()
    return box, box.close().getvalue()


def test_quailfeeder_removable_lid_drops_the_hinge():
    """A removable lid needs no hinge profile and no loose knuckle parts."""
    _, data = _render_removable("--lid_type=removable")
    etree.fromstring(data)

    ns = "{http://www.w3.org/2000/svg}"
    labels = [(text.text or "").strip() for text in etree.fromstring(data).iter(ns + "text")]
    assert "hinges" not in labels
    assert "feeding lid" in labels

    # plain top edges, so both walls stay at their nominal height
    assert _part_bbox(data, "front")[3] == pytest.approx(35.0)
    assert _part_bbox(data, "back")[3] == pytest.approx(55.0)


def test_quailfeeder_removable_lid_sits_between_the_side_stops():
    """The lid is shortened by both stops and the stops keep it in place."""
    box, data = _render_removable("--lid_type=removable --lid_stop=10 --lid_play=0.3 --lid_grip=0")
    thickness = box.thickness
    slope = box.lid_depth

    _, _, lid_width, lid_length = _part_bbox(data, "feeding lid")
    assert lid_width == pytest.approx(150.0, abs=0.01)
    assert lid_length == pytest.approx(slope - 2 * 10.0 - 0.3, abs=0.01)

    # each stop lifts its end of the sloped top edge by one thickness
    _, _, side_depth, side_height = _part_bbox(data, "side left")
    assert side_depth == pytest.approx(60.0, abs=0.01)
    assert side_height == pytest.approx(55.0 + thickness, abs=0.01)


def test_quailfeeder_removable_lid_grip_notch():
    """The finger notch is cut into the removable lid unless disabled."""
    _, with_notch = _render_removable("--lid_type=removable")
    _, without_notch = _render_removable("--lid_type=removable --lid_grip=0")

    assert len(_part_points(with_notch, "feeding lid")) > len(
        _part_points(without_notch, "feeding lid"))


def test_quailfeeder_rejects_oversized_lid_stops():
    box = QuailFeeder()
    box.parseArgs("--lid_type=removable --lid_stop=40".split())
    box.open()
    with pytest.raises(ValueError):
        box.render()
