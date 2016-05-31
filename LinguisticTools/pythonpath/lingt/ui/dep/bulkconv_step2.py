# -*- coding: Latin-1 -*-
#
# This file created December 24 2015 by Jim Kornelsen
#
# 05-Feb-16 JDK  Show a mark in the list to indicate font changes.
# 11-Feb-16 JDK  Show modified font settings when FontItem is selected.
# 19-Feb-16 JDK  Add checkboxes to separate font type, size and style.
# 24-Feb-16 JDK  Use a single foundFonts label instead of three labels.
# 07-Mar-16 JDK  Handle chkJoin changes.
# 25-Mar-16 JDK  Split up into separate classes for each control.
# 26-Apr-16 JDK  Implement separate style classes for combos and radios.
# 29-Apr-16 JDK  Add methods for filling to each control class.
# 16-May-16 JDK  Separate class for sample labels because ctrl props change.
# 28-May-16 JDK  Added Step2Master.
# 31-May-16 JDK  Standardize names of filling methods.

"""
Bulk Conversion dialog step 2.

This module exports:
    FormStep2
"""
import collections
import copy
import logging

from lingt.access.writer import styles
from lingt.app import exceptions
from lingt.app.data.bulkconv_structs import FontItem, FontChange
from lingt.app.svc.bulkconversion import Samples
from lingt.ui.common import dutil
from lingt.ui.common import evt_handler
from lingt.ui.common.dlgdefs import DlgBulkConversion as _dlgdef
from lingt.utils import util
from lingt.utils.fontsize import FontSize
from lingt.utils.locale import theLocale

logger = logging.getLogger("lingt.ui.dlgbulkconv_step2")


class FormStep2:
    """Create control classes and load values."""

    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = Step2Master(ctrl_getter, app)
        self.event_handlers = []
        self.event_handlers.extend(self.step2Master.get_event_handlers())
        self.event_handlers.extend([
            ClipboardButtons(ctrl_getter, app, self.step2Master),
            JoinCheckboxes(ctrl_getter, app, self.step2Master),
            VerifyHandler(ctrl_getter, app)
            ])

    def start_working(self):
        for event_handler in self.event_handlers:
            event_handler.start_working()
        found_font_info = FoundFontInfo(self.ctrl_getter, self.app)
        found_font_info.load_values()

    def store_results(self):
        """Store settings in user vars."""
        logger.debug(util.funcName('begin'))
        fontChanges = self.app.getFontChanges()
        self.app.userVars.store('FontChangesCount', str(len(fontChanges)))
        varNum = 0
        for fontChange in fontChanges:
            fontChange.setVarNum(varNum)
            varNum += 1
            fontChange.userVars = self.app.userVars
            fontChange.storeUserVars()

        MAX_CLEAN = 1000  # should be more than enough
        for varNum in range(len(fontChanges), MAX_CLEAN):
            fontChange = FontChange(None, self.app.userVars, varNum)
            foundSomething = fontChange.cleanupUserVars()
            if not foundSomething:
                break

        checkboxShowConverter = CheckboxShowConverter(
            self.ctrl_getter, self.app)
        checkboxShowConverter.store_results()
        verifyHandler = VerifyHandler(self.ctrl_getter, self.app)
        verifyHandler.store_results()
        logger.debug(util.funcName('end'))

    def refresh_and_fill_list(self):
        self.step2Master.refresh_and_fill_list()


class Step2Master:
    """Controls that need to be called by events.  The controls objects are
    maintained across events.
    """
    def __init__(self, ctrl_getter, app):
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.listFontsUsed = ListFontsUsed(ctrl_getter, app, self)
        self.data_controls = []  # controls that store FontItem data
        for ctrl_class in (
                ConverterControls,
                FontNameHandler,
                FontTypeHandler,
                FontSizeHandler,
                StyleTypeHandler,
                StyleNameHandler,
            ):
            controls_object = ctrl_class(ctrl_getter, app)  # create new
            self.data_controls.append(controls_object)

    def get_event_handlers(self):
        return [self.listFontsUsed] + self.data_controls

    def read_change(self):
        """Reads the form and returns a FontChange object."""
        fontChange = FontChange(None, self.app.userVars)
        for fontitem_controls in self.data_controls:
            fontitem_controls.update_change(fontChange)
        return fontChange

    def copy_change_attrs(self, change_from, change_to):
        """Set attributes of change_to based on change_from."""
        for fontitem_controls in self.data_controls:
            fontitem_controls.copy_change(change_from, change_to)

    def refresh_and_fill_list(self):
        self.listFontsUsed.refresh_and_fill()

    def fill_for_item(self, fontItem):
        """Fill form according to specified font settings."""
        logger.debug(util.funcName('begin'))
        foundFontInfo = FoundFontInfo(self.ctrl_getter, self.app)
        for fontitem_controls in self.data_controls + [foundFontInfo]:
            fontitem_controls.fill_for_item(fontItem)
        logger.debug(util.funcName('end'))


