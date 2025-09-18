import sys
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
        user_input3 = self.lineEdit_3.text()  # Get text from the third QLineEdit

        # Print the inputs to the console
        print("Input 1:", user_input1)
        print("Input 2:", user_input2)
        print("Input 3:", user_input3)

        # Update the labels or perform any additional logic here
        # For example, you can update a label with the concatenated input:
        print("MD Attachment:", user_input3)

    def closeApp(self):
        # Close the application
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
