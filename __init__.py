#   Copyright (c)  2023  John Apt.
#   Permission is granted to copy, distribute and/or modify this document
#   under the terms of the GNU Free Documentation License, Version 1.2
#   or any later version published by the Free Software Foundation;
#   with no Invariant Sections, no Front-Cover Texts, and no Back-Cover
#   Texts.  A copy of the license is included in the section entitled "GNU
#   Free Documentation License".

# Import os
import os

# Entrypoint into Pymol API
from pymol import cmd

# Import Qt modules
from PyQt5 import QtCore, QtGui, QtWidgets

def __init_plugin__(app=None):
    # add menu entry
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('Transform Tool', run_plugin_gui)

# global reference to avoid garbage collection
dialog = None
ui = None
objectList = None
transformToolInstance = None

def run_plugin_gui():
    global dialog
    global ui
    global objectList
    global transformToolInstance
    # Check if cmd.get_names() is empty
    if cmd.get_names() == []:
        print("No objects found, please load an object to use the Transform Tool")
        return
    # Check if dialog already exists, if not create a new one
    if dialog is None:
        # create a new Window using the Ui_Form class
        dialog = QtWidgets.QDialog()
        ui = Ui_Form()
        ui.setupUi(dialog)
        # Instantiate pymolObjectList
        objectList = PymolObjectList() 
        # Instantiate transformTool
        transformToolInstance = TransformTool(objectList, ui)
    # Check if dialog was successfully created, then show it
    if dialog is not None:
        dialog.show()

class PymolObject:
    def __init__(self, name):
        self.name = name
        self.TotalRotation = [0, 0, 0]
        self.TotalTranslation = [0, 0, 0]
        self.undoStack = []
        self.redoStack = []
    
    # Rotate action
    def rotate(self, axis, angle):
        # Rotate the object about its center
        CoM = cmd.centerofmass(self.name)
        cmd.rotate(axis, angle, self.name, origin=CoM, camera=0)
        # Update the total rotation vector
        if axis == "x":
            self.TotalRotation[0] += angle
        elif axis == "y":
            self.TotalRotation[1] += angle
        elif axis == "z":
            self.TotalRotation[2] += angle
        # Add the action to the undo stack
        self.undoStack.append(["rotate", axis, -angle])
    
    # Translate action
    def translate(self, vector):
        # Translate the object
        cmd.translate(vector, self.name, camera=0)
        # Update the total translation vector
        self.TotalTranslation = [self.TotalTranslation[0] + vector[0], self.TotalTranslation[1] + vector[1], self.TotalTranslation[2] + vector[2]]
        # Add the action to the undo stack
        self.undoStack.append(["translate", [-vector[0], -vector[1], -vector[2]]])

    # Undo action
    def undo(self):
        # Check if the undo stack is empty
        if self.undoStack == []:
            return
        # Get the last action from the undo stack
        action = self.undoStack.pop()
        # Perform the inverse action, then add it to the redo stack
        if action[0] == "rotate":
            self.rotate(action[1], action[2])
            self.undoStack.pop()
        elif action[0] == "translate":
            self.translate(action[1])
            self.undoStack.pop()
        # Add the inverse action to the redo stack
        if action[0] == "rotate":
            self.redoStack.append(["rotate", action[1], -action[2]])
        elif action[0] == "translate":
            self.redoStack.append(["translate", [-action[1][0], -action[1][1], -action[1][2]]])
    
    # Redo action
    def redo(self):
        # Check if the redo stack is empty
        if self.redoStack == []:
            return
        # Get the last action from the redo stack
        action = self.redoStack.pop()
        # Perform the action
        if action[0] == "rotate":
            self.rotate(action[1], action[2])
        elif action[0] == "translate":
            self.translate(action[1])
    # Reset action
    def reset(self):
        # Reset the object by going through the entire undo stack
        while self.undoStack != []:
            self.undo()
        # Clear the undo and redo stacks
        self.undoStack = []
        self.redoStack = []

class PymolObjectList:
    def __init__(self):
        # Create a new list. Each object in the list should contain an undo stack
        self.list = []
        # Call update to populate the list
        self.update()

    # Update the list of objects
    def update(self):
        # Get the list of objects in the current session, ignoring any objects named "Axes"
        for object in cmd.get_names():
            if object != "Axes":
                # If the object is not already in the list, add it
                if object not in [object.name for object in self.list]:
                    self.list.append(PymolObject(object))