class ClipboardButtons(evt_handler.ActionEventHandler):
    """This does not actually use the system clipboard, but it implements
    copy/paste functionality.
    """
    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ActionEventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = step2Master
        self.btnReset = ctrl_getter.get(_dlgdef.BTN_RESET)
        self.btnCopy = ctrl_getter.get(_dlgdef.BTN_COPY)
        self.btnPaste = ctrl_getter.get(_dlgdef.BTN_PASTE)
        self.copiedSettings = None

    def add_listeners(self):
        self.btnReset.setActionCommand('ResetFont')
        self.btnCopy.setActionCommand('CopyFont')
        self.btnPaste.setActionCommand('PasteFont')
        for ctrl in (self.btnReset, self.btnCopy, self.btnPaste):
            ctrl.addActionListener(self)

    def handle_action_event(self, action_command):
        if action_command == 'ResetFont':
            self.resetFont()
        elif action_command == 'CopyFont':
            self.copyFont()
        elif action_command == 'PasteFont':
            self.pasteFont()
        else:
            evt_handler.raise_unknown_action(action_command)

    def resetFont(self):
        if not self.app.selected_item():
            return
        for item in self.app.fontItemList.matching_items():
            item.change = None
        self.step2Master.refresh_and_fill_list()

    def copyFont(self):
        logger.debug(util.funcName())
        self.copiedSettings = self.step2Master.read_change()

    def pasteFont(self):
        logger.debug(util.funcName())
        if self.copiedSettings is None:
            self.app.msgbox.display("First copy font settings.")
            return
        if not self.app.selected_item():
            return
        for item in self.app.fontItemList.matching_items():
            item.create_change()
            self.step2Master.copy_change_attrs(
                self.copiedSettings, item.change)
        self.step2Master.refresh_and_fill_list()


