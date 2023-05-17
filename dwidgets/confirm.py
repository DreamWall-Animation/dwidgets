from PySide2 import QtWidgets


def confirm_dialog(text, title=''):
    prompt = QtWidgets.QMessageBox(
        windowTitle=title, text=text, standardButtons=(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Abort))
    prompt.setDefaultButton(QtWidgets.QMessageBox.Abort)
    if prompt.exec_() == QtWidgets.QMessageBox.Abort:
        return False
    else:
        return True
