"""Prompt templates for testgen-agent.

This module exists so that `prompts/` is a package and its `.txt` templates can
be declared as package data — `agent.py` resolves them with
`Path(__file__).parent / "prompts"`, so in an installed (non-editable) copy they
must sit next to the other modules in site-packages. There is no Python code
here beyond this docstring.
"""
