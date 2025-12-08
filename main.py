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
        self.setWindowTitle("Poster Generator - 海报合成工具")
        self.resize(600, 420)
        self.setAcceptDrops(True) # 允许拖拽
        self.current_images = [] # 缓存当前的图片列表
        self.setup_ui()
        self.apply_styles()

    def apply_styles(self):
        """应用现代亮色主题样式"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                color: #333333;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
            }
            
            /* 输入框样式 */
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                color: #333333;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
                background-color: #ffffff;
            }
            QLineEdit:disabled {
                background-color: #f0f0f0;
                color: #999999;
            }

            /* 标签样式 */
            QLabel {
                color: #555555;
            }
            QLabel#TitleLabel {
                font-size: 20px;
                font-weight: 600;
                color: #222222;
                margin-bottom: 10px;
            }
            QLabel#InfoLabel {
                font-size: 13px;
                font-weight: 500;
                padding: 4px 10px;
                border-radius: 4px;
            }

            /* 按钮样式 */
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                color: #333333;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #b0b0b0;
                color: #0078d7;
            }
            QPushButton:pressed {
                background-color: #eef0f2;
            }
            
            /* 主动作按钮 (Primary Button) */
            QPushButton#PrimaryButton {
                background-color: #0078d7;
                color: white;
                border: none;
                font-weight: 600;
                font-size: 15px;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #0063b1;
            }
            QPushButton#PrimaryButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#PrimaryButton:disabled {
                background-color: #e0e0e0;
                color: #a0a0a0;
            }

            /* 拖拽区域样式 */
            QFrame#DropZone {
                background-color: #ffffff;
                border: 2px dashed #cfd7e6;
                border-radius: 12px;
            }
            QFrame#DropZone:hover {
                border-color: #0078d7;
                background-color: #f0f7ff;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # 可选：高亮拖拽区域
            self.drop_frame.setStyleSheet("""
                QFrame#DropZone {
                    background-color: #f0f7ff;
                    border: 2px dashed #0078d7;
                    border-radius: 12px;
                }
            """)

    def dragLeaveEvent(self, event):
        # 恢复样式
        self.drop_frame.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        """拖拽释放事件"""
        # 恢复样式
        self.drop_frame.setStyleSheet("")
        
        urls = event.mimeData().urls()
        if urls:
            # 获取第一个文件的路径
            file_path = urls[0].toLocalFile()
            if os.path.isdir(file_path):
                self.line_dir.setText(file_path)
                self.update_folder_info(file_path)
            else:
                # 如果拖入的是文件，尝试获取其父目录
                parent_dir = os.path.dirname(file_path)
                self.line_dir.setText(parent_dir)
                self.update_folder_info(parent_dir)

    def setup_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(35, 35, 35, 35)

        # 标题
        title = QLabel("Poster Generator")
        title.setObjectName("TitleLabel")
        main_layout.addWidget(title)

        # 1. 文件夹选择区域 (设计为拖拽区)
        self.drop_frame = QWidget() # 使用 QWidget 或 QFrame
        self.drop_frame.setObjectName("DropZone")
        # 为 DropZone 创建子布局
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setContentsMargins(20, 25, 20, 20)
        drop_layout.setSpacing(12)

        # 内部组件
        drop_tip = QLabel("📂 拖入文件夹 或 点击选择")
        drop_tip.setAlignment(Qt.AlignCenter)
        drop_tip.setStyleSheet("font-size: 16px; color: #555; font-weight: 600;")
        
        self.line_dir = QLineEdit()
        self.line_dir.setPlaceholderText("当前未选择任何路径")
        self.line_dir.setReadOnly(True) 
        self.line_dir.setStyleSheet("background: transparent; border: none; color: #666; padding: 0;")
        self.line_dir.setAlignment(Qt.AlignCenter)

        self.btn_browse = QPushButton("浏览文件夹")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFixedWidth(130)
        self.btn_browse.clicked.connect(self.select_directory)

        # 图片数量提示 (现在放在 Drop Zone 内部，作为状态反馈)
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("InfoLabel")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        
        # 将组件加入 DropZone 布局
        drop_layout.addWidget(drop_tip)
        drop_layout.addWidget(self.line_dir)
        drop_layout.addWidget(self.btn_browse, 0, Qt.AlignCenter)
        drop_layout.addSpacing(5) 
        drop_layout.addWidget(self.lbl_info) 

        main_layout.addWidget(self.drop_frame)

        # 2. 数量输入区域
        setting_layout = QHBoxLayout()
        
        lbl_num = QLabel("生成序列:")
        lbl_num.setStyleSheet("font-weight: 600; font-size: 14px;")
        
        self.line_num = QLineEdit()
        self.line_num.setPlaceholderText("例如: 5 5 6 (每张海报包含的图片数)")
        regex = QRegularExpression("^[0-9\\s]*$")
        validator = QRegularExpressionValidator(regex)
        self.line_num.setValidator(validator)
        
        setting_layout.addWidget(lbl_num)
        setting_layout.addWidget(self.line_num)
        main_layout.addLayout(setting_layout)

        # 说明文字
        tip_label = QLabel("ℹ️ 提示：输出文件将保存在原文件夹下的 'output' 子目录中。")
        tip_label.setStyleSheet("color: #777; font-size: 12px; margin-top: 5px;")
        main_layout.addWidget(tip_label)

        # 弹簧
        main_layout.addStretch()

        # 3. 生成按钮
        self.btn_run = QPushButton("🚀 开始生成海报")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.run_generation)
        main_layout.addWidget(self.btn_run)
        
        self.setLayout(main_layout)

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
            self.lbl_info.setText(f"✅ 已加载 {count} 张图片")
            # 柔和的绿色背景
            self.lbl_info.setStyleSheet("color: #155724; background-color: #d4edda; border: 1px solid #c3e6cb;")
        else:
            self.lbl_info.setText(f"❌ 未找到支持的图片")
            # 柔和的红色背景
            self.lbl_info.setStyleSheet("color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb;")

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