# -*- coding: Latin-1 -*-
#
# This file created Aug 8 2015 by Jim Kornelsen
#
# 24-Aug-15 JDK  Define __str__() instead of toItemText().
# 25-Aug-15 JDK  Add FontItem.numberedVar().
# 18-Dec-15 JDK  Use rich comparisons instead of getID().
# 24-Dec-15 JDK  Moved part of FontItem to a new FontChange class.
# 05-Feb-16 JDK  Show a mark in the list to indicate font changes.
# 19-Feb-16 JDK  Add fonts found of each type.
# 22-Jun-16 JDK  Add method to group items.
# 24-Jun-16 JDK  FontItemList holds FontItemGroup instead of FontItem.

"""
Data structures for Bulk Conversion used by lower layer packages.
To avoid cyclic imports, these are not defined in the BulkConversion module.

This module exports:
    FontItem
    FontChange
"""
import copy
import functools

from lingt.access.sec_wrapper import ConverterSettings
from lingt.access.writer.uservars import Syncable
from lingt.app import exceptions
from lingt.utils.fontsize import FontSize


class FontInfo:
    STYLETYPE_CUSTOM = 'CustomFormatting'
    STYLETYPE_PARA = 'ParaStyle'
    STYLETYPE_CHAR = 'CharStyle'

    def __init__(self):
        self.name = ""  # font name
        self.fontType = 'Western'  # 'Western' (Standard), 'Complex' or 'Asian'
        self.size = FontSize()
        self.styleType = self.STYLETYPE_CUSTOM
        self.styleDisplayName = ""  # for example "Default Style"
        self.styleName = ""  # underlying name of styleDisplayName, "Standard"

    def __repr__(self):
        return repr(self.name, self.styleName)

    def getPropSuffix(self):
        """For use in UNO properties such as CharFontComplex."""
        if self.fontType == 'Western':
            return ""
        else:
            return self.fontType


@functools.total_ordering
class FontItem(FontInfo):
    """A structure to hold input data for one font."""

    def __init__(self):
        FontInfo.__init__(self)
        self.name = "(Default)"  # could be a standard name, complex or Asian
        self.nameStandard = "(Default)"  # could be non-Unicode Devanagari
        self.nameComplex = "(Default)"  # CTL fonts such as Unicode Devanagari
        self.nameAsian = "(Default)"  # Chinese, Japanese, Korean (CJK) fonts
        self.inputData = list()  # data that gets read from the file
        self.inputDataOrder = 0  # sort order this item occurred in the file
        self.change = None  # type FontChange

    def create_change(self, userVars):
        """Create a new FontChange for this item if it doesn't exist yet.
        Now this item will be recognized as having a change,
        even if the values aren't actually any different.
        """
        if not self.change:
            self.change = FontChange(self, userVars)

    def set_change(self, fontChange):
        self.change = fontChange
        fontChange.fontItem = self

    def effective_info(self):
        """Gets the FontInfo object that is currently effective."""
        if self.change:
            return self.change
        else:
            return self

    def __str__(self):
        strval = str(self.name)
        if self.styleDisplayName:
            strval += " (%s)" % self.styleDisplayName
        if self.change:
            strval = "*  " + strval
        return strval

    def attrs(self):
        """Attributes that uniquely identify this object.
        Used for magic methods below.
        """
        return (
            self.name, self.fontType,
            self.styleName, self.styleType,
            self.size,
            self.nameStandard, self.nameComplex, self.nameAsian)

    def __lt__(self, other):
        return (isinstance(other, FontItem) and
                self.attrs() < other.attrs())

    def __eq__(self, other):
        """This method gets used when testing for membership using *in*,
        as odt_converter.py does.
        """
        #pylint: disable=protected-access
        return (isinstance(other, FontItem) and
                self.attrs() == other.attrs())
        #pylint: enable=protected-access

    def __hash__(self):
        """Make instances with identical attributes use the same hash."""
        return hash(self.attrs())


