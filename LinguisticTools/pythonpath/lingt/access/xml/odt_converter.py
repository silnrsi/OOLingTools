# -*- coding: Latin-1 -*-
#
# This file created June 22 2015 by Jim Kornelsen
#
# 16-Dec-15 JDK  Fixed bug: specify absolute path to xml files.
# 17-Dec-15 JDK  Implemented readContentFile with limited functionality.
# 22-Dec-15 JDK  Read a list of text nodes.
# 23-Dec-15 JDK  Added changeContentFile().
# 24-Dec-15 JDK  Added class OdtChanger.
# 20-Feb-16 JDK  Read complex and Asian font types.
# 21-Jun-16 JDK  Choose font type based on Unicode block.

"""
Read and change an ODT file in XML format.
Call SEC_wrapper to do engine-based conversion.

This module exports:
    OdtReader
    OdtChanger
"""
import copy
import io
import os
import xml.dom.minidom
import xml.parsers.expat

from lingt.access.common.file_reader import FileReader
from lingt.access.xml import xmlutil
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import FontItem
from lingt.utils import letters
from lingt.utils import util


class OdtReader(FileReader):

    SUPPORTED_FORMATS = [("xml", "Unzipped Open Document Format (.odt)"),]

    def __init__(self, srcdir, unoObjs):
        FileReader.__init__(self, unoObjs)
        self.srcdir = srcdir
        self.defaultFontItem = None
        self.stylesDom = None
        self.contentDom = None
        self.stylesDict = {}  # keys style name, value FontItem

    def _initData(self):
        """Elements are of type bulkconv_structs.FontItem."""
        self.data = []

    def _verifyDataFound(self):
        if not self.data:
            raise exceptions.DataNotFoundError(
                "Did not find any fonts in folder %s", self.srcdir)

    def _read(self):
        self.stylesDom = self.loadFile(
            os.path.join(self.srcdir, 'styles.xml'))
        self.progressBar.updatePercent(30)
        self.readStylesFile(self.stylesDom)
        self.progressBar.updatePercent(35)

        self.contentDom = self.loadFile(
            os.path.join(self.srcdir, 'content.xml'))
        self.progressBar.updatePercent(45)
        self.readContentFile(self.contentDom)
        self.progressBar.updatePercent(50)

    def loadFile(self, filepath):
        """Returns dom, raises exceptions.FileAccessError."""
        self.logger.debug(util.funcName('begin', args=filepath))
        if not os.path.exists(filepath):
            raise exceptions.FileAccessError(
                "Cannot find file %s", filepath)
        dom = None
        try:
            dom = xml.dom.minidom.parse(filepath)
        except xml.parsers.expat.ExpatError as exc:
            raise exceptions.FileAccessError(
                "Error reading file %s\n\n%s",
                filepath, str(exc).capitalize())
        if dom is None:
            raise exceptions.FileAccessError(
                "Error reading file %s", filepath)
        self.logger.debug(util.funcName('end'))
        return dom

    def readStylesFile(self, dom):
        """Read in styles.xml."""
        self.logger.debug(util.funcName('begin'))
        for style in dom.getElementsByTagName("style:default-style"):
            if style.getAttribute("style:family") == "paragraph":
                self.defaultFontItem = self.read_text_props(style)
        for style in dom.getElementsByTagName("style:style"):
            xmlStyleName = style.getAttribute("style:name")
            parentStyleName = style.getAttribute("style:parent-style-name")
            if parentStyleName in self.stylesDict:
                parentFontItem = self.stylesDict[parentStyleName]
                if xmlStyleName in self.stylesDict:
                    fontItem = self.stylesDict[xmlStyleName]
                    for attrName in (
                            'nameStandard', 'nameComplex', 'nameAsian'):
                        if parentFontItem.getattr(attrName) != "(None)":
                            setattr(
                                fontItem, attrName,
                                parentFontItem.getattr(attrName))
                else:
                    fontItem = parentFontItem
                self.stylesDict[xmlStyleName] = fontItem
            self.read_text_props(style)
        self.logger.debug(util.funcName('end'))

    def read_text_props(self, styleNode):
        """Read style:text-properties nodes and store in self.stylesDict.
        Returns the FontItem for that style.
        """
        xmlStyleName = styleNode.getAttribute("style:name")
        if xmlStyleName in self.stylesDict:
            fontItem = self.stylesDict[xmlStyleName]
        else:
            fontItem = FontItem()
        for textprop in styleNode.getElementsByTagName(
                "style:text-properties"):
            # Western is last in the list because it is the default.
            # The others will only be used if there are Complex or Asian
            # characters in the text.
            for xmlAttr, fontItemAttr, fontType in [
                    ("style:font-name-asian", 'nameAsian', 'Asian'),
                    ("style:font-name-complex", 'nameComplex', 'Complex'),
                    ("style:font-name", 'nameStandard', 'Western')]:
                fontName = textprop.getAttribute(xmlAttr)
                if fontName:
                    fontItem.name = fontName
                    fontItem.fontType = fontType
                    setattr(fontItem, fontItemAttr, fontName)
                    self.stylesDict[xmlStyleName] = fontItem
        return self.stylesDict.get(xmlStyleName, FontItem())

    def readContentFile(self, dom):
        """Read in content.xml."""
        self.logger.debug(util.funcName('begin'))
        # Unlike common styles, automatic styles are not visible to the user.
        auto_styles = dom.getElementsByTagName("office:automatic-styles")[0]
        if auto_styles:
            for style in auto_styles.childNodes:
                self.read_text_props(style)
        for paragraph in dom.getElementsByTagName("text:p"):
            xmlStyleName = paragraph.getAttribute("text:style-name")
            paraFontItem = self.stylesDict.get(
                xmlStyleName, self.defaultFontItem)
            para_texts = xmlutil.getElemTextList(paragraph)
            fontItemAppender = FontItemAppender(self.data, paraFontItem)
            fontItemAppender.add_texts(para_texts)
            for span in paragraph.getElementsByTagName("text:span"):
                xmlStyleName = span.getAttribute("text:style-name")
                spanFontItem = self.stylesDict.get(xmlStyleName, paraFontItem)
                span_texts = xmlutil.getElemTextList(span)
                fontItemAppender = FontItemAppender(self.data, spanFontItem)
                fontItemAppender.add_texts(span_texts)
        #TODO: look for text:class-name, which is for paragraph styles.
        self.logger.debug(util.funcName('end'))


