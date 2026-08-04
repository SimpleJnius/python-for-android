"""Tests for pythonforandroid's implementation of Kivy's Android bootstrap
contract (``_kivy_bootstrap.py``, shipped by the ``android`` recipe).

Off-device, so ``jnius`` and the build-generated ``android.config`` are faked,
following the same approach as test_androidmodule_ctypes_finder.py. Faking
``android.config`` directly in ``sys.modules`` (rather than importing the real
``android`` package) also sidesteps ``android/__init__.py``'s
``from android._android import *``, which needs the native extension this
module must not depend on.
"""
import os
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock

import pytest

# Import the module under test the way Kivy does: top-level, not under
# `android` (see the comment in recipes/android/src/setup.py).
android_src_folder = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "..", "pythonforandroid", "recipes", "android", "src"
))
sys.path.insert(0, android_src_folder)


@contextmanager
def _bootstrap_module(activity_class_name="org.kivy.android.PythonActivity"):
    """Import a fresh ``_kivy_bootstrap`` against faked jnius/android.config.

    A fresh import per use avoids the module's cached ``_activity_class``
    leaking between tests.
    """
    fake_jnius = MagicMock()
    fake_config = ModuleType("android.config")
    fake_config.ACTIVITY_CLASS_NAME = activity_class_name
    with mock.patch.dict(
        sys.modules, jnius=fake_jnius, **{"android.config": fake_config}
    ):
        sys.modules.pop("_kivy_bootstrap", None)
        import _kivy_bootstrap
        try:
            yield SimpleNamespace(module=_kivy_bootstrap, jnius=fake_jnius)
        finally:
            sys.modules.pop("_kivy_bootstrap", None)


@pytest.fixture
def kivy_bootstrap():
    with _bootstrap_module() as bootstrap:
        yield bootstrap


def test_get_activity_reflects_the_configured_class(kivy_bootstrap):
    """The class reflected is the build's ACTIVITY_CLASS_NAME, not a literal."""
    activity = object()
    java_class = MagicMock(mActivity=activity)
    # `_kivy_bootstrap` did `from jnius import autoclass` at import time, so
    # the name it calls is already bound to this mock: configure its return
    # value rather than replacing the attribute on `kivy_bootstrap.jnius`,
    # which the module would never see.
    kivy_bootstrap.jnius.autoclass.return_value = java_class

    assert kivy_bootstrap.module.get_activity() is activity
    kivy_bootstrap.jnius.autoclass.assert_called_once_with(
        "org.kivy.android.PythonActivity"
    )


def test_get_activity_honours_custom_activity_class_name():
    """--activity-class-name is honoured: the name comes from android.config."""
    with _bootstrap_module("com.example.CustomActivity") as bootstrap:
        bootstrap.module.get_activity()
        bootstrap.jnius.autoclass.assert_called_once_with(
            "com.example.CustomActivity"
        )


def test_get_activity_may_return_none(kivy_bootstrap):
    """A p4a service has no Activity; None is a legitimate answer."""
    java_class = MagicMock(mActivity=None)
    kivy_bootstrap.jnius.autoclass.return_value = java_class

    assert kivy_bootstrap.module.get_activity() is None


def test_get_activity_resolves_the_class_once_but_reads_it_live(kivy_bootstrap):
    """The reflected class is cached; the live Activity is read fresh each call.

    Regression guard for the module's core promise: Android may recreate the
    Activity (rotation, config change, process death), so a second call must
    return whatever ``mActivity`` is *now*, not a value from the first call.
    """
    java_class = MagicMock()
    kivy_bootstrap.jnius.autoclass.return_value = java_class

    first_activity = object()
    java_class.mActivity = first_activity
    assert kivy_bootstrap.module.get_activity() is first_activity

    second_activity = object()
    java_class.mActivity = second_activity
    assert kivy_bootstrap.module.get_activity() is second_activity

    # autoclass() itself -- the expensive reflection -- only happens once.
    kivy_bootstrap.jnius.autoclass.assert_called_once()


def test_remove_presplash_is_a_noop_without_an_activity(kivy_bootstrap):
    """No Activity (a service) means no splash to remove, and no error."""
    java_class = MagicMock(mActivity=None)
    kivy_bootstrap.jnius.autoclass.return_value = java_class

    kivy_bootstrap.module.remove_presplash()  # must not raise


def test_remove_presplash_calls_removeLoadingScreen(kivy_bootstrap):
    """The splash is dismissed by asking the Activity, not a fixed method map."""
    activity = MagicMock()
    java_class = MagicMock(mActivity=activity)
    kivy_bootstrap.jnius.autoclass.return_value = java_class

    kivy_bootstrap.module.remove_presplash()

    activity.removeLoadingScreen.assert_called_once_with()


def test_remove_presplash_is_a_noop_when_activity_lacks_the_method(kivy_bootstrap):
    """service_only (and any custom activity) may have no splash to remove."""
    activity = SimpleNamespace()  # no removeLoadingScreen attribute at all
    java_class = MagicMock(mActivity=activity)
    kivy_bootstrap.jnius.autoclass.return_value = java_class

    kivy_bootstrap.module.remove_presplash()  # must not raise