class FontChange(FontInfo, Syncable):
    """A structure to hold form data for changing one font."""

    def __init__(self, font_from, userVars, varNum=0):
        """
        :param font_from: FontItem being converted from
        :param userVars: for persistent storage
        :param varNum: a user variable number unique to this change
        """
        FontInfo.__init__(self)
        Syncable.__init__(self, userVars)
        self.fontItem = font_from
        self.varNum = varNum  # for storage in user variables
        self.converter = ConverterSettings(userVars)
        self.converted_data = dict()  # key inputString, value convertedString

    def setVarNum(self, varNum):
        self.varNum = varNum

    def varNumStr(self):
        """Many user variables for the class contain this substring,
        based on enumerating the font items.
        Specify varNum before calling this method.
        """
        return "%03d" % self.varNum

    def numberedVar(self, suffix=""):
        """Get a user variable name that includes the file number.
        :param suffix: Add this to the end of the string.
        """
        return "font%s_%s" % (self.varNumStr(), suffix)

    def loadUserVars(self):
        self.fontItem.name = self.userVars.get(
            self.numberedVar("fontNameFrom"))
        self.fontItem.styleDisplayName = self.userVars.get(
            self.numberedVar("styleNameFrom"))
        if not self.fontItem.name and not self.fontItem.styleDisplayName:
            raise self.noUserVarData(self.numberedVar("fontNameFrom"))
        self.name = self.userVars.get(self.numberedVar("fontNameTo"))
        self.styleDisplayName = self.userVars.get(
            self.numberedVar("styleNameTo"))
        self.fontType = self.userVars.get(self.numberedVar("fontType"))
        self.size = FontSize()
        if not self.userVars.isEmpty(self.numberedVar("size")):
            self.size.loadUserVar(self.userVars, self.numberedVar("size"))
        self.styleType = self.userVars.get(self.numberedVar("styleType"))
        self.styleDisplayName = self.userVars.get(
            self.numberedVar("styleName"))
        self.converter.convName = self.userVars.get(
            self.numberedVar("convName"))
        self.converter.normForm = self.userVars.getInt(
            self.numberedVar("normalize"))
        varname = self.numberedVar('forward')
        if (not self.userVars.isEmpty(varname) and
                self.userVars.getInt(varname) == 0):
            self.converter.forward = False

    def storeUserVars(self):
        """Sets the user vars for this item."""
        fontNameFrom = self.fontItem.name
        if fontNameFrom == "(None)":
            fontNameFrom = None  #TESTME
        self.userVars.store(self.numberedVar("fontNameFrom"), fontNameFrom)
        self.userVars.store(self.numberedVar("fontNameTo"), self.name)
        self.userVars.store(
            self.numberedVar("styleNameFrom"), self.fontItem.styleDisplayName)
        self.userVars.store(
            self.numberedVar("styleNameTo"), self.styleDisplayName)
        self.userVars.store(self.numberedVar("fontType"), self.fontType)
        self.userVars.store(self.numberedVar("styleType"), self.styleType)
        if self.size.isSpecified():
            self.userVars.store(
                self.numberedVar('size'), self.size.getString())
        self.userVars.store(
            self.numberedVar("convName"), self.converter.convName)
        self.userVars.store(
            self.numberedVar('forward'), str(int(self.converter.forward)))
        self.userVars.store(
            self.numberedVar("normalize"), str(self.converter.normForm))

    def cleanupUserVars(self):
        """Returns True if something was cleaned up."""
        foundSomething1 = self.userVars.delete(
            self.numberedVar("fontNameFrom"))
        foundSomething2 = self.userVars.delete(
            self.numberedVar("styleNameFrom"))
        self.userVars.delete(self.numberedVar("fontNameTo"))
        self.userVars.delete(self.numberedVar("styleNameTo"))
        self.userVars.delete(self.numberedVar("fontType"))
        self.userVars.delete(self.numberedVar('size'))
        self.userVars.delete(self.numberedVar("styleType"))
        self.userVars.delete(self.numberedVar("convName"))
        self.userVars.delete(self.numberedVar('forward'))
        self.userVars.delete(self.numberedVar("normalize"))
        return foundSomething1 or foundSomething2

    def setattr_from_other(self, other, attr_name):
        """
        :param other: FontChange object to read from
        :param attr_name: for example 'styleName' or 'converter.name'
        """
        attr_names = attr_name.split('.')
        this_container = self._last_container(attr_names)
        # pylint: disable=protected-access
        other_container = other._last_container(attr_names)
        # pylint: enable=protected-access
        last_attr_name = attr_names[-1]
        other_value = getattr(other_container, last_attr_name)
        setattr(this_container, last_attr_name, other_value)

    def _last_container(self, attr_names):
        """Returns the object that contains the last attribute in
        attr_names.
        """
        if len(attr_names) == 1:
            return self
        if attr_names[0] == 'converter':
            return self.converter
        raise exceptions.LogicError(
            "Unexpected attribute names: %r", attr_names)


