#!/usr/local/bin/python3

import sys, os, threading, psycopg2, time
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLineEdit, QPushButton, QTableWidget, QFileDialog, QTableWidgetItem, QVBoxLayout, QFormLayout, QGridLayout, QPlainTextEdit, QLabel, QMessageBox
from PyQt5.QtGui import QFont, QFontDatabase
from subprocess import check_output

class Shp2Pgsql(QMainWindow):
    """docstring for Shp2Pgsql"""
    def __init__(self):
        super(Shp2Pgsql, self).__init__()

        path = os.environ['PATH']
        os.environ['PATH'] = '/usr/local/bin:/usr/bin:{}'.format(path)

        self.initUi()
        self.connection = None
        self.counter = 0
        self.file_count = 0

    def initUi(self):
        self.setWindowTitle('Shp2PgsqlGUI')
        self.resize(500, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        top_widget = QWidget()
        middle_widget = QWidget()
        bottom_widget = QWidget()

        self.fld_host = QLineEdit('localhost')
        self.fld_host.setPlaceholderText('Host')
        self.fld_port = QLineEdit('5432')
        self.fld_port.setPlaceholderText('Port')
        self.fld_user = QLineEdit()
        self.fld_user.setPlaceholderText('Username')
        self.fld_pass = QLineEdit()
        self.fld_pass.setPlaceholderText('Password')
        self.fld_dbname = QLineEdit()
        self.fld_dbname.setPlaceholderText('Database')

        btn_connect = QPushButton('Test &Connection')
        btn_connect.resize(btn_connect.sizeHint())
        btn_connect.setToolTip('Connect to database')
        btn_connect.clicked.connect(self.connect)

        self.btn_import = QPushButton('&Import')
        self.btn_import.resize(self.btn_import.sizeHint())
        self.btn_import.setToolTip('Import Shapefile to PostgreSQL database')
        self.btn_import.clicked.connect(self.execute)

        lbl_file = QLabel('File list:')
        self.tbl_file = QTableWidget()

        self.btn_add = QPushButton('&Add File')
        self.btn_add.clicked.connect(self.add_file)

        self.btn_exit = QPushButton('&Quit')
        self.btn_exit.resize(self.btn_exit.sizeHint())
        self.btn_exit.clicked.connect(self.close)

        lbl_log = QLabel('Log:')

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.txt_log.setFont(fixed_font)


        main_layout = QVBoxLayout(central_widget)
        top_layout = QFormLayout(top_widget)
        middle_layout = QVBoxLayout(middle_widget)
        bottom_layout = QGridLayout(bottom_widget)

        top_layout.addRow(QLabel('Host'), self.fld_host)
        top_layout.addRow(QLabel('Port'), self.fld_port)
        top_layout.addRow(QLabel('Username'), self.fld_user)
        top_layout.addRow(QLabel('Password'), self.fld_pass)
        top_layout.addRow(QLabel('Database'), self.fld_dbname)
        top_layout.addWidget(btn_connect)

        middle_layout.addWidget(lbl_file)
        middle_layout.addWidget(self.tbl_file)

        bottom_layout.addWidget(self.btn_add, 0, 0)
        bottom_layout.addWidget(self.btn_import, 0, 1)
        bottom_layout.addWidget(self.btn_exit, 1, 0, 1, 2)
        bottom_layout.addWidget(lbl_log, 2, 0, 1, 2)
        bottom_layout.addWidget(self.txt_log, 3, 0, 1, 2)

        main_layout.addWidget(top_widget)
        main_layout.addWidget(middle_widget)
        main_layout.addWidget(bottom_widget)

        self.txt_log.insertPlainText(
"""
┌──────────────────────────────────────┐
│                                      │
│        Shp2PgsqlGUI for macOS        │
│                                      │
│          by Rifa'i M. Hanif          │
│                                      │
└──────────────────────────────────────┘
"""
        )

        self.show()

    def connect(self, **kwargs):
        host = self.fld_host.text()
        port = self.fld_port.text()
        user = self.fld_user.text()
        password = self.fld_pass.text()
        dbname = self.fld_dbname.text()

        output = kwargs.get('output', True)

        try:
            self.connection = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
            if output:
                self.alert('Success', 'Connected to database', 'info')
            self.write_log('Connected to database {} on {}:{}'.format(dbname, host, port))
        except Exception as e:
            if output:
                self.alert('Error', 'Could not conect to database', 'critical')

    def add_file(self):
        home = os.path.expanduser('~')
        files, _ = QFileDialog.getOpenFileNames(self, 'Choose shape file to import', home, 'ESRI Shapefile (*.shp)')
        if len(files):
            self.tbl_file.setRowCount(len(files))
            self.tbl_file.setColumnCount(5)
            self.tbl_file.setHorizontalHeaderLabels(['File', 'Schema', 'Table', 'Geometry Column', 'SRID'])

            for i, file in enumerate(files):
                self.tbl_file.setItem(i, 0, QTableWidgetItem(file))
                self.tbl_file.setItem(i, 1, QTableWidgetItem('public'))
                self.tbl_file.setItem(i, 2, QTableWidgetItem(os.path.basename(os.path.splitext(file)[0]).lower()))
                self.tbl_file.setItem(i, 3, QTableWidgetItem('geom'))
                self.tbl_file.setItem(i, 4, QTableWidgetItem('4326'))

            self.tbl_file.resizeColumnsToContents()

    def execute(self):
        try:
            check_output(['shp2pgsql', '-?'])
        except Exception as e:
            self.alert('Error', 'shp2pgsql command not found.\nRun "brew install postgis" in terminal to install.', 'critical')

        try:
            self.connect(output=False)
            if not self.connection:
                self.alert('Error', 'No database connection', 'critical')
                return
        except Exception:
            self.alert('Error', 'No database connection', 'critical')
            return

        try:
            self.counter = 0
            self.file_count = self.tbl_file.rowCount()
            self.threads = {}

            self.btn_import.setDisabled(True)
            self.btn_add.setDisabled(True)
            self.btn_exit.setDisabled(True)

            for x in range(0, self.file_count):
                path = self.tbl_file.item(x, 0).text()
                schema = self.tbl_file.item(x, 1).text()
                table = self.tbl_file.item(x, 2).text()
                geom = self.tbl_file.item(x, 3).text()
                srid = self.tbl_file.item(x, 4).text()

                self.threads[x] = importThread(self.connection, path, schema, table, geom, srid)
                self.threads[x].write_log.connect(self.write_log_slot)
                self.threads[x].finished.connect(self.finish)
                self.threads[x].start()
        except Exception as e:
            self.write_log(str(e))

    def alert(self, title, text, type):
        if type is 'warning':
            icon = QMessageBox.Warning
        elif type is 'critical':
            icon = QMessageBox.Critical
        else:
            icon = QMessageBox.Information

        msgbox = QMessageBox(icon, title, text, QMessageBox.Ok)
        msgbox.exec_()

    def write_log(self, text):
        self.txt_log.insertPlainText(text + '\n')
        self.txt_log.ensureCursorVisible()

    @pyqtSlot(str)
    def write_log_slot(self, text):
        self.txt_log.insertPlainText(text + '\n')
        self.txt_log.ensureCursorVisible()

    @pyqtSlot()
    def finish(self):
        self.counter += 1
        if self.counter >= self.file_count:
            self.btn_import.setDisabled(False)
            self.btn_add.setDisabled(False)
            self.btn_exit.setDisabled(False)
            self.connection.close()
            self.connection = None
            self.write_log('Jobs done !!!')



class importThread(QThread):
    """docstring for importThread"""

    write_log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, connection, path, schema, table, geom, srid):
        super(importThread, self).__init__()
        self.connection = connection
        self.path = path
        self.schema = schema
        self.table = table
        self.geom = geom
        self.srid = srid

    def run(self):
        self.write_log.emit("Importing {} to {}.{}".format(self.path, self.schema, self.table))
        try:
            args = ['shp2pgsql', '-c', '-g', self.geom, '-s', self.srid]
            cur = self.connection.cursor()
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='{}' AND table_name='{}' AND table_type = 'BASE TABLE'".format(self.schema, self.table))

            try:
                row = cur.fetchone()
                if row:
                    args.append('-d')
            except Exception:
                pass

            args.extend([self.path, '.'.join([self.schema, self.table])])
            sql = check_output(args)
            cur.execute(sql)
            self.write_log.emit(cur.statusmessage)
            cur.close()
            self.write_log.emit("{} successfully imported to {}.{}".format(self.path, self.schema, self.table))
        except Exception:
            self.write_log.emit("An error occured during {} import.".format(self.path))

        self.finished.emit()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Shp2Pgsql()
    sys.exit(app.exec_())
