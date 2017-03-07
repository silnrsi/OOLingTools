# -*- coding: Latin-1 -*-
#
# This file created October 23, 2010 by Jim Kornelsen
#
# 23-Apr-13 JDK  Fix complaint about no handler for logging.
# 27-Apr-13 JDK  Make sure a writer doc is open.
# 13-May-13 JDK  Allow component context from argument as well as socket.
# 15-Sep-15 JDK  Output file encoded for unicode.
# 28-Sep-15 JDK  Load tests from modules rather than classes.
# 23-May-16 JDK  Added functions to run individual modules.

"""
This file runs a suite of automated tests all together.
Otherwise you can run each test individually from its file.

See build/README_build.txt for instructions to run this code.
"""
import io
import os
import unittest
# pylint: disable=import-error
import uno
# pylint: enable=import-error

from lingttest.utils import testutil

from lingttest.access import ex_updater_test
from lingttest.access import search_test
from lingttest.access import tables_test
from lingttest.access import textchanges_test
from lingttest.access import uservars_test
from lingttest.access import xml_readers_test
from lingttest.app import fileitemlist_test
from lingttest.app import spellingchecks_test
from lingttest.app import convpool_test
from lingttest.app import visual_test_grammar
from lingttest.app import visual_test_phonology
from lingttest.topdown import abbrevs_test
from lingttest.topdown import dataconv_test
from lingttest.topdown import grammar_test
from lingttest.topdown import phonology_test
from lingttest.topdown import step_through_list
from lingttest.ui import dlg_dataconv_test
from lingttest.ui import dlg_gramsettings_test
from lingttest.ui import messagebox_test
from lingttest.ui import wordlistfile_test

from lingt.utils import util


def get_master_suite():
    masterSuite = unittest.TestSuite()
    for module in (
            ex_updater_test,
            tables_test,
            search_test,
            textchanges_test,
            uservars_test,
            xml_readers_test,

            fileitemlist_test,
            spellingchecks_test,
            convpool_test,

            messagebox_test,
            dlg_gramsettings_test,
            dlg_dataconv_test,
            wordlistfile_test,

            abbrevs_test,
            phonology_test,
            grammar_test,
            dataconv_test,
            step_through_list,
        ):
        masterSuite.addTest(module.getSuite())
    # Uncomment to run only this test.
    #masterSuite = visual_test_phonology.getSuite()
    return masterSuite


def run_to_outfile(suite):
    run_suite(suite, True)

def run_to_stdout(suite):
    run_suite(suite, False)

def run_suite(suite, outputToFile):

    ## Make sure a writer document is open

    ctx = testutil.stored.getContext()
    unoObjs = util.UnoObjs(ctx, loadDocObjs=False)
    if len(unoObjs.getOpenDocs()) == 0:
        unoObjs.desktop.loadComponentFromURL(
            "private:factory/swriter", "_blank", 0, ())

    ## Load and run the suite

    if outputToFile:
        run_suite_to_outfile(suite)
    else:
        unittest.TextTestRunner(verbosity=2).run(suite)

    unoObjs = testutil.unoObjsForCurrentDoc()
    oVC = unoObjs.viewcursor
    oVC.gotoEnd(False)
    oVC.getText().insertString(oVC, "Testing finished.\n", False)
    testutil.restoreMsgboxDisplay()


def run_suite_to_outfile(suite):
    outfilepath = os.path.join(util.BASE_FOLDER, "testResults.txt")
    outfile = io.open(outfilepath, mode='w', encoding='UTF8')
    #outfile = open(outfilepath, mode='w')
    outfile.write("Calling TextTestRunner...\n")
    outfile.flush()
    unittest.TextTestRunner(stream=outfile, verbosity=2).run(suite)
    outfile.close()


if __name__ == '__main__':
    testutil.stored.getContext()
    run_to_stdout(get_master_suite())


def aaa_run_all_tests():
    testutil.stored.ctx = uno.getComponentContext()
    run_to_outfile(get_master_suite())


def run_module_suite(module):
    """Run tests from a single module only."""
    testutil.stored.ctx = uno.getComponentContext()
    run_to_outfile(module.getSuite())


def run_ex_updater_test():
    run_module_suite(ex_updater_test)

def run_search_test():
    run_module_suite(search_test)

def run_tables_test():
    run_module_suite(tables_test)

def run_textchanges_test():
    run_module_suite(textchanges_test)

def run_uservars_test():
    run_module_suite(uservars_test)

def run_xml_readers_test():
    run_module_suite(xml_readers_test)

def run_fileitemlist_test():
    run_module_suite(fileitemlist_test)

def run_spellingchecks_test():
    run_module_suite(spellingchecks_test)

def run_convpool_test():
    run_module_suite(convpool_test)

def run_visual_test_grammar():
    run_module_suite(visual_test_grammar)

def run_visual_test_phonology():
    run_module_suite(visual_test_phonology)

def run_abbrevs_test():
    run_module_suite(abbrevs_test)

def run_dataconv_test():
    run_module_suite(dataconv_test)

def run_grammar_test():
    run_module_suite(grammar_test)

def run_phonology_test():
    run_module_suite(phonology_test)

def run_step_through_list():
    run_module_suite(step_through_list)

def run_dlg_dataconv_test():
    run_module_suite(dlg_dataconv_test)

def run_dlg_gramsettings_test():
    run_module_suite(dlg_gramsettings_test)

def run_messagebox_test():
    run_module_suite(messagebox_test)

def run_wordlistfile_test():
    run_module_suite(wordlistfile_test)


# Functions that can be called from Tools -> Macros -> Run Macro.
g_exportedScripts = (
    aaa_run_all_tests,
    run_ex_updater_test,
    run_search_test,
    run_tables_test,
    run_textchanges_test,
    run_uservars_test,
    run_xml_readers_test,
    run_fileitemlist_test,
    run_spellingchecks_test,
    run_convpool_test,
    run_visual_test_grammar,
    run_visual_test_phonology,
    run_abbrevs_test,
    run_dataconv_test,
    run_grammar_test,
    run_phonology_test,
    run_step_through_list,
    run_dlg_dataconv_test,
    run_dlg_gramsettings_test,
    run_messagebox_test,
    run_wordlistfile_test,
    )
