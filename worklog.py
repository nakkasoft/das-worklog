import sys
import os
from PyQt5 import QtWidgets, uic

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi(r"d:\WorklogApplication\worklog.ui", self)  # Load the .ui file

        # Connect the submit button to the callback function
        self.pushButton.clicked.connect(self.submitText)

        # Connect the close button to the close function
        self.closeButton.clicked.connect(self.closeApp)

    def submitText(self):
        # Get the text from the input fields
        user_input1 = self.lineEdit.text()  # Get text from the first QLineEdit
        user_input2 = self.lineEdit_2.text()  # Get text from the second QLineEdit
        user_input3 = self.lineEdit_3.text()  # Get text from the third QLineEdit (file path)

        # Check if the third input is a valid .md file
        if os.path.isfile(user_input3) and user_input3.lower().endswith('.md'):
            print("Valid .md file attached.")
            print("Input 1:", user_input1)
            print("Input 2:", user_input2)
            print("MD Attachment:", user_input3)
            # Perform additional logic for valid submission
        else:
            QtWidgets.QMessageBox.warning(self, "Invalid File", "Please attach a valid .md file.")

    def closeApp(self):
        # Close the application
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
