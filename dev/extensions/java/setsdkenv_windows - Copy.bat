rem @echo off
REM This script sets all environment variables, which
REM are necessary for building the examples of the Office Development Kit.
REM The Script was developed for the operating systems Windows.
REM The SDK name
REM Example: set OO_SDK_NAME=libreoffice3.4_sdk
set OO_SDK_NAME=libreoffice5.0_sdk

REM Installation directory of the Software Development Kit.
REM Example: set OO_SDK_HOME=C:\Program Files\LibreOffice 3\sdk
set OO_SDK_HOME=%ProgramFiles(x86)%\LibreOffice 5\sdk

REM Office installation directory.
REM Example: set OFFICE_HOME=C:\Program Files\LibreOffice 3
set OFFICE_HOME=%ProgramFiles(x86)%\LibreOffice 5

REM Directory of the make command.
REM Example: set OO_SDK_MAKE_HOME=D:\NextGenerationMake\make
set OO_SDK_MAKE_HOME=C:\MinGW\bin

REM Directory of the zip tool.
REM Example: set OO_SDK_ZIP_HOME=D:\infozip\bin
set OO_SDK_ZIP_HOME=C:\Program Files\infozip

REM Directory of the cat tool.
REM Example: set OO_SDK_CAT_HOME=C:\UnxUtils\usr\local\wbin
set OO_SDK_CAT_HOME=%ProgramFiles(x86)%\UnxUtils\usr\local\wbin

REM Directory of the sed tool.
REM Example: set OO_SDK_SED_HOME=C:\UnxUtils\usr\local\wbin
set OO_SDK_SED_HOME=%ProgramFiles(x86)%\UnxUtils\usr\local\wbin

REM Directory of the C++ compiler.
REM Example:set OO_SDK_CPP_HOME=C:\Program Files\Microsoft Visual Studio 9.0\VC\bin
set OO_SDK_CPP_HOME=
set CPP_MANIFEST=
set CPP_WINDOWS_SDK=

REM Directory of the C# and VB.NET compilers.
REM Example:set OO_SDK_CLI_HOME=C:\WINXP\Microsoft.NET\Framework\v1.0.3705
set OO_SDK_CLI_HOME=C:\Windows\Microsoft.NET\Framework64\v2.0.50727

REM Java SDK installation directory.
REM Example: set OO_SDK_JAVA_HOME=C:\Program Files\Java\jdk1.6.0_05
set OO_SDK_JAVA_HOME=C:\Program Files\Java\jdk1.8.0_60

REM Special output directory
REM Example: set OO_SDK_OUT=C:\libreoffice5.0_sdk
set OO_SDK_OUT=c:\libreoffice5.0_sdk

REM Automatic deployment
REM Example: set SDK_AUTO_DEPLOYMENT=YES
set SDK_AUTO_DEPLOYMENT=YES

REM Check installation path for the Office Development Kit.
if not defined OO_SDK_HOME (
   echo Error: the variable OO_SDK_HOME is missing!
   goto :error
 )

REM Check installation path for the office.
REM if not defined OFFICE_HOME (
REM    echo Error: the variable OFFICE_HOME is missing!
REM    goto :error
REM  )

REM Check installation path for GNU make.
if not defined OO_SDK_MAKE_HOME (
   echo Error: the variable OO_SDK_MAKE_HOME is missing!
   goto :error
 )

REM Check installation path for the zip tool.
if not defined OO_SDK_ZIP_HOME (
   echo Error: the variable OO_SDK_ZIP_HOME is missing!
   goto :error
 )

REM Check installation path for the cat tool.
if not defined OO_SDK_CAT_HOME (
   echo Error: the variable OO_SDK_CAT_HOME is missing!
   goto :error
 )

REM Check installation path for the sed tool.
if not defined OO_SDK_SED_HOME (
   echo Error: the variable OO_SDK_SED_HOME is missing!
   goto :error
 )

REM Set library path. 
set "LIB=%OO_SDK_HOME%\lib;%LIB%"
if not defined CPP_WINDOWS_SDK goto skip1
set "LIB=%LIB%;%CPP_WINDOWS_SDK%\lib"
:skip1

REM Set office program path.
if not defined OFFICE_HOME goto skip2
set OFFICE_PROGRAM_PATH=%OFFICE_HOME%\program
:skip2

REM Set UNO path, necessary to ensure that the cpp examples using the
REM new UNO bootstrap mechanism use the configured office installation
REM (only set when using an Office).
if not defined OFFICE_HOME goto skip3
set UNO_PATH=%OFFICE_PROGRAM_PATH%
:skip3

