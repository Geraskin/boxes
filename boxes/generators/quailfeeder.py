# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import math

from boxes import *


class MountTabSegment(edges.BaseEdge):
    """Straight edge segment with a rectangular tab protruding outwards."""

    def __init__(self, boxes, depth, reference_edge) -> None:
        super().__init__(boxes, None)
        self.depth = depth
        self.reference_edge = reference_edge

    def startWidth(self) -> float:
        return self.reference_edge.startWidth()

    def endWidth(self) -> float:
        return self.reference_edge.endWidth()

    def margin(self) -> float:
        return max(self.reference_edge.margin(), self.depth)

    def __call__(self, length, **kw):
        # Opposite of a slot: step to the outside, run along the edge,
        # then return to the original edge line.
        self.corner(-90)
        self.edge(self.depth)
        self.corner(90)
        self.edge(length)
        self.corner(90)
        self.edge(self.depth)
        self.corner(-90)


class LidNotchSegment(edges.BaseEdge):
    """Straight edge segment with a rectangular notch cut into the part."""

    def __init__(self, boxes, depth) -> None:
        super().__init__(boxes, None)
        self.depth = depth

    def startWidth(self) -> float:
        return 0.0

    def endWidth(self) -> float:
        return 0.0

    def margin(self) -> float:
        return 0.0

    def __call__(self, length, **kw):
        # Mirror image of MountTabSegment: step into the material, run along
        # the notch and step back out to the edge line.
        self.corner(90)
        self.edge(self.depth)
        self.corner(-90)
        self.edge(length)
        self.corner(-90)
        self.edge(self.depth)
        self.corner(90)


