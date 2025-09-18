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

        # Define the directory where the .md file should exist
        worklog_directory = r"d:\WorklogApplication"

        # Find the first valid .md file in the directory
        md_file = None
        for file in os.listdir(worklog_directory):
            if file.lower().endswith('.md'):
                md_file = os.path.join(worklog_directory, file)
                break

        # Check if a valid .md file was found
        if md_file:
            print("Valid .md file found in WorklogApplication directory.")
            print("Input 1:", user_input1)
            print("Input 2:", user_input2)
            print("MD Attachment:", md_file)
            # Perform additional logic for valid submission
        else:
            QtWidgets.QMessageBox.warning(self, "No .md File Found", "No valid .md file found in the WorklogApplication directory.")

    def closeApp(self):
        # Close the application
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