class FontItemAppender:
    """Adds information to a list of FontItem objects.  Modifies the list."""

    FONT_TYPE_NUM_TO_NAME = {
        letters.TYPE_INDETERMINATE : 'Western',
        letters.TYPE_STANDARD : 'Western',
        letters.TYPE_COMPLEX : 'Complex',
        letters.TYPE_CJK : 'Asian',
        }

    def __init__(self, fontItems, baseFontItem):
        """
        :param fontItems: list of FontItem objects to modify
        :param baseFontItem: effective font of the node
        """
        self.fontItems = fontItems
        self.baseFontItem = baseFontItem
        self.fontItemDict = None

    def add_for_font_with_debug(self, textvals, xmlStyleName):
        self.logger.debug(
            util.funcName(args=(
                self.baseFontItem.name, len(textvals), xmlStyleName)))
        self.add_for_font(textvals)

    def add_texts(self, textvals):
        """Add content of a node for a particular effective font.
        :param textvals: text content of nodes
        """
        if not self.baseFontItem.name or self.baseFontItem.name == "(None)":
            return
        for newItem in self.get_items_for_each_type(textvals):
            self.add_item_data(newItem)

    def get_items_for_each_type(self, textvals):
        self.fontItemDict = {
            'Western' : None, 'Complex' : None, 'Asian' : None}
        text_of_one_type = ""
        for textval in textvals:
            curFontType = letters.TYPE_INDETERMINATE
            for c in textval:
                nextFontType = letters.getFontType(c, curFontType)
                if nextFontType == curFontType:
                    text_of_one_type += c
                elif text_of_one_type:
                    self.append_text_of_one_type(text_of_one_type, curFontType)
                    text_of_one_type = ""
                curFontType = nextFontType
            if text_of_one_type:
                self.append_text_of_one_type(text_of_one_type, curFontType)
        return list(self.fontItemDict.values())

    def append_text_of_one_type(self, textval, curFontType):
        fontTypeName = self.FONT_TYPE_NUM_TO_NAME[curFontType]
        fontItem = self.get_item_for_type(fontTypeName)
        fontItem.inputData.append(textval)

    def self.get_item_for_type(self, fontType):
        """
        Sets fontItem.fontType and fontItem.name.

        The font type is based on the unicode block of a character,
        not just based on formatting.
        Because the font name may just fall back to defaults.
        """
        if fontType in self.fontItemDict:
            return self.fontItemDict[fontType]
        attr_of_fontType = {
            'Asian' : 'nameAsian',
            'Complex' : 'nameComplex',
            'Western' : 'nameStandard'}
        newItem = copy.deepcopy(self.baseFontItem)
        #if (nextFontType == letters.TYPE_COMPLEX
        #        or nextFontType == letters.TYPE_CJK):
        newItem.fontType = fontType
        newItem.name = getattr(self.baseFontItem, attr_of_font_type[fontType])
        self.fontItemDict[fontType] = newItem
        return newItem

    def add_item_data(self, newItem):
        for item in self.fontItems:
            if item == newItem:
                item.inputData.extend(newItem.inputData)
                break
        else:
            # newItem was not in self.fontItems, so add it.
            self.logger.debug("appending FontItem %s", newItem)
            self.fontItems.append(newItem)


