import sys
import os
import shutil
import re

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit,
    QProgressBar, QFileDialog, QPushButton
)

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer



class CopyThread(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, aup2_path, target_folder=None):
        super().__init__()
        self.aup2_path = aup2_path
        self.target_folder = target_folder

    def run(self):
        folder_name = os.path.splitext(os.path.basename(self.aup2_path))[0]
        parent_dir = self.target_folder or os.path.dirname(self.aup2_path)
        target_folder_path = os.path.join(parent_dir, folder_name)

        if not os.path.exists(target_folder_path):
            os.makedirs(target_folder_path)
            self.log_signal.emit(f"フォルダ作成: {target_folder_path}")

        aup2_dest = os.path.join(target_folder_path, os.path.basename(self.aup2_path))
        if not os.path.exists(aup2_dest):
            shutil.copy2(self.aup2_path, aup2_dest)
            self.log_signal.emit(f"aup2コピー: {aup2_dest}")
        else:
            self.log_signal.emit(f"スキップ: {aup2_dest}")

        try:
            with open(self.aup2_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            self.log_signal.emit(f"読み込み失敗: {e}")
            return

        media_files = list(dict.fromkeys(re.findall(r'ファイル=(.+)', content)))

        if not media_files:
            self.log_signal.emit("メディアファイルが見つかりません")
            self.finished_signal.emit()
            return

        total = len(media_files)

        for i, src_path in enumerate(media_files, start=1):
            src = src_path.strip()
            if not src or src == "0":
                continue

            if os.path.isfile(src):
                dest = os.path.join(target_folder_path, os.path.basename(src))
                if not os.path.exists(dest):
                    try:
                        shutil.copy2(src, dest)
                        self.log_signal.emit(f"コピー: {dest}")
                    except Exception as e:
                        self.log_signal.emit(f"コピー失敗: {src} ({e})")
                else:
                    self.log_signal.emit(f"スキップ: {dest}")
            else:
                self.log_signal.emit(f"ファイルが見つかりません: {src}")

            self.progress_signal.emit(int(i / total * 100))

        self.finished_signal.emit()


class Aup2Copier(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("aup2Repack v1.0")
        self.setAcceptDrops(True)
        self.resize(600, 400)

        self.layout = QVBoxLayout()

        self.label = QLabel("ここに .aup2 ファイルをドラッグ＆ドロップしてください")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.layout.addWidget(self.log)

        self.progress = QProgressBar()
        self.progress.setValue(0)  
        self.layout.addWidget(self.progress)


        self.folder_btn = QPushButton("コピー先フォルダを選択")
        self.folder_btn.clicked.connect(self.select_target_folder)
        self.layout.addWidget(self.folder_btn)

        self.setLayout(self.layout)

        self.target_folder = None


    def select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "コピー先フォルダを選択")

        if folder:
            self.target_folder = folder
            self.log_message(f"コピー先変更: {self.target_folder}")


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()


    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".aup2"):
                self.start_copy_thread(path)


    def start_copy_thread(self, aup2_path):
        if not self.target_folder:
            self.log_message("コピー先未指定：aup2と同じフォルダにコピーします")

        self.progress.setValue(0)

        self.copy_thread = CopyThread(aup2_path, self.target_folder)
        self.copy_thread.progress_signal.connect(self.update_progress)
        self.copy_thread.log_signal.connect(self.log_message)
        self.copy_thread.finished_signal.connect(self.on_finished)
        self.copy_thread.start()


    def update_progress(self, value):
        self.progress.setValue(value)


    def log_message(self, message):
        self.log.append(message)
        self.log.verticalScrollBar().setValue(
            self.log.verticalScrollBar().maximum()
        )

    def on_finished(self):
        self.progress.setValue(100)
        self.log_message("コピー処理が完了しました。\n")

        QTimer.singleShot(1000, lambda: self.progress.setValue(0))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Aup2Copier()
    w.show()
    sys.exit(app.exec())
