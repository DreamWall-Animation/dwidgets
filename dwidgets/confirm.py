from PySide2 import QtWidgets


def confirm_dialog(text, title='', parent=None):
    prompt = QtWidgets.QMessageBox(
        windowTitle=title,
        text=text,
        parent=parent,
        standardButtons=(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Abort))
    prompt.setDefaultButton(QtWidgets.QMessageBox.Abort)
    if prompt.exec_() == QtWidgets.QMessageBox.Abort:
        return False
    else:
        return True