class TransformTool:
    def __init__(self, pymolObjectList, ui):
        self.pymolObjectList = pymolObjectList
        self.ui = ui
        # Current object is a reference to the PymolObject selected in the selectionComboBox
        self.currentObject = None
        self.translationLimit = self.ui.positionSpinBox.value()
        self.updateSelectionList()

        # Hookup callback functions for ui elements
        self.ui.xRotationSlider.valueChanged.connect(self.rotate)
        self.ui.yRotationSlider.valueChanged.connect(self.rotate)
        self.ui.zRotationSlider.valueChanged.connect(self.rotate)
        self.ui.xTranslationSlider.valueChanged.connect(self.translate)
        self.ui.yTranslationSlider.valueChanged.connect(self.translate)
        self.ui.zTranslationSlider.valueChanged.connect(self.translate)
        self.ui.selectionComboBox.activated.connect(self.updateSelectionList)
        self.ui.selectionComboBox.currentTextChanged.connect(self.changeSelection)
        self.ui.positionSpinBox.valueChanged.connect(self.positionSpinBoxChanged)
        self.ui.resetButton.clicked.connect(self.reset)
        self.ui.undoButton.clicked.connect(self.undo)
        self.ui.redoButton.clicked.connect(self.redo)
    
    # Update the list of objects and the selectionComboBox
    def updateSelectionList(self):
        # Update the list of objects
        self.pymolObjectList.update()
        # Populate selectionComboBox with the list of objects
        self.ui.selectionComboBox.clear()
        self.ui.selectionComboBox.addItems([object.name for object in self.pymolObjectList.list])
        # Set the currentObject to the object with the same name as the current selection
        for object in self.pymolObjectList.list:
            if object.name == self.ui.selectionComboBox.currentText():
                self.currentObject = object
                print(self.currentObject.name)
        # If the current selection is not in the list, set the currentObject to the first object in the list
        if self.currentObject == None:
            self.currentObject = self.pymolObjectList.list[0]
        self.updateSliders()
    
    # Change selectionComboBox to new selection
    def changeSelection(self):
        # Set the selectionComboBox to the currentText
        self.ui.selectionComboBox.setCurrentText(self.currentObject.name)
        
        # Set the currentObject to the object with the same name as the current selection
        for object in self.pymolObjectList.list:
            if object.name == self.ui.selectionComboBox.currentText():
                self.currentObject = object
        # Update the sliders
        self.updateSliders()

    def blockSliderSignals(self, boolVal):
        # set the blockSignals property of each slider to the value of boolVal
        self.ui.xRotationSlider.blockSignals(boolVal)
        self.ui.yRotationSlider.blockSignals(boolVal)
        self.ui.zRotationSlider.blockSignals(boolVal)
        self.ui.xTranslationSlider.blockSignals(boolVal)
        self.ui.yTranslationSlider.blockSignals(boolVal)
        self.ui.zTranslationSlider.blockSignals(boolVal)
    
    # Update the sliders to match the current object's total rotation and translation
    def updateSliders(self):
        # Block the signals from the sliders so they don't trigger their callbacks
        self.blockSliderSignals(True)
        # Reset all slider values to 0
        self.ui.xRotationSlider.setValue(self.currentObject.TotalRotation[0])
        self.ui.yRotationSlider.setValue(self.currentObject.TotalRotation[1])
        self.ui.zRotationSlider.setValue(self.currentObject.TotalRotation[2])
        self.ui.xTranslationSlider.setValue(self.currentObject.TotalTranslation[0] * 100 / self.translationLimit)
        self.ui.yTranslationSlider.setValue(self.currentObject.TotalTranslation[1] * 100 / self.translationLimit)
        self.ui.zTranslationSlider.setValue(self.currentObject.TotalTranslation[2] * 100 / self.translationLimit)
        # Unblock the signals from the sliders
        self.blockSliderSignals(False)

    # callback for the "Position" spin box
    def positionSpinBoxChanged(self):
        # Update the translationLimit
        self.translationLimit = self.ui.positionSpinBox.value()
        # lock the signals from the translation sliders
        self.blockSliderSignals(True)
        # Update the translation sliders
        self.ui.xTranslationSlider.setValue(self.ui.xTranslationSlider.value())
        self.ui.yTranslationSlider.setValue(self.ui.yTranslationSlider.value())
        self.ui.zTranslationSlider.setValue(self.ui.zTranslationSlider.value())
        # unlock the signals from the translation sliders
        self.blockSliderSignals(False)
    
    # callback for rotation sliders
    def rotate(self):
        # Get the current slider values
        x = self.ui.xRotationSlider.value()
        y = self.ui.yRotationSlider.value()
        z = self.ui.zRotationSlider.value()
        # Calculate the difference between the current and previous slider values
        dx = x - self.currentObject.TotalRotation[0]
        dy = y - self.currentObject.TotalRotation[1]
        dz = z - self.currentObject.TotalRotation[2]
        # Rotate the object for each non-zero difference
        if dx != 0:
            self.currentObject.rotate("x", dx)
        if dy != 0:
            self.currentObject.rotate("y", dy)
        if dz != 0:
            self.currentObject.rotate("z", dz)
    
    # callback for translation sliders
    def translate(self):
        # Get the current slider values
        x = self.ui.xTranslationSlider.value() * self.translationLimit / 100
        y = self.ui.yTranslationSlider.value() * self.translationLimit / 100
        z = self.ui.zTranslationSlider.value() * self.translationLimit / 100
        # Calculate the difference between the current and previous slider values
        dx = x - self.currentObject.TotalTranslation[0]
        dy = y - self.currentObject.TotalTranslation[1]
        dz = z - self.currentObject.TotalTranslation[2]
        # Translate the object
        self.currentObject.translate([dx, dy, dz])
    
    # callback for the "Reset" button
    def reset(self):
        # Reset the object
        self.currentObject.reset()
        # Update the sliders
        self.updateSliders()
    
    # callback for the "Undo" button
    def undo(self):
        # Undo the last action
        self.currentObject.undo()
        # Update the sliders
        self.updateSliders()
    
    # callback for the "Redo" button
    def redo(self):
        print("redo")
        # Redo the last action
        self.currentObject.redo()
        # Update the sliders
        self.updateSliders()


