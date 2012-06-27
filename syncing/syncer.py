from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from ui_sync import Ui_syncForm
import os
import sys
from subprocess import Popen, PIPE

#This feels a bit hacky
pardir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(pardir)

from utils import log, settings

class Syncer(QObject):
    """
    MS SQL syncer.  Calls the .NET MSSQLSyncer app to syncing
    the two databases.
    """
    def doSync(self):
        """
        Run the sync

        returns -- Returns a tuple of (state, message). state can be 'Pass' or
                   'Fail'
        """
        curdir = os.path.abspath(os.path.dirname(__file__))
        cmdpath = os.path.join(curdir,'bin\MSSQLSyncer.exe')
        p = Popen(cmdpath, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell = True)
        stdout, stderr = p.communicate()
        if not stdout == "":
            log(stdout)
            return ('Pass', stdout)
        else:
            log(stderr)
            return ('Fail', stderr)

class ImageSyncer(QObject):
    """
    Sync logic for syncing images from the device to the server.
    """
    def doSync(self):
        """
        Run the sync

        returns -- Returns a tuple of (state, message). state can be 'Pass' or
                   'Fail'
        """
        images = os.path.join(pardir, "data")
        server = settings.value("syncing/server_image_location").toString()
        if server.isEmpty():
            return ('Fail', "No server image location found in settings.ini")
        
        if not os.path.exists(images):
            # Don't return a fail if there is no data directory
            return
        
        cmd = 'xcopy "%s" "%s" /Q /D /S /E /K /C /H /R /Y' % (images, server)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell = True)
        stdout, stderr = p.communicate()
        if not stderr == "":
            return ('Fail', stderr)
        else:
            return ('Pass', stdout)

class SyncDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_syncForm()
        self.ui.setupUi(self)
        self.ui.buttonBox.hide()
        self.setWindowFlags(Qt.FramelessWindowHint)
        scr = QApplication.desktop().screenGeometry(0)
        self.move( scr.center() - self.rect().center() )
        self.failed = False

    def updateStatus(self, text):
        self.ui.statusLabel.setText(text)
        self.ui.buttonBox.show()

    def updateFailedStatus(self, text):
        self.ui.statusLabel.setStyleSheet("color: rgba(222, 13, 6);")
        self.ui.statusLabel.setText("Something went wrong. \n You might not "
                                    "have a internet connection \n\n We have logged it "
                                    "so we can take a look.")
                                    
        self.ui.label.setPixmap(QPixmap(":/syncing/sad"))
        log("SYNC ERROR:" + text)
        self.ui.buttonBox.show()
        self.failed = True

    def runSync(self):
        """
        Shows the sync dialog and runs the sync commands.
        """
        self.ui.statusLabel.setText("Sycning with server. \n Please Wait")
        message = self.ui.statusLabel.text()
        self.ui.statusLabel.setText(message + "\n\n Syncing map data...")
        QCoreApplication.processEvents()
        
        syncer = Syncer()
        state, sqlmsg = syncer.doSync()

        if state == 'Fail':
            self.updateFailedStatus(sqlmsg)
            return

        log(sqlmsg)

        self.ui.statusLabel.setText(message + "\n\n Syncing images...")
        QCoreApplication.processEvents()
        syncer = ImageSyncer()    
        state, msg = syncer.doSync()

        if state == 'Fail':
            self.updateFailedStatus(msg)
            return

        self.updateStatus("%s \n %s" % (sqlmsg, msg))

if __name__ == "__main__":
    sync = ImageSyncer()
    sync.doSync()