set OO_SDK_URE_BIN_DIR=%OFFICE_PROGRAM_PATH%
set OO_SDK_URE_LIB_DIR=%OFFICE_PROGRAM_PATH%
set OO_SDK_URE_JAVA_DIR=%OFFICE_PROGRAM_PATH%\classes
set OO_SDK_OFFICE_BIN_DIR=%OFFICE_PROGRAM_PATH%
set OO_SDK_OFFICE_LIB_DIR=%OFFICE_PROGRAM_PATH%
set OO_SDK_OFFICE_JAVA_DIR=%OFFICE_PROGRAM_PATH%\classes

REM Set classpath
set CLASSPATH=%OO_SDK_URE_JAVA_DIR%\juh.jar;%OO_SDK_URE_JAVA_DIR%\jurt.jar;%OO_SDK_URE_JAVA_DIR%\ridl.jar;%OO_SDK_URE_JAVA_DIR%\unoloader.jar;%OO_SDK_OFFICE_JAVA_DIR%\unoil.jar
REM if defined OFFICE_HOME (
REM     set CLASSPATH=%CLASSPATH%;%OO_SDK_OFFICE_JAVA_DIR%\unoil.jar
REM  )

REM Add directory of the SDK tools to the path.
set PATH=%OO_SDK_HOME%\bin;%OO_SDK_URE_BIN_DIR%;%OO_SDK_OFFICE_BIN_DIR%;%OO_SDK_HOME%\WINexample.out\bin;%PATH%

REM Set PATH appropriate to the output directory
if defined OO_SDK_OUT set PATH=%OO_SDK_OUT%\WINexample.out\bin;%PATH%
if not defined OO_SDK_OUT set PATH=%OO_SDK_HOME%\WINexample.out\bin;%PATH%

REM Add directory of the command make to the path, if necessary.
if defined OO_SDK_MAKE_HOME set PATH=%OO_SDK_MAKE_HOME%;%PATH%

REM Add directory of the zip tool to the path, if necessary.
if defined OO_SDK_ZIP_HOME set PATH=%OO_SDK_ZIP_HOME%;%PATH%

REM Add directory of the cat tool to the path, if necessary.
if defined OO_SDK_CAT_HOME set PATH=%OO_SDK_CAT_HOME%;%PATH%

REM Add directory of the sed tool to the path, if necessary.
if defined OO_SDK_SED_HOME set PATH=%OO_SDK_SED_HOME%;%PATH%

REM Add directory of the C++ compiler to the path, if necessary.
if defined OO_SDK_CPP_HOME set PATH=%OO_SDK_CPP_HOME%;%PATH%

REM Add directory of the Win SDK to the path, if necessary.
if defined CPP_WINDOWS_SDK set PATH=%CPP_WINDOWS_SDK%\bin;%PATH%
if defined CPP_WINDOWS_SDK set INCLUDE=%CPP_WINDOWS_SDK%\Include;%INCLUDE%
REM Add directory of the C# and VB.NET compilers to the path, if necessary.
if defined OO_SDK_CLI_HOME set PATH=%OO_SDK_CLI_HOME%;%PATH%

REM Add directory of the Java tools to the path, if necessary.
if defined OO_SDK_JAVA_HOME set PATH=%OO_SDK_JAVA_HOME%\bin;%OO_SDK_JAVA_HOME%\jre\bin;%PATH%

REM Set environment for C++ compiler tools, if necessary.
if defined OO_SDK_CPP_HOME call "%OO_SDK_CPP_HOME%\VCVARS32.bat"

REM Set title to identify the prepared shell.
title Shell prepared for SDK

REM Prepare shell with all necessary environment variables.
echo.
echo  ******************************************************************
echo  *
echo  * SDK environment is prepared for Windows
echo  *
echo  * SDK = %OO_SDK_HOME%
echo  * Office = %OFFICE_HOME%
echo  * Make = %OO_SDK_MAKE_HOME%
echo  * Zip = %OO_SDK_ZIP_HOME%
echo  * cat = %OO_SDK_CAT_HOME%
echo  * sed = %OO_SDK_SED_HOME%
echo  * C++ Compiler = %OO_SDK_CPP_HOME%
echo  * C# and VB.NET compilers = %OO_SDK_CLI_HOME%
echo  * Java = %OO_SDK_JAVA_HOME%
echo  * Special Output directory = %OO_SDK_OUT%
echo  * Auto deployment = %SDK_AUTO_DEPLOYMENT%
echo  *
echo  ******************************************************************
echo.
goto end

 :error
Error: Please insert the necessary environment variables into the batch file.

 :end