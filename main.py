import sys
import os
import re
import datetime
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QDragEnterEvent, QDropEvent

# 导入核心生成引擎
try:
    from poster_core import generate_poster_image
except ImportError:
    print("错误：找不到 poster_core.py，请确保它在同一目录下。")
    sys.exit(1)

class PosterGeneratorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("海报批量生成器 GUI")
        self.resize(550, 250)
        self.setAcceptDrops(True) # 允许拖拽
        self.setup_ui()
        self.current_images = [] # 缓存当前的图片列表

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """拖拽释放事件"""
        urls = event.mimeData().urls()
        if urls:
            # 获取第一个文件的路径
            file_path = urls[0].toLocalFile()
            if os.path.isdir(file_path):
                self.line_dir.setText(file_path)
                self.update_folder_info(file_path)

    def setup_ui(self):
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # 1. 文件夹选择区域
        dir_layout = QHBoxLayout()
        self.lbl_dir = QLabel("图片文件夹:")
        self.line_dir = QLineEdit()
        self.line_dir.setPlaceholderText("请选择包含图片的文件夹...")
        self.line_dir.setReadOnly(True) 
        self.btn_browse = QPushButton("选择...")
        self.btn_browse.clicked.connect(self.select_directory)

        dir_layout.addWidget(self.lbl_dir)
        dir_layout.addWidget(self.line_dir)
        dir_layout.addWidget(self.btn_browse)
        layout.addLayout(dir_layout)

        # [新增] 图片数量提示标签
        self.lbl_info = QLabel("尚未加载文件夹")
        self.lbl_info.setStyleSheet("color: gray; font-size: 12px; margin-left: 70px;") 
        layout.addWidget(self.lbl_info)

        # 2. 数量输入区域
        num_layout = QHBoxLayout()
        self.lbl_num = QLabel("生成序列:")
        self.line_num = QLineEdit()
        self.line_num.setPlaceholderText("例如: 5 5 6 (仅限数字和空格)")
        
        # [新增] 限制只能输入数字和空格
        # 正则表达式: ^[0-9\s]*$  表示从头到尾只能是 数字(0-9) 或 空白字符
        regex = QRegularExpression("^[0-9\\s]*$")
        validator = QRegularExpressionValidator(regex)
        self.line_num.setValidator(validator)
        
        num_layout.addWidget(self.lbl_num)
        num_layout.addWidget(self.line_num)
        layout.addLayout(num_layout)

        # 说明文字
        tip_label = QLabel("提示：输出文件将保存在所选文件夹下的 'output' 子目录中。")
        tip_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(tip_label)

        # 3. 生成按钮
        self.btn_run = QPushButton("开始生成图片")
        self.btn_run.setMinimumHeight(45)
        self.btn_run.setStyleSheet("""
            QPushButton {
                font-weight: bold; 
                font-size: 14px;
                background-color: #0078d7;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0063b1;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.btn_run.clicked.connect(self.run_generation)
        layout.addWidget(self.btn_run)

        # 弹簧
        layout.addStretch()
        
        self.setLayout(layout)

    def get_images_sorted(self, folder):
        """获取文件夹内图片并按自然顺序排序 (1, 2, 10...)"""
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        
        try:
            # 1. 筛选文件
            files = [f for f in os.listdir(folder) 
                     if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(valid_exts)]
            
            # 2. 定义自然排序的 Key
            # 原理：将字符串 "abc10.jpg" 切分为 ['abc', 10, '.jpg']，然后按列表元素比较
            def natural_key(string_):
                return [int(text) if text.isdigit() else text.lower() 
                        for text in re.split('(\d+)', string_)]
            
            # 3. 使用 Key 进行排序
            files.sort(key=natural_key)
            
            return [os.path.join(folder, f) for f in files]
        except Exception as e:
            self.show_error(f"读取或排序失败: {str(e)}")
            return []

    def select_directory(self):
        """打开文件夹选择框，并立即统计数量"""
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if folder:
            self.line_dir.setText(folder)
            self.update_folder_info(folder)

    def update_folder_info(self, folder):
        """[新增] 统计并显示图片数量"""
        self.current_images = self.get_images_sorted(folder)
        count = len(self.current_images)
        
        if count > 0:
            self.lbl_info.setText(f"✅ 已加载 {count} 张图片 (准备就绪)")
            self.lbl_info.setStyleSheet("color: green; font-size: 12px; margin-left: 70px; font-weight: bold;")
        else:
            self.lbl_info.setText(f"❌ 该文件夹下未找到图片")
            self.lbl_info.setStyleSheet("color: red; font-size: 12px; margin-left: 70px;")

    def show_error(self, message):
        QMessageBox.critical(self, "错误", message)

    def show_success(self, message):
        QMessageBox.information(self, "完成", message)

    def run_generation(self):
        # 1. 基础校验
        pic_folder = self.line_dir.text().strip()
        num_str = self.line_num.text().strip()

        if not pic_folder or not os.path.exists(pic_folder):
            self.show_error("请先选择有效的图片文件夹！")
            return

        if not num_str:
            self.show_error("请输入生成数量序列！")
            return

        # 2. 解析数字 (因为有了Validator，这里不太可能抛出 ValueError，但保留逻辑更稳健)
        try:
            counts = [int(x) for x in num_str.split()]
            if not counts:
                self.show_error("请输入至少一个数字！")
                return
            for c in counts:
                if c < 5:
                    self.show_error(f"单张图片数量不能少于5张（输入包含 {c}）")
                    return
        except ValueError:
            self.show_error("输入格式错误！")
            return

        # 3. 校验库存 (使用缓存的数量)
        # 为了保险起见，再次获取一次（防止用户选了文件夹后又去删了图片）
        all_images = self.get_images_sorted(pic_folder)
        total_available = len(all_images)
        total_needed = sum(counts)

        if total_needed > total_available:
            self.show_error(f"图片数量不足！\n\n需要: {total_needed} 张\n库存: {total_available} 张")
            return

        # 4. 准备 Output 文件夹
        output_dir = os.path.join(pic_folder, "output")
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                self.show_error(f"无法创建 output 文件夹: {e}")
                return

        # 5. 执行生成
        self.btn_run.setEnabled(False)
        self.btn_run.setText("正在生成中，请稍候...")
        QApplication.processEvents()

        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        start_index = 0
        success_count = 0

        try:
            for i, count in enumerate(counts):
                end_index = start_index + count
                batch_imgs = all_images[start_index : end_index]
                
                filename = f"template_{count}_{timestamp}_{i+1}.png"
                output_path = os.path.join(output_dir, filename)

                if generate_poster_image(batch_imgs, output_path):
                    success_count += 1
                else:
                    self.show_error(f"生成第 {i+1} 张海报时失败。")
                    self.btn_run.setEnabled(True)
                    self.btn_run.setText("开始生成图片")
                    return

                start_index = end_index

            self.show_success(f"成功处理！\n\n共生成 {success_count} 张海报。\n保存至: {output_dir}")

        except Exception as e:
            self.show_error(f"未知错误: {e}")
        finally:
            self.btn_run.setEnabled(True)
            self.btn_run.setText("开始生成图片")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PosterGeneratorApp()
    window.show()
    sys.exit(app.exec())