# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import math

from boxes import *


class QuailFeeder(Boxes):
    """Sloped feeder with a hinged feeding lid and rear wall standoffs.

    The feeder is intended for laser-cut plywood.  The rear wall is higher
    than the front wall, so the lid slopes down toward the birds.  The lid
    has a configurable row of rounded feeding openings and is attached with
    the standard Boxes.py cabinet hinge.

    The two side panels have two integral rear bumps.  These bumps project
    past the back wall and can rest against a cage wall, keeping the body of
    the feeder slightly away from it.
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
            "--rear_stop_depth", type=float, default=12.0,
            help="how far the side-wall standoffs project behind the feeder")
        self.argparser.add_argument(
            "--rear_stop_height", type=float, default=10.0,
            help="height of each rear standoff bump")

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

    @property
    def lid_depth(self):
        """Length of the sloped lid from the back hinge to the front wall."""
        return math.hypot(self.depth, self.back_height - self.front_height)

    def lid_openings(self):
        """Callback that cuts the feeding openings into the lid."""
        n = self.opening_count
        w = self.opening_width
        margin = self.opening_margin
        usable_width = self.width - 2 * margin
        gap = (usable_width - n * w) / (n + 1)

        max_depth = self.lid_depth - 2 * margin
        opening_depth = min(self.opening_depth, max_depth)
        if opening_depth <= 0:
            raise ValueError("opening_margin leaves no room for feeding openings")

        radius = min(self.opening_radius, w / 2.0, opening_depth / 2.0)
        y = self.lid_depth / 2.0

        for i in range(n):
            x = margin + gap + w / 2.0 + i * (w + gap)
            self.rectangularHole(x, y, w, opening_depth, r=radius)

    def side_wall(self, move=None, label="side"):
        """Draw one side wall including the two integral rear standoffs.

        Front, back and bottom panels use finger tabs.  Matching finger-hole
        rows are cut inside the side panel; keeping the outer side outline
        straight/custom lets us add the rear standoff bumps without defining
        a special edge type.
        """
        t = self.thickness
        d = self.depth
        fh = self.front_height
        bh = self.back_height
        sd = self.rear_stop_depth
        sh = self.rear_stop_height

        # Leave some uninterrupted material above and below the bumps.
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
        th = bh
        if self.move(tw, th, move, before=True):
            return

        with self.saved_context():
            # Matching slots for the finger tabs on bottom/front/back panels.
            self.fingerHolesAt(0, 0.5 * t, d, 0)
            self.fingerHolesAt(0.5 * t, 0, fh, 90)
            self.fingerHolesAt(d - 0.5 * t, 0, bh, 90)

            # Custom outer contour with two rear-facing bumps.
            self.drawPoints(points, close=True)

        self.move(tw, th, move, label=label)

    def render(self):
        self._validate()

        w = self.width
        d = self.depth
        fh = self.front_height
        bh = self.back_height

        # Bottom: tabs on every edge.  Front/back walls mate with the front
        # and rear tabs; the two side walls contain matching finger-hole rows.
        self.rectangularWall(w, d, "ffff", move="up", label="bottom")

        # Front wall: finger-jointed to bottom and side-wall slots.
        self.rectangularWall(w, fh, "Ffef", move="up", label="front")

        # Rear wall: same construction, with a cabinet hinge along its top.
        self.rectangularWall(w, bh, "Ffuf", move="up", label="back")

        # Two identical side panels.  Rear bumps are integral to each panel.
        self.side_wall(move="right", label="side left")
        self.side_wall(move="right", label="side right")

        # Sloped lid.  U is the matching half of the cabinet hinge used by
        # the rear wall's u edge.  The other lid edges remain straight so it
        # can simply rest on the sloped side-wall edges and front wall.
        self.rectangularWall(
            w,
            self.lid_depth,
            "Ueee",
            callback=[self.lid_openings],
            move="up",
            label="feeding lid",
        )

        # Cabinet hinges require their separate eye/pin pieces as well.
        self.edges["u"].parts(move="up")
