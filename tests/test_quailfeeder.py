from lxml import etree
import pytest

from boxes.generators.quailfeeder import QuailFeeder


def render_box(args=""):
    box = QuailFeeder()
    box.parseArgs(args)
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
    box.parseArgs("--width=100 --opening_count=8 --opening_width=20")
    box.open()
    with pytest.raises(ValueError):
        box.render()


def test_quailfeeder_rejects_oversized_mount_tab():
    box = QuailFeeder()
    box.parseArgs("--mount_style=wall_tabs --mount_tab_height=30")
    box.open()
    with pytest.raises(ValueError):
        box.render()
