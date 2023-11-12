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

    # If there is no (sele), prompt the user to select an object in the console
    if 'sele' not in cmd.get_names('selections'):
        print('Please select an object to transform.')
        return
    
    # Create a new window
    dialog = QtWidgets.QDialog()

    # Load the UI
    uifile = os.path.join(os.path.dirname(__file__), 'TransformTool.ui')
    form = loadUi(uifile, dialog)

    # Get list of objects in the current session
    objectList = cmd.get_object_list(selection='(sele)')

    # callback for the "Reset" button
    def reset():
        # Reset all slider values to 0
        form.xRotationSlider.setValue(0)
        form.yRotationSlider.setValue(0)
        form.zRotationSlider.setValue(0)
        form.xTranslationSlider.setValue(0)
        form.yTranslationSlider.setValue(0)
        form.zTranslationSlider.setValue(0)
        # Set the object transform to the original transform
        for object in objectList:
            print(object)
            cmd.matrix_reset(object)

    # total rotation vector
    rotation = [0, 0, 0]

    # callback for rotation sliders
    def rotate():
        # Get the current slider values
        x = form.xRotationSlider.value()
        y = form.yRotationSlider.value()
        z = form.zRotationSlider.value()
        # Calculate the difference between the current and previous slider values
        dx = x - rotation[0]
        dy = y - rotation[1]
        dz = z - rotation[2]
        # Update the total rotation vector
        rotation[0] = x
        rotation[1] = y
        rotation[2] = z
        # Rotate the object
        for object in objectList:
            cmd.rotate('x', dx, object)
            cmd.rotate('y', dy, object)
            cmd.rotate('z', dz, object)
        
    # total translation vector
    translation = [0, 0, 0]
    # TODO: Add translation min/max value customization
    # translationLimit
    translationLimit = 10
    # callback for translation sliders
    def translate():
        # Get the current slider values
        x = form.xTranslationSlider.value()
        y = form.yTranslationSlider.value()
        z = form.zTranslationSlider.value()
        # Calculate the difference between the current and previous slider values
        dx = x - translation[0]
        dy = y - translation[1]
        dz = z - translation[2]
        # Update the total translation vector
        translation[0] = x
        translation[1] = y
        translation[2] = z
        # Translate the object
        for object in objectList:
            cmd.translate([dx, dy, dz], object)

    # Hookup callback functions for ui elements
    form.resetTransform.clicked.connect(reset)
    form.xRotationSlider.valueChanged.connect(rotate)
    form.yRotationSlider.valueChanged.connect(rotate)
    form.zRotationSlider.valueChanged.connect(rotate)
    form.xTranslationSlider.valueChanged.connect(translate)
    form.yTranslationSlider.valueChanged.connect(translate)
    form.zTranslationSlider.valueChanged.connect(translate)

    # Hookup callback for selection changes
    

    # Cleanup when the window is closed
    def cleanup():
        reset(1)
        global dialog
        dialog = None
    dialog.destroyed.connect(cleanup)

    return dialog


    
