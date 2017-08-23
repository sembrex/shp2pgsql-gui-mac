#!/usr/local/bin/python2

import sys, os, threading, psycopg2, time
from PyQt5 import QtCore, QtWidgets, QtGui
from subprocess import check_output, call
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
        self.threads = {}
        self.selected_rows = []
        self.home = os.path.expanduser('~')

    def initUi(self):
        self.btn_test.clicked.connect(self.connect)
        self.btn_import.clicked.connect(self.import_)
        self.btn_add.clicked.connect(self.add_file)
        self.btn_clear.clicked.connect(lambda: self.clear_table(1))
        self.btn_clear2.clicked.connect(lambda: self.clear_table(2))
        self.btn_save_log.clicked.connect(self.save_log)
        self.btn_remove.setVisible(False)
        self.btn_remove.clicked.connect(lambda: self.remove_selected(1))
        self.btn_remove2.setVisible(False)
        self.btn_remove2.clicked.connect(lambda: self.remove_selected(2))
        self.btn_fetch.clicked.connect(self.fetch_table)
        self.btn_export.clicked.connect(self.export_)

        self.tbl_table.cellDoubleClicked.connect(self.export_dest)

        self.act_add.triggered.connect(self.add_file)
        self.act_about.triggered.connect(self.show_about)

        self.tbl_file.itemSelectionChanged.connect(lambda: self.selection_changed(1))
        self.tbl_table.itemSelectionChanged.connect(lambda: self.selection_changed(2))

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
            self.write_log(str(e))
            if output:
                self.alert('Error', 'Could not conect to database', 'critical')

    def add_file(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, 'Choose shape file to import', self.home, 'ESRI Shapefiles (*.shp)')
        if len(files):
            row_count = self.tbl_file.rowCount()
            self.tbl_file.setRowCount(len(files) + row_count)

            for i, file in enumerate(files):
                self.tbl_file.setItem(i + row_count, 0, QtWidgets.QTableWidgetItem(file))
                self.tbl_file.setItem(i + row_count, 1, QtWidgets.QTableWidgetItem('public'))
                self.tbl_file.setItem(i + row_count, 2, QtWidgets.QTableWidgetItem(os.path.basename(os.path.splitext(file)[0]).lower()))
                self.tbl_file.setItem(i + row_count, 3, QtWidgets.QTableWidgetItem('geom'))
                self.tbl_file.setItem(i + row_count, 4, QtWidgets.QTableWidgetItem('4326'))

            self.tbl_file.resizeColumnsToContents()

    def clear_table(self, num):
        if num == 1:
            table = self.tbl_file
        else:
            table = self.tbl_table

        table.clearContents()
        table.setRowCount(0)
        table.resizeColumnsToContents()

    def selection_changed(self, num):
        items = self.tbl_file.selectedItems() if num == 1 else self.tbl_table.selectedItems()
        self.selected_rows = []
        for item in items:
            row = item.row()
            if not row in self.selected_rows:
                self.selected_rows.append(row)

        if num == 1:
            self.btn_remove.setVisible(len(self.selected_rows) > 0)
        else:
            self.btn_remove2.setVisible(len(self.selected_rows) > 0)

    def remove_selected(self, num):
        self.selected_rows.sort(reverse=True)
        for row in self.selected_rows:
            if num == 1:
                self.tbl_file.removeRow(row)
            else:
                self.tbl_table.removeRow(row)
        self.selected_rows = []

    def fetch_table(self):
        try:
            self.connect(output=False)
            if not self.connection:
                self.alert('Error', 'No database connection', 'critical')
                return
        except Exception:
            self.alert('Error', 'No database connection', 'critical')
            return

        cur = self.connection.cursor()
        cur.execute("select table_schema, table_name from information_schema.tables where table_name != 'spatial_ref_sys' and table_schema not in ('pg_catalog', 'information_schema') and table_type = 'BASE TABLE'")
        tables = cur.fetchall()

        if tables:
            self.tbl_table.setRowCount(0)
            for t in tables:
                cur.execute("select column_name, udt_name from information_schema.columns where table_name='{}' and udt_name in ('geography', 'geometry')".format(t[1]))
                geom = cur.fetchone()
                if geom:
                    row_count = self.tbl_table.rowCount()
                    self.tbl_table.insertRow(row_count)
                    self.tbl_table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(t[0]))
                    self.tbl_table.setItem(row_count, 1, QtWidgets.QTableWidgetItem(t[1]))
                    self.tbl_table.setItem(row_count, 2, QtWidgets.QTableWidgetItem(geom[0]))
                    self.tbl_table.setItem(row_count, 3, QtWidgets.QTableWidgetItem(os.path.join(self.home, t[1] + '.shp')))
                    self.write_log('{} column found in table {}.{}. Adding table to list.'.format(geom[1], t[0], t[1]))
        else:
            self.write_log('No table found')

        if not self.tbl_table.rowCount():
            self.write_log('Could not find table with geography or geometry column.')
            self.alert('Info', 'Could not find table with geography or geometry column.', 'info')

        self.tbl_table.resizeColumnsToContents()
        cur.close()
        self.connection.close()
        self.connection = None

    def export_dest(self, row, col):
        if col == 3:
            file, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As', self.home, 'ESRI Shapefile (*.shp)')
            if file:
                self.tbl_table.setItem(row, col, QtWidgets.QTableWidgetItem(file))
                self.tbl_table.resizeColumnsToContents()

    def save_log(self):
        file, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As', self.home, 'Text File (*.txt)')
        if file:
            file = open(file, 'w')
            file.write(self.txt_log.toPlainText())
            file.close()
            self.alert('Success', 'Log saved', 'info')

    def show_about(self):
        about = QtWidgets.QMessageBox(self)
        about.setWindowTitle('About')
        about.setText('Shp2PgsqlGUI for macOS\n\nThis software helps you operating shp2pgsql and pgsql2shp in GUI mode.')
        about.exec_()

    def import_(self):
        try:
            check_output(['shp2pgsql', '-?'])
        except Exception:
            self.write_log('shp2pgsql command not found.\nRun "brew install postgis" in terminal to install.')
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

    def export_(self):
        try:
            check_output(['pgsql2shp', '-?'])
        except Exception:
            self.write_log('pgsql2shp command not found.\nRun "brew install postgis" in terminal to install.')
            self.alert('Error', 'pgsql2shp command not found.\nRun "brew install postgis" in terminal to install.', 'critical')

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
            self.file_count = self.tbl_table.rowCount()
            self.threads = {}

            self.btn_export.setDisabled(True)
            self.btn_fetch.setDisabled(True)
            self.btn_clear2.setDisabled(True)

            host = self.fld_host.text()
            port = self.fld_port.text()
            dbname = self.fld_dbname.text()
            user = self.fld_user.text()
            password = self.fld_password.text()

            for x in range(0, self.file_count):
                schema = self.tbl_table.item(x, 0).text()
                table = self.tbl_table.item(x, 1).text()
                geom = self.tbl_table.item(x, 2).text()
                dest = self.tbl_table.item(x, 3).text()

                self.threads[x] = exportThread(host, port, dbname, user, password, schema, table, geom, dest)
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

    @QtCore.pyqtSlot(int)
    def finish(self, num):
        self.counter += 1
        if self.counter >= self.file_count:
            if num == 1:
                self.btn_import.setDisabled(False)
                self.btn_add.setDisabled(False)
                self.btn_clear.setDisabled(False)
            else:
                self.btn_export.setDisabled(False)
                self.btn_fetch.setDisabled(False)
                self.btn_clear2.setDisabled(False)

            self.connection.close()
            self.connection = None
            self.write_log('Jobs done !!!')
            self.counter = 0
            self.file_count = 0
            self.threads = {}



class importThread(QtCore.QThread):
    """docstring for importThread"""

    write_log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)

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
        except Exception as e:
            self.write_log(str(e))
            self.write_log.emit("An error occured during {} import.".format(self.path))

        self.finished.emit(1)


class exportThread(QtCore.QThread):
    """docstring for exportThread"""

    write_log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)

    def __init__(self, host, port, dbname, user, password, schema, table, geom, dest):
        super(exportThread, self).__init__()
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.schema = schema
        self.table = table
        self.geom = geom
        self.dest = dest

    def run(self):
        self.write_log.emit("Exporting {}.{} to {}".format(self.schema, self.table, self.dest))
        try:
            output = check_output(['pgsql2shp', '-h', self.host, '-p', self.port, '-u', self.user, '-P', self.password, '-g', self.geom, '-f', self.dest, self.dbname, '{}.{}'.format(self.schema, self.table)])
            self.write_log.emit(output)
        except Exception as e:
            self.write_log(str(e))
            self.write_log.emit("An error occured during {}.{} export.".format(self.schema, self.table))

        self.finished.emit(2)





if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Shp2Pgsql()
    sys.exit(app.exec_())
