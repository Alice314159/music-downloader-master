from GetMusicUrl import Music
from configs import configs
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QDesktopWidget, QLabel, QPushButton, QLineEdit, QFileDialog
import sys
import re
import os
import json
import requests


class MyWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        '''构造函数'''
        # 调用父类构造函数
        super(MyWindow, self).__init__(parent)
        # 设置窗口标记（无边框|任务栏右键菜单）
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        self.setWindowTitle(configs['window_title'])
        self.setWindowIcon(QtGui.QIcon(configs['window_icon']))
        self.w_size = configs['window_size']  # 窗口大小
        self.setFixedWidth(self.w_size[0])  # 宽度固定
        self.setMinimumHeight(self.w_size[1])
        self.setMaximumHeight(self.w_size[1]*2)  # 高度可变
        self.center()
        self.init_ui()
        self.show()

        # other
        self.pattern = re.compile('https?://music\.163\.com/.*id=(\d+)')
        self.music = Music()

    def init_ui(self):
        self.url = QLineEdit(self, placeholderText='请输入歌曲链接:https://music.163.com/#/song?id=*****')
        self.url.setGeometry(self.w_size[0]//9, self.w_size[1]//8, self.w_size[0]*7//9, self.w_size[1]//7)
        self.url.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r'https?://music\.163\.com(/#)?/song\?id=\d{0,11}')))

        #存储位置
        self.file_store = QLineEdit(self, placeholderText='C:\\')
        self.file_store.setGeometry(self.w_size[0]//9, self.w_size[1]*3//8, self.w_size[0]*5//9, self.w_size[1]//7)


        #设置存储路径
        self.file_btn = QPushButton('设置路径', self)
        self.file_btn.setGeometry(self.w_size[0] *7//10, self.w_size[1] * 3 // 8, self.w_size[0]*2// 9,
                                   self.w_size[1]//7)
        self.file_btn.clicked.connect(self.openFile)

        #查询按钮
        self.query_btn = QPushButton('查询', self)
        self.query_btn.setGeometry(self.w_size[0]//9, self.w_size[1]*7//11, self.w_size[0]*3//10, self.w_size[1]//7)
        self.query_btn.clicked.connect(self.query)


        self.down_btn = QPushButton('下载', self)
        self.down_btn.setGeometry(self.w_size[0]*5//9, self.w_size[1]*7//11, self.w_size[0]*3//10, self.w_size[1]//7)
        self.down_btn.clicked.connect(self.download)


        self.tips = QLabel('输出信息：', self)
        self.tips.move(self.w_size[0]//9, self.w_size[1]*6//7)
        self.tips.setAutoFillBackground(True)
        self.tips.setAlignment(QtCore.Qt.AlignLeft)
        self.tips.setFixedWidth(self.w_size[0]*7//8)
        self.tips.setFixedHeight(self.w_size[1])

    def openFile(self):
        get_directory_path = QFileDialog.getExistingDirectory(self,
                                                              "选取指定文件夹",
                                                              "C:/")
        self.file_store.setText(str(get_directory_path))

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def _validate_id(self):
        """检查输入，获得输入文本的有效id值"""
        s = self.url.text()
        r = re.match(self.pattern, s)  # match从s的开始进行匹配，search匹配整个字符串
        if r:
            return r.group(1)
        else:
            return None

    def notify(self, s, t):
        """设置提醒
        s: 提醒的内容
        t: 提醒的类型[yellow, red, green]
        """
        self.tips.setText(s)
        line_nums = len(s.split('\n'))
        if line_nums <= 2:
            self.resize(self.w_size[0], self.w_size[1])
        elif 8 > line_nums > 2:
            self.resize(self.w_size[0], self.w_size[1]*3//2)
        else:
            self.resize(self.w_size[0], self.w_size[1]*2)

    def query(self):
        _id = self._validate_id()

        # 检查输入
        if not _id:
            self.notify('输入无效，请确认\n', 'red')
            return None
        self.music.set_id(_id)
        d = self.music.get_music_detail()
        if not d:
            self.notify('找不到该音乐\n', 'red')
            return None

        # 查询detail
        text = ''
        data = json.loads(d, encoding='utf8')
        try:
            text += '歌曲: ' + data['songs'][0]['name'] + '\n'
            text += '歌手: ' + data['songs'][0]['ar'][0]['name'] + '\n'
            text += '专辑: ' + data['songs'][0]['al']['name'] + '\n'
            text += 'music id: ' + str(data['songs'][0]['id']) + '\n'
            text += '存储至: ' + self.file_store.text() + '\n'
        except:
            text = '找不到音乐，请检查后重试'
            self.notify(text, 'red')
            return None

        # 再次发包查询url，size，MD5等信息
        u = self.music.get_music_url()
        u2 = json.loads(u, encoding='utf8')
        try:
            url = u2['data'][0]['url']  # url 太长，不显示了
            md5 = u2['data'][0]['md5']
            size = u2['data'][0]['size']
            text += ' \n' + 'md5: ' + md5 + '\n' + 'File size: ' + str(size) + ' byte\n'
        except:
            text = '未知错误，无法获取文件信息'
            self.notify(text, 'red')
            return None

        self.notify(text, 'green')
        return url, data['songs'][0]['name'], data['songs'][0]['ar'][0]['name'],md5  # 只有成功查询到音乐才返回url, 歌名与MD5

    def download(self):
        r = self.query()
        if not r:  # 在query里已经notify了，无需重复
            return
        url, name,singer, md5 = r  # 拆包
        opendir = self.file_store.text()
        file = requests.get(url)
        if file.status_code == 200:
            with open(os.path.join(opendir, name+'_'+singer+'.mp3'), 'wb') as f:
                f.write(file.content)


if __name__ == "__main__":
    '''主函数'''
    # 声明变量
    app = QtWidgets.QApplication(sys.argv)

    # 创建窗口
    window = MyWindow()
    # 应用程序事件循环
    sys.exit(app.exec_())

