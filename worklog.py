import sys
from PyQt5 import QtWidgets, uic

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi("temp.ui", self)   # 1. temp.ui 불러오기

        # 2. 라벨 텍스트 읽기 (개별 접근)
        print("label text:", self.label.text())
        print("label_2 text:", self.label_2.text())
        print("label_3 text:", self.label_3.text())
        print("label_4 text:", self.label_4.text())
        print("label_5 text:", self.label_5.text())
        print("label_6 text:", self.label_6.text())

        # 3. 버튼 클릭 → 콜백 연결
        self.pushButton.clicked.connect(self.tempCallBack)

    def tempCallBack(self):
        print("pushButton clicked!")

        # 콜백 실행 시 라벨 값 다시 출력 (개별 접근)
        print("label text:", self.label.text())
        print("label_2 text:", self.label_2.text())
        print("label_3 text:", self.label_3.text())
        print("label_4 text:", self.label_4.text())
        print("label_5 text:", self.label_5.text())
        print("label_6 text:", self.label_6.text())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
