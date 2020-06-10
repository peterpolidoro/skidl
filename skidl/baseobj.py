# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by XESS Corp.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Base object for Circuit, Interface, Package, Part, Net, Bus, Pin objects.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re
from builtins import object, str, super
from copy import deepcopy
from collections import namedtuple
import inspect

from future import standard_library

from .Alias import Alias
from .AttrDict import AttrDict
from .defines import *
# from .erc import eval_stmnt_list, exec_function_list
from .logger import erc_logger
from .Note import Note

standard_library.install_aliases()


class SkidlBaseObject(object):

    # These are fallback lists so every object will have them to reference.
    erc_list = list()
    erc_assertion_list = list()

    def __init__(self):
        self.fields = AttrDict(attr_obj=self)

    def __setattr__(self, key, value):
        if key == "fields":
            # Whatever is assigned to the fields attribute is cast to an AttrDict.
            super().__setattr__(key, AttrDict(attr_obj=self, **value))

        else:
            super().__setattr__(key, value)

            # Whenever an attribute is changed, then also sync it with the fields dict
            # in case it is mirroring one of the dict entries.
            self.fields.sync(key)

    @property
    def aliases(self):
        try:
            return self._aliases
        except AttributeError:
            return Alias([])  # No aliases, so just return an empty list.

    @aliases.setter
    def aliases(self, name_or_list):
        if not name_or_list:
            return
        self._aliases = Alias(name_or_list)

    @aliases.deleter
    def aliases(self):
        try:
            del self._aliases
        except AttributeError:
            pass

    @property
    def notes(self):
        try:
            return self._notes
        except AttributeError:
            return Note([])  # No notes, so just return empty list.

    @notes.setter
    def notes(self, text_or_notes):
        if not text_or_notes:
            return
        self._notes = Note(text_or_notes)

    @notes.deleter
    def notes(self):
        try:
            del self._notes
        except AttributeError:
            pass

    def copy(self):
        cpy = SkidlBaseObject()
        cpy.fields = deepcopy(self.fields)
        try:
            cpy.aliases = deepcopy(self.aliases)
        except AttributeError:
            pass
        try:
            cpy.notes = deepcopy(self.notes)
        except AttributeError:
            pass
        return cpy

    def ERC(self, *args, **kwargs):
        """Run ERC on this object."""

        # Run ERC functions.
        exec_function_list(self, "erc_list", *args, **kwargs)

        # Run ERC assertions.
        eval_stmnt_list(self, "erc_assertion_list")


    def add_erc_function(self, func):
        """Add an ERC function to a class or class instance."""

        self.erc_list.append(func)


    def add_erc_assertion(self, assertion, fail_msg="FAILED", severity=ERROR):
        """Add an ERC assertion to a class or class instance."""

        # Tuple for storing assertion code object with its global & local dicts.
        EvalTuple = namedtuple(
            "EvalTuple", "stmnt fail_msg severity filename lineno function globals locals"
        )

        assertion_frame, filename, lineno, function, _, _ = inspect.stack()[1]
        self.erc_assertion_list.append(
            EvalTuple(
                assertion,
                fail_msg,
                severity,
                filename,
                lineno,
                function,
                assertion_frame.f_globals,
                assertion_frame.f_locals,
            )
        )


def eval_stmnt_list(inst, list_name):
    """
    Evaluate class-wide and local statements on a class instance.

    Args:
        inst: Instance of a class.
        list_name: String containing the attribute name of the list of
            class-wide and local code objects.
    """

    def erc_report(evtpl):
        log_msg = "{evtpl.stmnt} {evtpl.fail_msg} in {evtpl.filename}:{evtpl.lineno}:{evtpl.function}.".format(
            evtpl=evtpl
        )
        if evtpl.severity == ERROR:
            erc_logger.error(log_msg)
        elif evtpl.severity == WARNING:
            erc_logger.warning(log_msg)

    # Evaluate class-wide statements on this instance.
    if list_name in inst.__class__.__dict__:
        for evtpl in inst.__class__.__dict__[list_name]:
            try:
                assert eval(evtpl.stmnt, evtpl.globals, evtpl.locals)
            except AssertionError:
                erc_report(evtpl)

    # Now evaluate any statements for this particular instance.
    if list_name in inst.__dict__:
        for evtpl in inst.__dict__[list_name]:
            try:
                assert eval(evtpl.stmnt, evtpl.globals, evtpl.locals)
            except AssertionError:
                erc_report(evtpl)


def exec_function_list(inst, list_name, *args, **kwargs):
    """
    Execute class-wide and local ERC functions on a class instance.

    Args:
        inst: Instance of a class.
        list_name: String containing the attribute name of the list of
            class-wide and local functions.
        args, kwargs: Arbitary argument lists to pass to the functions
            that are executed. (All functions get the same arguments.) 
    """

    # Execute the class-wide functions on this instance.
    if list_name in inst.__class__.__dict__:
        for f in inst.__class__.__dict__[list_name]:
            f(inst, *args, **kwargs)

    # Now execute any instance functions for this particular instance.
    if list_name in inst.__dict__:
        for f in inst.__dict__[list_name]:
            f(inst, *args, **kwargs)