# Ui_Form. This is generated code made by converting the .ui file to .py using pyuic5
# If you want to make changes to the UI, make them in the .ui file using Qt Designer,
# then convert the .ui file to .py using pyuic5, then replace the Ui_Form class below.
class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(365, 186)
        self.gridLayoutWidget = QtWidgets.QWidget(Form)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 10, 341, 111))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.label_5 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 1, 2, 1, 1)
        self.zTranslationSlider = QtWidgets.QSlider(self.gridLayoutWidget)
        self.zTranslationSlider.setAutoFillBackground(False)
        self.zTranslationSlider.setMinimum(-100)
        self.zTranslationSlider.setMaximum(100)
        self.zTranslationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.zTranslationSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.zTranslationSlider.setTickInterval(0)
        self.zTranslationSlider.setObjectName("zTranslationSlider")
        self.gridLayout.addWidget(self.zTranslationSlider, 4, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 3, 0, 1, 1)
        self.yTranslationSlider = QtWidgets.QSlider(self.gridLayoutWidget)
        self.yTranslationSlider.setAutoFillBackground(False)
        self.yTranslationSlider.setMinimum(-100)
        self.yTranslationSlider.setMaximum(100)
        self.yTranslationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.yTranslationSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.yTranslationSlider.setTickInterval(0)
        self.yTranslationSlider.setObjectName("yTranslationSlider")
        self.gridLayout.addWidget(self.yTranslationSlider, 3, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.yRotationSlider = QtWidgets.QSlider(self.gridLayoutWidget)
        self.yRotationSlider.setAutoFillBackground(False)
        self.yRotationSlider.setMinimum(-180)
        self.yRotationSlider.setMaximum(180)
        self.yRotationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.yRotationSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.yRotationSlider.setTickInterval(0)
        self.yRotationSlider.setObjectName("yRotationSlider")
        self.gridLayout.addWidget(self.yRotationSlider, 3, 2, 1, 1)
        self.xRotationSlider = QtWidgets.QSlider(self.gridLayoutWidget)
        self.xRotationSlider.setAutoFillBackground(False)
        self.xRotationSlider.setMinimum(-180)
        self.xRotationSlider.setMaximum(180)
        self.xRotationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.xRotationSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.xRotationSlider.setTickInterval(0)
        self.xRotationSlider.setObjectName("xRotationSlider")
        self.gridLayout.addWidget(self.xRotationSlider, 2, 2, 1, 1)
        self.zRotationSlider = QtWidgets.QSlider(self.gridLayoutWidget)
        self.zRotationSlider.setAutoFillBackground(False)
        self.zRotationSlider.setMinimum(-180)
        self.zRotationSlider.setMaximum(180)
        self.zRotationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.zRotationSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.zRotationSlider.setTickInterval(0)
        self.zRotationSlider.setObjectName("zRotationSlider")
        self.gridLayout.addWidget(self.zRotationSlider, 4, 2, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 1, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 4, 0, 1, 1)
        self.xTranslationSlider = QtWidgets.QSlider(self.gridLayoutWidget)
        self.xTranslationSlider.setAutoFillBackground(False)
        self.xTranslationSlider.setMinimum(-100)
        self.xTranslationSlider.setMaximum(100)
        self.xTranslationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.xTranslationSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.xTranslationSlider.setTickInterval(0)
        self.xTranslationSlider.setObjectName("xTranslationSlider")
        self.gridLayout.addWidget(self.xTranslationSlider, 2, 1, 1, 1)
        self.selectionComboBox = QtWidgets.QComboBox(Form)
        self.selectionComboBox.setGeometry(QtCore.QRect(190, 130, 161, 22))
        self.selectionComboBox.setInsertPolicy(QtWidgets.QComboBox.InsertAlphabetically)
        self.selectionComboBox.setObjectName("selectionComboBox")
        self.label = QtWidgets.QLabel(Form)
        self.label.setGeometry(QtCore.QRect(10, 130, 121, 21))
        self.label.setObjectName("label")
        self.positionSpinBox = QtWidgets.QSpinBox(Form)
        self.positionSpinBox.setGeometry(QtCore.QRect(140, 130, 41, 22))
        self.positionSpinBox.setMinimum(1)
        self.positionSpinBox.setMaximum(100)
        self.positionSpinBox.setProperty("value", 10)
        self.positionSpinBox.setObjectName("positionSpinBox")
        self.resetButton = QtWidgets.QPushButton(Form)
        self.resetButton.setGeometry(QtCore.QRect(300, 160, 56, 17))
        self.resetButton.setObjectName("resetButton")
        self.redoButton = QtWidgets.QPushButton(Form)
        self.redoButton.setGeometry(QtCore.QRect(240, 160, 56, 17))
        self.redoButton.setObjectName("redoButton")
        self.undoButton = QtWidgets.QPushButton(Form)
        self.undoButton.setGeometry(QtCore.QRect(180, 160, 56, 17))
        self.undoButton.setObjectName("undoButton")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Transform Tool"))
        self.label_5.setText(_translate("Form", "Rotation (Degrees)"))
        self.label_7.setText(_translate("Form", "Y"))
        self.label_4.setText(_translate("Form", "X"))
        self.label_6.setText(_translate("Form", "Position (Angstroms)"))
        self.label_8.setText(_translate("Form", "Z"))
        self.label.setText(_translate("Form", "Position slider min/max:"))
        self.resetButton.setText(_translate("Form", "Reset"))
        self.redoButton.setText(_translate("Form", "Redo"))
        self.undoButton.setText(_translate("Form", "Undo"))






# Old code, refactoring in progress
# def make_dialog():
#     # Entrypoint into Pymol API
#     from pymol import cmd

#     from pymol.Qt import QtWidgets
#     from pymol.Qt.utils import loadUi

#     import math

#     # If there are no objects in the current session, return
#     if cmd.get_names() == []:
#         print("No objects found, please load an object to use the Transform Tool")
#         return
    
#     # Create a new window
#     dialog = QtWidgets.QDialog()

#     # Load the UI
#     uifile = os.path.join(os.path.dirname(__file__), 'TransformTool.ui')
#     form = loadUi(uifile, dialog)

#     # Get the list of objects in the current session
#     objectList = cmd.get_names()
#     # Populate selectionComboBox with the list of objects
#     form.selectionComboBox.addItems(objectList)
#     # Set the current selection to the first object in the list
#     global currentObject
#     currentObject = objectList[0]

#     # callback for the "Selection" combo box
#     def selectionChanged():
#         resetSliders()
#         # Set the current selection to the selected object
#         global currentObject
#         currentObject = objectList[form.selectionComboBox.currentIndex()]
        
#     # callback for the "Reset" button
#     def resetSliders():
#         # Block the signals from the sliders so they don't trigger their callbacks
#         form.xRotationSlider.blockSignals(True)
#         form.yRotationSlider.blockSignals(True)
#         form.zRotationSlider.blockSignals(True)
#         form.xTranslationSlider.blockSignals(True)
#         form.yTranslationSlider.blockSignals(True)
#         form.zTranslationSlider.blockSignals(True)
#         # Reset all slider values to 0
#         form.xRotationSlider.setValue(0)
#         form.yRotationSlider.setValue(0)
#         form.zRotationSlider.setValue(0)
#         form.xTranslationSlider.setValue(0)
#         form.yTranslationSlider.setValue(0)
#         form.zTranslationSlider.setValue(0)
#         # Unblock the signals from the sliders
#         form.xRotationSlider.blockSignals(False)
#         form.yRotationSlider.blockSignals(False)
#         form.zRotationSlider.blockSignals(False)
#         form.xTranslationSlider.blockSignals(False)
#         form.yTranslationSlider.blockSignals(False)
#         form.zTranslationSlider.blockSignals(False)
#         # Reset the total rotation and translation vectors
#         global rotation
#         global translation
#         rotation = [0, 0, 0]
#         translation = [0, 0, 0]
    
#     # TODO: Implement reset button
#     # callback for the "Reset" button
#     # def reset():
#     #     # Reset all slider values to 0
#     #     resetSliders()

#     # total rotation vector
#     global totalRotation
#     totalRotation = [0, 0, 0]

#     # callback for rotation sliders
#     def rotate():
#         # Get the current slider values
#         x = form.xRotationSlider.value()
#         y = form.yRotationSlider.value()
#         z = form.zRotationSlider.value()
#         # Calculate the difference between the current and previous slider values
#         dx = x - totalRotation[0]
#         dy = y - totalRotation[1]
#         dz = z - totalRotation[2]
#         # Update the total rotation vector
#         totalRotation[0] = x
#         totalRotation[1] = y
#         totalRotation[2] = z
#         # Rotate the object about its center
#         CoM = cmd.centerofmass(currentObject)
        
#         cmd.rotate('x', dx, currentObject, origin=CoM, camera=0)
#         cmd.rotate('y', dy, currentObject, origin=CoM, camera=0)
#         cmd.rotate('z', dz, currentObject, origin=CoM, camera=0)
        
#     # total translation vector
#     global totalTranslation
#     totalTranslation = [0, 0, 0]
#     # translationLimit
#     global translationLimit
#     translationLimit = form.positionSpinBox.value()

#     # callback for the "Position" spin box
#     def positionSpinBoxChanged():
#         # Update the translationLimit
#         global translationLimit
#         translationLimit = form.positionSpinBox.value()
#         # lock the signals from the translation sliders
#         form.xTranslationSlider.blockSignals(True)
#         form.yTranslationSlider.blockSignals(True)
#         form.zTranslationSlider.blockSignals(True)
#         # Update the translation sliders
#         form.xTranslationSlider.setValue(form.xTranslationSlider.value())
#         form.yTranslationSlider.setValue(form.yTranslationSlider.value())
#         form.zTranslationSlider.setValue(form.zTranslationSlider.value())
#         # unlock the signals from the translation sliders
#         form.xTranslationSlider.blockSignals(False)
#         form.yTranslationSlider.blockSignals(False)
#         form.zTranslationSlider.blockSignals(False)

#     # callback for translation sliders
#     def translate():
#         # Get the current slider values
#         x = form.xTranslationSlider.value() * translationLimit / 100
#         y = form.yTranslationSlider.value() * translationLimit / 100
#         z = form.zTranslationSlider.value() * translationLimit / 100
#         # Calculate the difference between the current and previous slider values
#         dx = x - totalTranslation[0]
#         dy = y - totalTranslation[1]
#         dz = z - totalTranslation[2]
#         # Update the total translation vector
#         totalTranslation[0] = x
#         totalTranslation[1] = y
#         totalTranslation[2] = z
#         # Translate the object
#         cmd.translate([dx, dy, dz], currentObject, camera=0)

#     # Hookup callback functions for ui elements
#     form.xRotationSlider.valueChanged.connect(rotate)
#     form.yRotationSlider.valueChanged.connect(rotate)
#     form.zRotationSlider.valueChanged.connect(rotate)
#     form.xTranslationSlider.valueChanged.connect(translate)
#     form.yTranslationSlider.valueChanged.connect(translate)
#     form.zTranslationSlider.valueChanged.connect(translate)
#     form.selectionComboBox.currentTextChanged.connect(selectionChanged)
#     form.positionSpinBox.valueChanged.connect(positionSpinBoxChanged)


#     # Cleanup when the window is closed
#     def cleanup():
#         resetSliders()
#         print("Transform Tool closed")
#         global dialog
#         dialog = None

#     # Hookup cleanup function
#     dialog.finished.connect(cleanup)

#     return dialog


    