class OdtChanger:
    def __init__(self, reader, fontChanges):
        """
        :param reader: type OdtReader
        :param fontChanges: list of elements type FontChange
        """
        self.reader = reader
        self.logger = reader.logger
        self.fontChanges = fontChanges

    def makeChanges(self):
        self.logger.debug(util.funcName('begin'))
        num_changes = self.change_text(self.reader.contentDom)
        self.change_styles(self.reader.contentDom, self.reader.stylesDom)
        with io.open(os.path.join(self.reader.srcdir, 'styles.xml'),
                     mode="wt", encoding="utf-8") as f:
            self.reader.stylesDom.writexml(f, encoding="utf-8")
        with io.open(os.path.join(self.reader.srcdir, 'content.xml'),
                     mode="wt", encoding="utf-8") as f:
            self.reader.contentDom.writexml(f, encoding="utf-8")
        self.logger.debug(util.funcName('end'))
        return num_changes

    def change_text(self, dom):
        """Convert text in content.xml with EncConverters."""
        self.logger.debug(util.funcName('begin'))
        num_changes = 0
        for paragraph in dom.getElementsByTagName("text:p"):
            xmlStyleName = paragraph.getAttribute("text:style-name")
            #self.logger.debug("para style name %s", xmlStyleName)
            paraFontItem = self.reader.stylesDict.get(
                xmlStyleName, self.reader.defaultFontItem)
            paraFontChange = self.effective_fontChange(paraFontItem)
            if paraFontChange:
                for para_child in paragraph.childNodes:
                    if para_child.nodeType == para_child.TEXT_NODE:
                        if para_child.data in paraFontChange.converted_data:
                            para_child.data = paraFontChange.converted_data[
                                para_child.data]
                            num_changes += 1
            for span in paragraph.getElementsByTagName("text:span"):
                xmlStyleName = span.getAttribute("text:style-name")
                #self.logger.debug("span style name %s", xmlStyleName)
                spanFontItem = self.reader.stylesDict.get(
                    xmlStyleName, paraFontItem)
                spanFontChange = self.effective_fontChange(spanFontItem)
                if spanFontChange:
                    for span_child in span.childNodes:
                        if span_child.nodeType == span_child.TEXT_NODE:
                            if (span_child.data in
                                    spanFontChange.converted_data):
                                span_child.data = (
                                    spanFontChange.converted_data[
                                        span_child.data])
                            num_changes += 1
        self.logger.debug(util.funcName('end'))
        return num_changes

    def change_styles(self, contentDom, stylesDom):
        """Change fonts and styles."""
        for style in (
                contentDom.getElementsByTagName("style:font-face") +
                stylesDom.getElementsByTagName("style:font-face")):
            fontName = style.getAttribute("style:name")
            for fontChange in self.fontChanges:
                if fontName == fontChange.fontItem.name:
                    style.setAttribute("style:name", fontChange.name)
                    style.setAttribute("svg:font-family", fontChange.name)
        for style in (
                contentDom.getElementsByTagName("style:style") +
                stylesDom.getElementsByTagName("style:default-style")):
            for textprop in style.getElementsByTagName(
                    "style:text-properties"):
                fontName = textprop.getAttribute("style:font-name")
                for fontChange in self.fontChanges:
                    if fontName == fontChange.fontItem.name:
                        textprop.setAttribute(
                            "style:font-name", fontChange.name)
                        #style.setAttribute(
                        #    "style:parent-style-name", fontChange.fontType)
                        #fontSize = textprop.getAttribute("fo:font-size")
                        #if fontSize and fontChange.size.isSpecified():
                        if fontChange.size.isSpecified():
                            textprop.setAttribute(
                                "fo:font-size", str(fontChange.size) + "pt")

    def effective_fontChange(self, fontItem):
        """Returns the FontChange object for the effective font,
        that is, the font specified by a paragraph node or
        overridden by a span node.
        """
        if fontItem is None:
            return None
        for fontChange in self.fontChanges:
            #if fontChange == fontItem:  #TODO
            if (fontChange.name == fontItem.name
                    and fontChange.nameComplex == fontItem.nameComplex):
                return fontChange
        return None

