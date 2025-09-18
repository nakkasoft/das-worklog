import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QLineEdit
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt  # Import Qt for alignment

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Welcome to Worklog Genie!!!')  # Updated the window title
        self.setGeometry(100, 100, 400, 500)  # x, y, width, height

        # Set azure blue background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('#F0FFFF'))  # Azure blue color
        self.setPalette(palette)

        # Create a label
        self.label = QLabel('Welcome to Worklog Genie!!!', self)
        self.label.setAlignment(Qt.AlignCenter)  # Align the label text to the center

        # Create labels for instructions
        self.input_label1 = QLabel('Key: JIRA/Collab', self)
        self.input_label2 = QLabel('Key: Gerrit', self)
        self.md_file_label = QLabel('Enter the path or name of the .md file:', self)

        # Create input fields
        self.input_field1 = QLineEdit(self)
        self.input_field1.setPlaceholderText('Enter first input here')

        self.input_field2 = QLineEdit(self)
        self.input_field2.setPlaceholderText('Enter second input here')

        self.md_file_input = QLineEdit(self)
        self.md_file_input.setPlaceholderText('Enter .md file path or name here')

        # Create buttons
        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.submit_text)

        self.close_button = QPushButton('Close', self)
        self.close_button.clicked.connect(self.close_app)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_label1)
        layout.addWidget(self.input_field1)
        layout.addWidget(self.input_label2)
        layout.addWidget(self.input_field2)
        layout.addWidget(self.md_file_label)
        layout.addWidget(self.md_file_input)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

    def close_app(self):
        self.close()

    def submit_text(self):
        user_input1 = self.input_field1.text()
        user_input2 = self.input_field2.text()
        md_file_input = self.md_file_input.text()
        if user_input1.strip() and user_input2.strip() and md_file_input.strip():  # Check if all inputs are not empty
            self.label.setText(f'{user_input1} {user_input2}\nMD File: {md_file_input}')
        else:
            self.label.setText('Please fill in all inputs!')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