class ListFontsUsed(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ItemEventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.step2Master = step2Master
        self.list_ctrl = ctrl_getter.get(_dlgdef.LIST_FONTS_USED)

    def add_listeners(self):
        self.list_ctrl.addItemListener(self)

    def handle_item_event(self, src):
        self._read_selected_item()
        self.fill_form_for_selected_item()
        self.updateFontsList()

    def _read_selected_item(self):
        """Sets the app's selected_index."""
        try:
            self._set_app_index(
                dutil.get_selected_index(self.list_ctrl, "a file"))
        except exceptions.ChoiceProblem as exc:
            self.app.msgbox.displayExc(exc)
            self._set_app_index(-1)
            return None

    def refresh_and_fill(self):
        self.updateFontsList()
        self.fill_form_for_selected_item()

    def updateFontsList(self):
        """Redraw the list and select the same item."""
        dutil.fill_list_ctrl(
            self.list_ctrl,
            [str(fontItem) for fontItem in self.app.fontItemList])
        if self.app.fontItemList.items:
            if self._get_app_index() == -1:
                self._set_app_index(0)
            dutil.select_index(
                self.list_ctrl, self._get_app_index())

    def fill_form_for_selected_item(self):
        """Fills step 2 form data controls based on the item selected in the
        list."""
        logger.debug(util.funcName('begin'))
        fontItem = self.app.selected_item()
        if not fontItem:
            logger.debug("No fontItem selected.")
            return
        self.step2Master.fill_for_item(fontItem)

    def _set_app_index(self, index):
        self.app.fontItemList.selected_index = index

    def _get_app_index(self):
        return self.app.fontItemList.selected_index


class FontChangeControlHandler:
    """Abstract base class to handle reading and writing of FontItem change
    controls.
    Inherit it alongside one of the evt_handler.EventHandler subclasses.
    """

    def __init__(self, ctrl_getter, app):
        if self.__class__ is FontChangeControlHandler:
            # The base classes should not be instantiated.
            raise NotImplementedError
        self.ctrl_getter = ctrl_getter
        self.app = app

    def handle_action_event(self, dummy_action_command):
        self.app.update_list(self)

    def handle_item_event(self, dummy_src):
        self.app.update_list(self)

    def handle_text_event(self, dummy_src):
        self.app.update_list(self)

    #XXX: Do we need a function like this?
    #def update_change_if_ctrl_was_changed(self, fontChange):
    #    if not self.last_source:
    #        return
    #    self.read()
    #    self.last_source = None

    def update_change(self, fontChange):
        """Read form values and modify fontChange accordingly."""
        pass

    def fill_for_item(self, fontItem):
        if fontItem.change:
            self._fill_for_item_change(fontItem.change)
        else:
            self._fill_for_item_no_change(fontItem)

    def _fill_for_item_change(self, fontChange):
        """Set form values based on the fontChange values."""
        pass

    def _fill_for_item_no_change(self, fontItem):
        """Set form values based on the fontItem values."""
        pass

    def copy_change(self, change_from, change_to):
        """Set attributes of change_to based on change_from."""
        pass


class ConverterControls(FontChangeControlHandler, evt_handler.EventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.EventHandler.__init__(self)
        sampleControls = SampleControls(ctrl_getter, app)
        convName = ConvName(ctrl_getter, app, sampleControls)
        chkReverse = CheckboxReverse(ctrl_getter, app, sampleControls)
        self.controls_objects = (
            convName, chkReverse, sampleControls)

    def start_working(self):
        for controls_object in self.controls_objects:
            controls_object.start_working()

    def fill_for_item(self, fontItem):
        for controls_object in self.controls_objects:
            controls_object.fill_for_item(fontItem)


class ConvName(FontChangeControlHandler, evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, sample_controls):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ActionEventHandler.__init__(self)
        self.sample_controls = sample_controls
        self.btnSelectConv = ctrl_getter.get(_dlgdef.BTN_CHOOSE_CONV)
        self.txtConvName = ctrl_getter.get(_dlgdef.TXT_CONV_NAME)

    def add_listeners(self):
        self.btnSelectConv.setActionCommand('SelectConverter')
        self.btnSelectConv.addActionListener(self)

    def handle_action_event(self, action_command):
        self.selectConverter()
        FontChangeControlHandler.handle_action_event(self, action_command)
        self.sample_controls.fill_for_selected_item()

    def selectConverter(self):
        logger.debug(util.funcName('begin'))
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        conv_settings = None
        if fontItem.change:
            conv_settings = fontItem.change.converter
        newChange = self.app.convPool.selectConverter(conv_settings)
        fontItem.change = newChange
        self.app.convPool.cleanup_unused()
        checkboxReverse = CheckboxReverse(
            self.ctrl_getter, self.app, self.sample_controls)
        self.fill_for_item(fontItem)
        checkboxReverse.fill_for_item(fontItem)
        logger.debug(util.funcName('end'))

    def update_change(self, fontChange):
        converter = fontChange.converter
        converter.txtConvName = self.txtConvName.getText()

    def _fill_for_item_change(self, fontChange):
        self.txtConvName.setText(
            fontChange.converter.convName)

    def _fill_for_item_no_change(self, dummy_fontItem):
        self.txtConvName.setText("<No converter>")

    def copy_change(self, change_from, change_to):
        change_to.converter.convName = change_from.converter.convName


class CheckboxReverse(FontChangeControlHandler,
                      evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app, sample_controls):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.sample_controls = sample_controls
        self.chkReverse = ctrl_getter.get(_dlgdef.CHK_REVERSE)

    def add_listeners(self):
        self.chkReverse.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        self.sample_controls.fill_for_selected_item()

    def update_change(self, fontChange):
        converter = fontChange.converter
        converter.forward = (self.chkReverse.getState() == 0)

    def _fill_for_item_change(self, fontChange):
        self.chkReverse.setState(
            not fontChange.converter.forward)

    def _fill_for_item_no_change(self, dummy_fontItem):
        self.chkReverse.setState(False)

    def copy_change(self, change_from, change_to):
        change_to.converter.forward = change_from.converter.forward


class SampleControls(FontChangeControlHandler, evt_handler.EventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.EventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.samples = Samples(self.app.convPool)
        self.sampleLabels = SampleLabels(ctrl_getter, app)
        self.nextInputControls = ButtonNextInput(
            ctrl_getter, app, self.samples, self.sampleLabels)
        self.showConvControls = CheckboxShowConverter(
            ctrl_getter, app, self.nextInputControls)

    def start_working(self):
        self.sampleLabels.load_values()
        self.nextInputControls.start_working()
        self.showConvControls.start_working()

    def store_results(self):
        self.showConvControls.store_results()

    def fill_for_selected_item(self):
        fontItem = self.app.selected_item()
        if not fontItem:
            return
        self.fill_for_item(fontItem)

    def fill_for_item(self, fontItem):
        if fontItem.change:
            converter = fontItem.change.converter
            self.samples.last_settings[converter.convName] = converter
        self.samples.set_fontItem(fontItem)
        self.nextInputControls.nextInputSample()

    def change_font(self, fontItem):
        self.sampleLabels.change_font(fontItem)

    def change_font_size(self, fontSize):
        self.sampleLabels.change_font_size(fontSize)


class SampleLabels:
    """Label controls to display sample input and converted text."""

    def __init__(self, ctrl_getter, dummy_app):
        self.lblInput = ctrl_getter.get(_dlgdef.INPUT_DISPLAY)
        self.lblConverted = ctrl_getter.get(_dlgdef.CONVERTED_DISPLAY)
        self.lblSampleNum = ctrl_getter.get(_dlgdef.SAMPLE_NUM)

    def load_values(self):
        self.lblInput.setText(Samples.NO_DATA)
        self.lblSampleNum.setText("0 / 0")
        self.lblConverted.setText(Samples.NO_DATA)

    def fill_for_data(self, samples):
        logger.debug(util.funcName())
        inputSampleText = samples.inputData[samples.sampleIndex]
        self.lblInput.setText(inputSampleText)
        self.lblSampleNum.setText(
            "%d / %d" % (
                samples.sampleNum(),
                len(samples.inputData)))
        self.lblConverted.setText(samples.converted_data)

    def fill_for_no_data(self):
        logger.debug(util.funcName())
        self.lblInput.setText(Samples.NO_DATA)
        self.lblSampleNum.setText("0 / 0")
        self.lblConverted.setText(Samples.NO_DATA)

    def change_font(self, fontItem):
        """See also lingt.access.writer.textchanges.changeFont()."""
        self.lblConverted.getModel().FontName = fontItem.name
        self.lblConverted.getModel().FontNameAsian = fontItem.name

    def change_font_size(self, fontSize):
        """:param fontSize: type lingt.utils.FontSize"""
        fontSize.changeCtrlProp(self.lblConverted)
        #fontSize.changeCtrlProp(self.lblConverted, True)


class ButtonNextInput(FontChangeControlHandler,
                      evt_handler.ActionEventHandler):
    def __init__(self, ctrl_getter, app, samples, sampleLabels):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ActionEventHandler.__init__(self)
        self.samples = samples
        self.sampleLabels = sampleLabels
        self.btnNextInput = ctrl_getter.get(_dlgdef.BTN_NEXT_INPUT)

    def add_listeners(self):
        self.btnNextInput.setActionCommand('NextInput')
        self.btnNextInput.addActionListener(self)

    def handle_action_event(self, dummy_action_command):
        self.nextInputSample()

    def nextInputSample(self):
        logger.debug(util.funcName('begin'))
        if self.samples.inputData:
            if not self.samples.has_more():
                self.btnNextInput.getModel().Enabled = False
                return
            self.samples.gotoNext()
            self.btnNextInput.getModel().Enabled = (
                self.samples.has_more())
            showConvControls = CheckboxShowConverter(
                self.ctrl_getter, self.app, None)
            if showConvControls.chkShowConverted.getState() == 1:
                try:
                    self.samples.get_converted()
                except exceptions.MessageError as exc:
                    self.app.msgbox.displayExc(exc)
            self.sampleLabels.fill_for_data(self.samples)
        else:
            self.btnNextInput.getModel().Enabled = False
            self.sampleLabels.fill_for_no_data()
        logger.debug(util.funcName('end'))

    def show_sample_again(self):
        if self.samples.sampleIndex > -1:
            self.samples.sampleIndex -= 1
        self.nextInputSample()


class CheckboxShowConverter(FontChangeControlHandler,
                            evt_handler.ItemEventHandler):
    """Controls to display sample input and converted text."""

    def __init__(self, ctrl_getter, app, next_input_controls=None):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.next_input_controls = next_input_controls
        evt_handler.ItemEventHandler.__init__(self)
        self.chkShowConverted = ctrl_getter.get(_dlgdef.CHK_SHOW_CONVERTED)

    def load_values(self):
        #self.chkShowConverted.setState(
        #    userVars.getInt('DisplayConverted'))
        self.chkShowConverted.setState(False)

    def add_listeners(self):
        self.chkShowConverted.addItemListener(self)

    def handle_item_event(self, dummy_src):
        self.next_input_controls.show_sample_again()

    def store_results(self):
        displayConverted = (
            self.chkShowConverted.getState() == 1)
        self.app.userVars.store(
            'DisplayConverted', "%d" % displayConverted)


class JoinCheckboxes(evt_handler.ItemEventHandler):
    """Checkboxes that join or split the list."""

    def __init__(self, ctrl_getter, app, step2Master):
        evt_handler.ItemEventHandler.__init__(self)
        self.app = app
        self.step2Master = step2Master
        self.chkJoinFontTypes = ctrl_getter.get(_dlgdef.CHK_JOIN_FONT_TYPES)
        self.chkJoinSize = ctrl_getter.get(_dlgdef.CHK_JOIN_SIZE)
        self.chkJoinStyles = ctrl_getter.get(_dlgdef.CHK_JOIN_STYLES)

    def load_values(self):
        userVars = self.app.userVars
        self.chkJoinFontTypes.setState(userVars.getInt('JoinFontTypes'))
        self.chkJoinSize.setState(userVars.getInt('JoinSize'))
        self.chkJoinStyles.setState(userVars.getInt('JoinStyles'))

    def add_listeners(self):
        for ctrl in (
                self.chkJoinFontTypes, self.chkJoinSize, self.chkJoinStyles):
            ctrl.addItemListener(self)

    def handle_item_event(self, src):
        self.read()
        self.step2Master.refresh_and_fill_list()

    def read(self):
        self.app.fontItemList.groupFontTypes = bool(
            self.chkJoinFontTypes.getState())
        self.app.fontItemList.groupSizes = bool(
            self.chkJoinSize.getState())
        self.app.fontItemList.groupStyles = bool(
            self.chkJoinStyles.getState())


class FoundFontInfo:
    """Information about the font found.  These values are read-only."""

    def __init__(self, ctrl_getter, dummy_app):
        self.foundFonts = ctrl_getter.get(_dlgdef.FOUND_FONTS)
        self.foundFontSize = ctrl_getter.get(_dlgdef.FOUND_FONT_SIZE)

    def load_values(self):
        self.fill_for_item(FontItem())

    def fill_for_item(self, fontItem):
        foundFontNames = ""
        for title, fontName in (
                ("Standard", fontItem.nameStandard),
                ("Complex", fontItem.nameComplex),
                ("Asian", fontItem.nameAsian)):
            foundFontNames += "%s:  %s\n" % (
                theLocale.getText(title), fontName)
        self.foundFonts.setText(foundFontNames)
        if fontItem.size.isSpecified():
            fontItem.size.changeCtrlVal(self.foundFontSize)
        else:
            self.foundFontSize.setText("(Default)")


class FontNameHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.ctrl_getter = ctrl_getter
        self.app = app
        self.comboFontName = ctrl_getter.get(_dlgdef.COMBO_FONT_NAME)

    def load_values(self):
        fontNames = styles.getListOfFonts(self.app.unoObjs, addBlank=True)
        dutil.fill_list_ctrl(self.comboFontName, fontNames)

    def add_listeners(self):
        self.comboFontName.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        self.change_control_prop()
        style_type_handler = StyleTypeHandler(self.ctrl_getter, self.app)
        style_type_handler.fill('CustomFormatting')
        self.app.update_list(style_type_handler)

    def update_change(self, fontChange):
        fontChange.name = self.comboFontName.getText()
        if fontChange.name == "(None)":
            fontChange.name = None

    def _fill_for_item_no_change(self, dummy_fontItem):
        self.clear_combo_box()

    def _fill_for_item_change(self, fontChange):
        if fontChange.name and fontChange.name != "(None)":
            self.comboFontName.setText(fontChange.name)
        else:
            self.clear_combo_box()

    def copy_change(self, change_from, change_to):
        change_from.name = change_to.name

    def clear_combo_box(self):
        self.comboFontName.setText("")

    def change_control_prop(self):
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.change_font(self.app.selected_item())


class FontTypeHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.optStandard = ctrl_getter.get(_dlgdef.OPT_FONT_STANDARD)
        self.optComplex = ctrl_getter.get(_dlgdef.OPT_FONT_COMPLEX)
        self.optAsian = ctrl_getter.get(_dlgdef.OPT_FONT_ASIAN)
        self.radios = [
            dutil.RadioTuple(self.optStandard, 'Western'),
            dutil.RadioTuple(self.optComplex, 'Complex'),
            dutil.RadioTuple(self.optAsian, 'Asian')]

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def update_change(self, fontChange):
        fontChange.fontType = dutil.whichSelected(self.radios)
        #font_name_handler = FontNameHandler(self.ctrl_getter, self.app)
        #font_name_handler.read(fontChange)

    def _fill_for_item_no_change(self, fontItem):
        self.fill(fontItem.fontType)

    def _fill_for_item_change(self, fontChange):
        self.fill(fontChange.fontType)

    def copy_change(self, change_from, change_to):
        change_from.fontType = change_to.fontType

    def fill(self, fontType, *dummy_args):
        dutil.selectRadio(self.radios, fontType)


class FontSizeHandler(FontChangeControlHandler, evt_handler.TextEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.TextEventHandler.__init__(self)
        self.txtFontSize = ctrl_getter.get(_dlgdef.TXT_FONT_SIZE)

    def add_listeners(self):
        self.txtFontSize.addTextListener(self)

    def update_change(self, fontChange):
        fontChange.size = FontSize()
        fontChange.size.loadCtrl(self.txtFontSize)

    def _fill_for_item_no_change(self, fontItem):
        self.change_control_prop(fontItem.size)

    def _fill_for_item_change(self, fontChange):
        self.change_control_prop(fontChange.size)

    def copy_change(self, change_from, change_to):
        change_from.size = copy.copy(change_to.size)

    def change_control_prop(self, fontSize):
        fontSize.changeCtrlVal(self.txtFontSize)
        sampleControls = SampleControls(self.ctrl_getter, self.app)
        sampleControls.change_font_size(fontSize)


class StyleTypeHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        self.optParaStyle = ctrl_getter.get(_dlgdef.OPT_PARA_STYLE)
        self.optCharStyle = ctrl_getter.get(_dlgdef.OPT_CHAR_STYLE)
        self.optNoStyle = ctrl_getter.get(_dlgdef.OPT_NO_STYLE)  # not any style
        self.radios = [
            dutil.RadioTuple(self.optNoStyle, 'CustomFormatting'),
            dutil.RadioTuple(self.optParaStyle, 'ParaStyle'),
            dutil.RadioTuple(self.optCharStyle, 'CharStyle')]

    def add_listeners(self):
        for radio in self.radios:
            radio.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        style_name_handler = StyleNameHandler(self.ctrl_getter, self.app)
        style_name_handler.selectFontFromStyle()

    def update_change(self, fontChange):
        fontChange.styleType = dutil.whichSelected(self.radios)
        style_name_handler = StyleNameHandler(self.ctrl_getter, self.app)
        style_name_handler.update_change(fontChange)

    def _fill_for_item_change(self, fontChange):
        self.fill(fontChange.styleType)

    def _fill_for_item_no_change(self, fontItem):
        self.fill(fontItem.styleType)

    def copy_change(self, change_from, change_to):
        change_from.styleType = change_to.styleType

    def fill(self, styleType, *dummy_args):
        dutil.selectRadio(self.radios, styleType)


StyleNameTuple = collections.namedtuple(
    'StyleNameTuple', ['styleType', 'ctrl', 'styleNames'])

class StyleNameHandler(FontChangeControlHandler, evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        FontChangeControlHandler.__init__(self, ctrl_getter, app)
        evt_handler.ItemEventHandler.__init__(self)
        comboParaStyle = ctrl_getter.get(_dlgdef.COMBO_PARA_STYLE)
        comboCharStyle = ctrl_getter.get(_dlgdef.COMBO_CHAR_STYLE)
        self.styledata = [
            StyleNameTuple('Paragraph', comboParaStyle, {}),
            StyleNameTuple('Character', comboCharStyle, {})]

    def load_values(self):
        logger.debug(util.funcName())
        for data in self.styledata:
            stylesList = styles.getListOfStyles(
                data.styleType + 'Styles', self.app.unoObjs)
            data.styleNames.update(dict(stylesList))
            dispNames = tuple([dispName for dispName, name in stylesList])
            dutil.fill_list_ctrl(data.ctrl, dispNames)

    def add_listeners(self):
        for data in self.styledata:
            data.ctrl.addItemListener(self)

    def handle_item_event(self, src):
        FontChangeControlHandler.handle_item_event(self, src)
        style_type_handler = StyleTypeHandler(self.ctrl_getter, self.app)
        fontItem = self.app.selected_item()
        if fontItem.change:
            style_type_handler.fill(fontItem.change.styleType)
            self.selectFontFromStyle()
        else:
            style_type_handler.fill(fontItem.styleType)
            self.selectFontFromStyle()

    def update_change(self, fontChange):
        fontChange.styleName = ""
        for data in self.styledata:
            if evt_handler.sameName(self.last_source, data.ctrl):
                fontChange.styleType = data.styleType
                displayName = data.ctrl.getText()
                try:
                    fontChange.styleName = data.styleNames[displayName]
                except KeyError:
                    logger.warning("%s is not a known style.", displayName)
                break

    def selectFontFromStyle(self):
        """Selects the font based on the style."""
        logger.debug(util.funcName())
        fontItem = self.app.selected_item()
        fontChange = fontItem.change
        if fontChange.styleType == 'CustomFormatting':
            return
        self.readFontOfStyle(fontChange)
        font_name_handler = FontNameHandler(self.ctrl_getter, self.app)
        font_name_handler.fill_for_item(fontItem)
        font_size_handler = FontSizeHandler(self.ctrl_getter, self.app)
        font_size_handler.fill_for_item(fontItem)

    def readFontOfStyle(self, fontChange):
        """Sets fontChange.fontName and fontChange.fontSize."""
        styleFonts = styles.StyleFonts(self.app.unoObjs)
        name, size = styleFonts.getFontOfStyle(
            fontChange.styleType,
            fontChange.fontType,
            fontChange.styleName)
        fontChange.fontName = name
        fontChange.fontSize = size

    def _fill_for_item_no_change(self, fontItem):
        self.clear_combo_boxes()

    def _fill_for_item_change(self, fontChange):
        for data in self.styledata:
            if data.styleType == fontChange.styleType:
                data.ctrl.setText(fontChange.styleName)

    def clear_combo_boxes(self):
        for data in self.styledata:
            data.ctrl.setText("")

    def copy_change(self, change_from, change_to):
        change_from.styleName = change_to.styleName


class VerifyHandler(evt_handler.ItemEventHandler):
    def __init__(self, ctrl_getter, app):
        self.chkVerify = ctrl_getter.get(_dlgdef.CHK_VERIFY)
        self.app = app

    def load_values(self):
        self.chkVerify.setState(self.app.userVars.getInt('AskEachChange'))

    def store_results(self):
        self.app.askEach = (
            self.chkVerify.getState() == 1)
        self.app.userVars.store(
            'AskEachChange', "%d" % self.app.askEach)

