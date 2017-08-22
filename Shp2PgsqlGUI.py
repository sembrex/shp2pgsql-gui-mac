#!/usr/local/bin/python3

import sys, os, threading, psycopg2, time
from PyQt5 import QtCore, QtWidgets, QtGui
from subprocess import check_output
from mainwindow import Ui_MainWindow

class Shp2Pgsql(QtWidgets.QMainWindow, Ui_MainWindow):
    """docstring for Shp2Pgsql"""
    def __init__(self):
        super(Shp2Pgsql, self).__init__()
        self.setupUi(self)

        path = os.environ['PATH']
        os.environ['PATH'] = '/usr/local/bin:/usr/bin:{}'.format(path)

        self.initUi()
        self.connection = None
        self.counter = 0
        self.file_count = 0

    def initUi(self):
        self.btn_test.clicked.connect(self.connect)
        self.btn_import.clicked.connect(self.execute)
        self.btn_add.clicked.connect(self.add_file)
        self.btn_clear.clicked.connect(self.clear_table)
        self.btn_save_log.clicked.connect(self.save_log)

        self.act_add.triggered.connect(self.add_file)
        self.act_about.triggered.connect(self.show_about)

        fixed_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self.txt_log.setFont(fixed_font)
        self.txt_log.insertPlainText("========== Shp2PgsqlGUI for macOS ==========\n")

        self.show()

    def connect(self, **kwargs):
        host = self.fld_host.text()
        port = self.fld_port.text()
        user = self.fld_user.text()
        password = self.fld_password.text()
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
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, 'Choose shape file to import', home, 'ESRI Shapefiles (*.shp)')
        if len(files):
            self.tbl_file.setRowCount(len(files))

            for i, file in enumerate(files):
                self.tbl_file.setItem(i, 0, QtWidgets.QTableWidgetItem(file))
                self.tbl_file.setItem(i, 1, QtWidgets.QTableWidgetItem('public'))
                self.tbl_file.setItem(i, 2, QtWidgets.QTableWidgetItem(os.path.basename(os.path.splitext(file)[0]).lower()))
                self.tbl_file.setItem(i, 3, QtWidgets.QTableWidgetItem('geom'))
                self.tbl_file.setItem(i, 4, QtWidgets.QTableWidgetItem('4326'))

            self.tbl_file.resizeColumnsToContents()

    def clear_table(self):
        self.tbl_file.clearContents()
        self.tbl_file.setRowCount(0)
        self.tbl_file.resizeColumnsToContents()

    def save_log(self):
        home = os.path.expanduser('~')
        file, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As', home, 'Text File (*.txt)')
        if file:
            file = open(file, 'w')
            file.write(self.txt_log.toPlainText())
            file.close()
            self.alert('Success', 'Log saved', 'info')

    def show_about(self):
        about = QtWidgets.QMessageBox(self)
        about.setWindowTitle('About')
        about.setText('Shp2PgsqlGUI for macOS\n\nThis software helps you operating shp2pgsql in GUI mode.')
        about.exec_()

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
            self.btn_clear.setDisabled(True)

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
            icon = QtWidgets.QMessageBox.Warning
        elif type is 'critical':
            icon = QtWidgets.QMessageBox.Critical
        else:
            icon = QtWidgets.QMessageBox.Information

        msgbox = QtWidgets.QMessageBox(icon, title, text, QtWidgets.QMessageBox.Ok)
        msgbox.exec_()

    def write_log(self, text):
        self.txt_log.insertPlainText(text + '\n')
        self.txt_log.ensureCursorVisible()

    @QtCore.pyqtSlot(str)
    def write_log_slot(self, text):
        self.txt_log.insertPlainText(text + '\n')
        self.txt_log.ensureCursorVisible()

    @QtCore.pyqtSlot()
    def finish(self):
        self.counter += 1
        if self.counter >= self.file_count:
            self.btn_import.setDisabled(False)
            self.btn_add.setDisabled(False)
            self.btn_clear.setDisabled(False)
            self.connection.close()
            self.connection = None
            self.write_log('Jobs done !!!')



class importThread(QtCore.QThread):
    """docstring for importThread"""

    write_log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

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
    app = QtWidgets.QApplication(sys.argv)
    w = Shp2Pgsql()
    sys.exit(app.exec_())