class QuailFeeder(Boxes):
    """Sloped feeder with a hinged feeding lid and configurable wall mount.

    The feeder is intended for laser-cut plywood. The rear wall is higher
    than the front wall, so the lid slopes down toward the birds. The lid
    has a configurable row of rounded feeding openings. It is either
    attached with the standard Boxes.py cabinet hinge (which needs pieces of
    wire or nails as hinge axles) or cut as a drop-in lid. That one is cut to
    the outer width, so it rests on the side panels' sloped top edges, and a
    wide latch on the front wall's top edge keeps it from sliding down.

    Mounting can be done in three ways:

    * wall_tabs: one tab on the front wall and one on the rear wall, both on
      the selected left/right side. They pass through matching slots in that
      side panel and can continue into slots in the cage wall.
    * rear_standoffs: the original pair of rear-facing bumps on both side
      panels.
    * none: no extra mounting geometry.
    """

    ui_group = "Tray"

    def __init__(self) -> None:
        Boxes.__init__(self)

        self.addSettingsArgs(edges.FingerJointSettings)
        self.addSettingsArgs(edges.CabinetHingeSettings)

        self.argparser.add_argument(
            "--width", type=float, default=150.0,
            help="inner feeder width in mm")
        self.argparser.add_argument(
            "--depth", type=float, default=60.0,
            help="horizontal feeder depth in mm")
        self.argparser.add_argument(
            "--front_height", type=float, default=35.0,
            help="height of the front wall in mm")
        self.argparser.add_argument(
            "--back_height", type=float, default=55.0,
            help="height of the back wall in mm")

        self.argparser.add_argument(
            "--opening_count", type=int, default=5,
            help="number of feeding openings in the lid")
        self.argparser.add_argument(
            "--opening_width", type=float, default=18.0,
            help="feeding opening width in mm")
        self.argparser.add_argument(
            "--opening_depth", type=float, default=30.0,
            help="feeding opening size along the lid slope in mm")
        self.argparser.add_argument(
            "--opening_radius", type=float, default=5.0,
            help="corner radius of the feeding openings in mm")
        self.argparser.add_argument(
            "--opening_margin", type=float, default=8.0,
            help="minimum margin around the row of feeding openings in mm")

        self.argparser.add_argument(
            "--mount_style", type=str,
            choices=("wall_tabs", "rear_standoffs", "none"),
            default="wall_tabs",
            help="how the feeder mounts to the cage wall")
        self.argparser.add_argument(
            "--mount_side", type=str, choices=("left", "right"),
            default="right",
            help="side used by wall_tabs")
        self.argparser.add_argument(
            "--mount_tab_depth", type=float, default=12.0,
            help="how far the front/back mounting tabs protrude in mm")
        self.argparser.add_argument(
            "--mount_tab_height", type=float, default=10.0,
            help="height of each front/back mounting tab in mm")
        self.argparser.add_argument(
            "--mount_clearance", type=float, default=0.2,
            help="extra clearance added to matching side-panel mount slots in mm")

        self.argparser.add_argument(
            "--rear_stop_depth", type=float, default=12.0,
            help="how far rear_standoffs project behind the feeder")
        self.argparser.add_argument(
            "--rear_stop_height", type=float, default=10.0,
            help="height of each rear standoff bump")

        self.argparser.add_argument(
            "--lid_type", type=str, choices=("hinged", "removable"),
            default="hinged",
            help="how the feeding lid is held: cabinet hinge or drop-in lid")
        self.argparser.add_argument(
            "--lid_latch", type=float, default=80.0,
            help="width of the latch holding a removable lid in mm")
        self.argparser.add_argument(
            "--lid_latch_height", type=float, default=5.0,
            help="how far the lid latch rises above the front wall's top edge in mm")
        self.argparser.add_argument(
            "--lid_front_overhang", type=float, default=4.0,
            help="how far a removable lid overhangs the front wall in mm")
        self.argparser.add_argument(
            "--lid_play", type=float, default=0.4,
            help="clearance of a removable lid in the latch notch in mm")

    def _validate(self):
        t = self.thickness

        if self.width <= 4 * t:
            raise ValueError("width is too small for the selected material thickness")
        if self.depth <= 4 * t:
            raise ValueError("depth is too small for the selected material thickness")
        if self.front_height <= 2 * t:
            raise ValueError("front_height is too small for the selected material thickness")
        if self.back_height <= self.front_height:
            raise ValueError("back_height must be larger than front_height")
        if self.opening_count < 1:
            raise ValueError("opening_count must be at least 1")
        if self.opening_width <= 0 or self.opening_depth <= 0:
            raise ValueError("feeding opening dimensions must be positive")
        if self.opening_margin < 0:
            raise ValueError("opening_margin must not be negative")

        if self.mount_style == "wall_tabs":
            if self.mount_tab_depth <= 0:
                raise ValueError("mount_tab_depth must be positive")
            if self.mount_tab_height <= 0:
                raise ValueError("mount_tab_height must be positive")
            if self.mount_clearance < 0:
                raise ValueError("mount_clearance must not be negative")
            if self.mount_tab_height > self.front_height - 4 * t:
                raise ValueError(
                    "mount_tab_height is too large for front_height; leave room "
                    "for finger joints above and below the tab")

        if self.mount_style == "rear_standoffs":
            if self.rear_stop_depth < 0:
                raise ValueError("rear_stop_depth must not be negative")
            if self.rear_stop_height <= 0:
                raise ValueError("rear_stop_height must be positive")
            if self.back_height < 2 * self.rear_stop_height + 6 * t:
                raise ValueError(
                    "back_height is too small for two rear stops; reduce rear_stop_height")

        usable_width = self.width - 2 * self.opening_margin
        if self.opening_count * self.opening_width > usable_width:
            raise ValueError(
                "feeding openings do not fit; reduce opening_count/opening_width "
                "or opening_margin")

        if self.lid_type == "removable":
            if self.lid_latch <= 0:
                raise ValueError("lid_latch must be positive for a removable lid")
            if self.lid_latch_height <= 0:
                raise ValueError("lid_latch_height must be positive")
            if self.lid_front_overhang < 0:
                raise ValueError("lid_front_overhang must not be negative")
            if self.lid_play < 0:
                raise ValueError("lid_play must not be negative")
            if self.lid_latch + self.lid_play > self.width - 4 * t:
                raise ValueError(
                    "lid_latch is too wide for the front wall; reduce lid_latch")
            if self.lid_notch_depth + 2 * self.opening_margin >= self.lid_length:
                raise ValueError(
                    "the latch notch leaves no room for the feeding openings; "
                    "reduce lid_front_overhang or opening_margin")

    @property
    def lid_depth(self):
        """Length of the sloped lid from the back hinge to the front wall."""
        return math.hypot(self.depth, self.back_height - self.front_height)

    @property
    def lid_slope_ratio(self):
        """Length along the lid plane per mm of feeder depth."""
        return self.lid_depth / self.depth

    @property
    def lid_length(self):
        """Span of the lid along the slope, from its rear edge to its front edge.

        A removable lid seats its rear edge on the back wall's top edge (so
        there is no gap behind it) and overhangs the front wall.
        """
        if self.lid_type == "removable":
            reach = self.depth - self.thickness + self.lid_front_overhang
            return reach * self.lid_slope_ratio
        return self.lid_depth

    @property
    def lid_width(self):
        """Width of the lid: a removable one rests on top of the side panels.

        Sized to the outer width, so it sits on the side panels' sloped top
        edges instead of dropping in between them.
        """
        if self.lid_type == "removable":
            return self.width + 2 * self.thickness
        return self.width

    @property
    def lid_notch_depth(self):
        """Depth of the latch notch cut into the front edge of a removable lid.

        The notch reaches from the lid's front edge up to one material
        thickness behind the front wall's outer face, where the latch's inner
        face stops the lid from sliding down the slope.
        """
        reach = self.thickness + self.lid_front_overhang + self.lid_play
        return reach * self.lid_slope_ratio

    def lid_openings(self):
        """Callback that cuts the feeding openings into the lid."""
        n = self.opening_count
        w = self.opening_width
        margin = self.opening_margin
        usable_width = self.width - 2 * margin
        gap = (usable_width - n * w) / (n + 1)

        max_depth = self.lid_length - 2 * margin
        opening_depth = min(self.opening_depth, max_depth)
        if opening_depth <= 0:
            raise ValueError("opening_margin leaves no room for feeding openings")

        radius = min(self.opening_radius, w / 2.0, opening_depth / 2.0)
        y = self.lid_length / 2.0
        # a removable lid is wider than the opening, keep the row centred on it
        offset = (self.lid_width - self.width) / 2.0

        for i in range(n):
            x = offset + margin + gap + w / 2.0 + i * (w + gap)
            self.rectangularHole(x, y, w, opening_depth, r=radius)

    def _tab_split(self, height):
        tab_height = self.mount_tab_height
        lower = (height - tab_height) / 2.0
        upper = height - tab_height - lower
        return lower, tab_height, upper

    def _mount_edge(self, height):
        """Finger-jointed vertical edge with a centered outward mount tab."""
        lower, tab_height, upper = self._tab_split(height)
        finger = self.edges["f"]
        tab = MountTabSegment(self, self.mount_tab_depth, finger)
        return edges.CompoundEdge(
            self,
            [finger, tab, finger],
            [lower, tab_height, upper],
        )

    def _wall_side_edges(self, height):
        left = self.edges["f"]
        right = self.edges["f"]
        if self.mount_style == "wall_tabs":
            if self.mount_side == "left":
                left = self._mount_edge(height)
            else:
                right = self._mount_edge(height)
        return left, right

    def _side_joint_holes(self, x, height, has_mount_tab=False):
        """Finger holes for a front/back wall, plus one pass-through tab slot."""
        if not has_mount_tab:
            self.fingerHolesAt(x, 0, height, 90)
            return

        lower, tab_height, upper = self._tab_split(height)
        if lower > 0:
            self.fingerHolesAt(x, 0, lower, 90)
        if upper > 0:
            self.fingerHolesAt(x, lower + tab_height, upper, 90)

        clearance = self.mount_clearance
        self.rectangularHole(
            x,
            lower + tab_height / 2.0,
            self.thickness + clearance,
            tab_height + clearance,
        )

    def _bottom_notches(self, width):
        """Cut the notches taking the bottom panel's front/back fingers.

        Drawn explicitly instead of using the "F" edge: that edge reserves
        one material thickness, which made the walls one thickness taller
        than front_height/back_height and shifted their side joints.
        """
        settings = self.edges["f"].settings
        fingers, leftover = self.edges["f"].calcFingers(width, None)
        t = self.thickness
        for i in range(fingers):
            pos = leftover / 2.0 + i * (settings.space + settings.finger)
            self.rectangularHole(pos + 0.5 * settings.finger, 0.5 * t,
                                 settings.finger + settings.play,
                                 settings.width + settings.play)

    def _lid_notch_edge(self):
        """Lid front edge with the notch taking the latch of the front wall."""
        width = self.lid_latch + self.lid_play
        side = (self.lid_width - width) / 2.0
        notch = LidNotchSegment(self, self.lid_notch_depth)
        return edges.CompoundEdge(
            self,
            [self.edges["e"], notch, self.edges["e"]],
            [side, width, side],
        )

    def _lid_latch_edge(self):
        """Front wall top edge with the latch standing above it."""
        side = (self.width - self.lid_latch) / 2.0
        latch = MountTabSegment(self, self.lid_latch_height, self.edges["e"])
        return edges.CompoundEdge(
            self,
            [self.edges["e"], latch, self.edges["e"]],
            [side, self.lid_latch, side],
        )

    def side_wall(self, mounting_side=False, move=None, label="side"):
        """Draw one side wall and the matching front/back joint slots."""
        t = self.thickness
        d = self.depth
        fh = self.front_height
        bh = self.back_height

        if self.mount_style == "rear_standoffs":
            sd = self.rear_stop_depth
            sh = self.rear_stop_height

            edge_clearance = 2 * t
            low0 = edge_clearance
            low1 = low0 + sh
            high1 = bh - edge_clearance
            high0 = high1 - sh

            points = [
                (0, 0),
                (d, 0),
                (d, low0),
                (d + sd, low0),
                (d + sd, low1),
                (d, low1),
                (d, high0),
                (d + sd, high0),
                (d + sd, high1),
                (d, high1),
                (d, bh),
                (0, fh),
            ]
            tw = d + sd
        else:
            points = [
                (0, 0),
                (d, 0),
                (d, bh),
                (0, fh),
            ]
            tw = d

        th = bh
        if self.move(tw, th, move, before=True):
            return

        with self.saved_context():
            # The bottom sits between the front and back walls, so its
            # left/right edges only span the inner depth.
            self.fingerHolesAt(t, 0.5 * t, d - 2 * t, 0)

            use_mount_slots = self.mount_style == "wall_tabs" and mounting_side
            self._side_joint_holes(0.5 * t, fh, use_mount_slots)
            self._side_joint_holes(d - 0.5 * t, bh, use_mount_slots)

            self.drawPoints(points, close=True)

        self.move(tw, th, move, label=label)

    def render(self):
        self._validate()

        w = self.width
        d = self.depth
        fh = self.front_height
        bh = self.back_height
        t = self.thickness
        rear_edge = "u" if self.lid_type == "hinged" else "e"

        # The front and back walls are sandwiched between the side panels and
        # take up one material thickness each, so the bottom only spans the
        # inner depth. Otherwise its finger joints overhang front and back.
        self.rectangularWall(w, d - 2 * t, "ffff", move="up", label="bottom")

        front_latch = "e" if self.lid_type == "hinged" else self._lid_latch_edge()
        front_left, front_right = self._wall_side_edges(fh)
        self.rectangularWall(
            w,
            fh,
            ["e", front_right, front_latch, front_left],
            callback=[lambda: self._bottom_notches(w)],
            move="up",
            label="front",
        )

        back_left, back_right = self._wall_side_edges(bh)
        self.rectangularWall(
            w,
            bh,
            ["e", back_right, rear_edge, back_left],
            callback=[lambda: self._bottom_notches(w)],
            move="up",
            label="back",
        )

        self.side_wall(
            mounting_side=(self.mount_side == "left"),
            move="right",
            label="side left",
        )
        self.side_wall(
            mounting_side=(self.mount_side == "right"),
            move="right",
            label="side right",
        )

        if self.lid_type == "hinged":
            lid_edges = ["U", "e", "e", "e"]
        else:
            lid_edges = ["e", "e", self._lid_notch_edge(), "e"]
        self.rectangularWall(
            self.lid_width,
            self.lid_length,
            lid_edges,
            callback=[self.lid_openings],
            move="up",
            label="feeding lid",
        )

        if self.lid_type == "hinged":
            self.edges["u"].parts(move="up")
