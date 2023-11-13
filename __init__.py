#   Copyright (c)  2023  John Apt.
#   Permission is granted to copy, distribute and/or modify this document
#   under the terms of the GNU Free Documentation License, Version 1.2
#   or any later version published by the Free Software Foundation;
#   with no Invariant Sections, no Front-Cover Texts, and no Back-Cover
#   Texts.  A copy of the license is included in the section entitled "GNU
#   Free Documentation License".

# Import os
import os

def __init_plugin__(app=None):
    # add menu entry
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('Transform Tool', run_plugin_gui)

# global reference to avoid garbage collection of our dialog
dialog = None

def run_plugin_gui():
    global dialog

    if dialog is None:
        # create a new (empty) Window
        dialog = make_dialog()
    # Check if dialog was successfully created, then show it
    if dialog is not None:
        dialog.show()

def make_dialog():
    # Entrypoint into Pymol API
    from pymol import cmd

    from pymol.Qt import QtWidgets
    from pymol.Qt.utils import loadUi

    import math

    # If there are no objects in the current session, return
    if cmd.get_names() == []:
        print("No objects found, please load an object to use the Transform Tool")
        return
    
    # Create a new window
    dialog = QtWidgets.QDialog()

    # Load the UI
    uifile = os.path.join(os.path.dirname(__file__), 'TransformTool.ui')
    form = loadUi(uifile, dialog)

    # Get the list of objects in the current session
    objectList = cmd.get_names()
    # Populate selectionComboBox with the list of objects
    form.selectionComboBox.addItems(objectList)
    # Set the current selection to the first object in the list
    global currentObject
    currentObject = objectList[0]

    # callback for the "Selection" combo box
    def selectionChanged():
        resetSliders()
        # Set the current selection to the selected object
        global currentObject
        currentObject = objectList[form.selectionComboBox.currentIndex()]
        
    # callback for the "Reset" button
    def resetSliders():
        # Block the signals from the sliders so they don't trigger their callbacks
        form.xRotationSlider.blockSignals(True)
        form.yRotationSlider.blockSignals(True)
        form.zRotationSlider.blockSignals(True)
        form.xTranslationSlider.blockSignals(True)
        form.yTranslationSlider.blockSignals(True)
        form.zTranslationSlider.blockSignals(True)
        # Reset all slider values to 0
        form.xRotationSlider.setValue(0)
        form.yRotationSlider.setValue(0)
        form.zRotationSlider.setValue(0)
        form.xTranslationSlider.setValue(0)
        form.yTranslationSlider.setValue(0)
        form.zTranslationSlider.setValue(0)
        # Unblock the signals from the sliders
        form.xRotationSlider.blockSignals(False)
        form.yRotationSlider.blockSignals(False)
        form.zRotationSlider.blockSignals(False)
        form.xTranslationSlider.blockSignals(False)
        form.yTranslationSlider.blockSignals(False)
        form.zTranslationSlider.blockSignals(False)
        # Reset the total rotation and translation vectors
        global rotation
        global translation
        rotation = [0, 0, 0]
        translation = [0, 0, 0]

    # callback for the "Reset" button
    def reset():
        # Reset all slider values to 0
        resetSliders()

    # total rotation vector
    totalRotation = [0, 0, 0]

    # callback for rotation sliders
    def rotate():
        # Get the current slider values
        x = form.xRotationSlider.value()
        y = form.yRotationSlider.value()
        z = form.zRotationSlider.value()
        # Calculate the difference between the current and previous slider values
        dx = x - totalRotation[0]
        dy = y - totalRotation[1]
        dz = z - totalRotation[2]
        # Update the total rotation vector
        totalRotation[0] = x
        totalRotation[1] = y
        totalRotation[2] = z
        # Rotate the object about its center
        cmd.rotate('x', dx, currentObject, origin=totalTranslation, camera=0)
        cmd.rotate('y', dy, currentObject, origin=totalTranslation, camera=0)
        cmd.rotate('z', dz, currentObject, origin=totalTranslation, camera=0)
        
    # total translation vector
    totalTranslation = [0, 0, 0]
    # TODO: Add translation min/max value customization
    # translationLimit
    translationLimit = 100
    # callback for translation sliders
    def translate():
        # Get the current slider values
        x = form.xTranslationSlider.value() * translationLimit / 100
        y = form.yTranslationSlider.value() * translationLimit / 100
        z = form.zTranslationSlider.value() * translationLimit / 100
        # Calculate the difference between the current and previous slider values
        dx = x - totalTranslation[0]
        dy = y - totalTranslation[1]
        dz = z - totalTranslation[2]
        # Update the total translation vector
        totalTranslation[0] = x
        totalTranslation[1] = y
        totalTranslation[2] = z
        # Translate the object
        cmd.translate([dx, dy, dz], currentObject, camera=0)

    # Hookup callback functions for ui elements
    form.resetTransform.clicked.connect(reset)
    form.xRotationSlider.valueChanged.connect(rotate)
    form.yRotationSlider.valueChanged.connect(rotate)
    form.zRotationSlider.valueChanged.connect(rotate)
    form.xTranslationSlider.valueChanged.connect(translate)
    form.yTranslationSlider.valueChanged.connect(translate)
    form.zTranslationSlider.valueChanged.connect(translate)
    form.selectionComboBox.currentTextChanged.connect(selectionChanged)

    # Cleanup when the window is closed
    def cleanup():
        resetSliders()
        print("Transform Tool closed")
        global dialog
        dialog = None

    # Hookup cleanup function
    dialog.finished.connect(cleanup)

    return dialog


    