def _generic_item_attrs():
    """Returns all attribute names of the FontItem class."""
    return FontItem().__dict__.keys()

def _generic_change_attrs():
    """Returns all attribute names of the FontChange class."""
    generic_item = FontItem()
    generic_change = FontChange(generic_item, None)
    return generic_change.__dict__.keys()

@functools.total_ordering
class FontItemGroup():
    """Holds one or more related FontItem objects.
    This is what gets displayed in the list.
    """
    VARIOUS = "(Various)"

    def __init__(self, fontItems):
        """:param fontItems: list of FontItem objects for one group."""
        self.items = fontItems
        self.different_item_attrs = set()  # names of FontItem attrs
        self.different_change_attrs = set()  # names of FontChange attrs
        self.effective_item = None
        self.reload()

    def reload(self):
        self._determine_variations()
        self._determine_effective_item()

    def _determine_variations(self):
        """Find any attributes that vary across items in the group."""
        self.different_item_attrs = set()
        self.different_change_attrs = set()
        if len(self.items) <= 1:
            # No variations since there are not multiple items.
            return
        first_item = self.items[0]
        first_change = first_item.change
        for attr in _generic_item_attrs():
            for item in self.items[1:]:
                if getattr(first_item, attr) != getattr(item, attr):
                    self.different_item_attrs.add(attr)
                    break
        for attr in _generic_change_attrs():
            for item in self.items[1:]:
                if not first_change and not item.change:
                    continue
                if ((first_change and not item.change)
                        or (item.change and not first_change)
                        or (getattr(first_change, attr) !=
                            getattr(item.change, attr))):
                    self.different_change_attrs.add(attr)
                    break

    def _determine_effective_item(self):
        """Returns an item with this group's values, where values that vary are
        marked as such.
        """
        fontItem = FontItem()
        for attr in _generic_item_attrs():
            setattr(fontItem, attr, self.itemattr(attr))
        if fontItem.change or self.itemattr_varies('change'):
            fontItem.change = FontChange(fontItem, None)
            for attr in _generic_change_attrs():
                setattr(fontItem.change, attr, self.changeattr(attr))
        #TODO: merge inputData lists
        #TODO: if two items have different converters, then don't perform
        #      any conversion -- leave converted text blank
        self.effective_item = fontItem

    def itemattr(self, attr):
        """Get a FontItem attribute."""
        return self._get_attr_or_various(
            self.get_first_item(), attr, self.itemattr_varies(attr))

    def changeattr(self, attr):
        """Get a FontChange attribute."""
        return self._get_attr_or_various(
            self.get_first_change(), attr, self.changeattr_varies(attr))

    def _get_attr_or_various(self, info, attr, varies):
        if not varies:
            return getattr(info, attr)
        if attr == 'size':
            return FontSize()
        if attr == 'inputData':
            return []
        if attr == 'change':
            return FontChange(FontItem(), None)
        if attr == 'converter':
            return ConverterSettings(None)
        if attr == 'converted_data':
            return dict()
        # Must be an attribute of type string.
        return self.VARIOUS

    def get_first_item(self):
        """Attributes of the first item can be used to display the information
        unless the attributes are in self.different_attrs.
        """
        if len(self.items):
            return self.items[0]
        return FontItem()

    def get_first_change(self):
        item = self.first_item()
        if item.change:
            return item.change
        return FontChange(item, None)

    def itemattr_varies(self, attr):
        """Returns true if values vary across items in the group."""
        return attr in different_item_attrs

    def changeattr_varies(self, attr):
        return attr in different_change_attrs

    def __lt__(self, other):
        # < calls FontItem.__lt__() defined in this module.
        return (isinstance(other, FontItemGroup) and
                self.effective_item() < other.effective_item())

    def __eq__(self, other):
        # == calls FontItem.__eq__() defined in this module.
        return (isinstance(other, FontItemGroup) and
                self.effective_item() == other.effective_item())
