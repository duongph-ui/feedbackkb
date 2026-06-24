"""Step 0 smoke — package imports, version present."""

import feedbackkb_server


def test_package_imports():
    assert feedbackkb_server.__version__ == "0.0.0"


def test_package_has_docstring():
    assert feedbackkb_server.__doc__
    assert "standalone" in feedbackkb_server.__doc__.lower()
