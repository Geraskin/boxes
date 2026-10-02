"""Local fork defaults for the Boxes.py web application.

Keep upstream library defaults untouched while making every generator opened
through the local web server start with the settings used on this laser.
"""

import boxes


_LOCAL_WEB_DEFAULTS = {
    "thickness": 2.5,
    "burn": 0.0,
    "reference": 0.0,
}


if not getattr(boxes.Boxes, "_geraskin_web_defaults_patched", False):
    _original_boxes_init = boxes.Boxes.__init__

    def _boxes_init_with_local_web_defaults(self) -> None:
        _original_boxes_init(self)
        for action in self.argparser._actions:
            if action.dest in _LOCAL_WEB_DEFAULTS:
                action.default = _LOCAL_WEB_DEFAULTS[action.dest]

    boxes.Boxes.__init__ = _boxes_init_with_local_web_defaults
    boxes.Boxes._geraskin_web_defaults_patched = True
