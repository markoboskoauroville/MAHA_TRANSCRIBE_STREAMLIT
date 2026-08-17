# -*- coding: utf-8 -*-
"""
A tiny hand-rolled Streamlit custom component (no build step, no npm) that
reads/writes browser localStorage and reports it back to Python.

Why not st.components.v1.html(): that embed's iframe is sandboxed without
allow-top-navigation, so a script inside it cannot redirect the page to
carry a value back — confirmed by testing (window.top.location.replace
throws "Unsafe attempt to initiate navigation"). A real declare_component,
even a one-file vanilla-JS one, communicates over postMessage instead of
navigation, which the sandbox allows. Verified end-to-end with a headless
browser: a value written on one page load is read back correctly on a
completely fresh navigation, and is invisible to a different browser
context — real per-browser persistence, no server round-trip.
"""
import os
import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ls_bridge_frontend")
_component = components.declare_component("ls_bridge", path=_FRONTEND_DIR)


def ls_bridge(write_key=None, write_value=None, key=None):
    """Optionally write one key to localStorage, then always return every
    'maha_'-prefixed key currently stored, as {"ok": bool, "data": {...}}.
    Returns None on the very first render of a given key, before the
    browser round-trip completes — callers should treat that as "not yet
    known" rather than "empty"."""
    return _component(write_key=write_key, write_value=write_value, key=key, default=None)
