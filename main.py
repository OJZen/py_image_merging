import sys
import os
import datetime
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt

# 导入核心生成引擎
try:
    from poster_core import generate_poster_image
except ImportError:
    print("错误：找不到 poster_core.py，请确保它在同一目录下。")
    sys.exit(1)

class PosterGeneratorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片拼接器 V1.0")
        self.resize(500, 200)
        self.setup_ui()

    def setup_ui(self):
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. 文件夹选择区域
        dir_layout = QHBoxLayout()
        self.lbl_dir = QLabel("图片文件夹:")
        self.line_dir = QLineEdit()
        self.line_dir.setPlaceholderText("请选择包含图片的文件夹...")
        self.line_dir.setReadOnly(True) # 只读，防止手输错误
        self.btn_browse = QPushButton("选择...")
        self.btn_browse.clicked.connect(self.select_directory)

        dir_layout.addWidget(self.lbl_dir)
        dir_layout.addWidget(self.line_dir)
        dir_layout.addWidget(self.btn_browse)
        layout.addLayout(dir_layout)

        # 2. 数量输入区域
        num_layout = QHBoxLayout()
        self.lbl_num = QLabel("生成序列:")
        self.line_num = QLineEdit()
        self.line_num.setPlaceholderText("例如: 5 5 6 (用空格分隔)")
        
        num_layout.addWidget(self.lbl_num)
        num_layout.addWidget(self.line_num)
        layout.addLayout(num_layout)

        # 说明文字
        tip_label = QLabel("提示：输出文件将保存在所选文件夹下的 'output' 子目录中。")
        tip_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(tip_label)

        # 3. 生成按钮
        self.btn_run = QPushButton("开始生成图片")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_run.clicked.connect(self.run_generation)
        layout.addWidget(self.btn_run)

        # 弹簧，把内容顶上去
        layout.addStretch()
        
        self.setLayout(layout)

    def select_directory(self):
        """打开文件夹选择框"""
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if folder:
            self.line_dir.setText(folder)

    def show_error(self, message):
        """错误弹窗"""
        QMessageBox.critical(self, "错误", message)

    def show_success(self, message):
        """成功弹窗"""
        QMessageBox.information(self, "完成", message)

    def get_images_sorted(self, folder):
        """获取文件夹内图片并排序 (非递归)"""
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        try:
            # 只获取当前目录的文件，不包含子目录
            files = [f for f in os.listdir(folder) 
                     if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(valid_exts)]
            files.sort() # 按文件名 ASCII 排序
            return [os.path.join(folder, f) for f in files]
        except Exception as e:
            self.show_error(f"读取文件夹失败: {str(e)}")
            return []

    def run_generation(self):
        # 1. 获取并校验输入
        pic_folder = self.line_dir.text().strip()
        num_str = self.line_num.text().strip()

        if not pic_folder:
            self.show_error("请先选择图片文件夹！")
            return
        
        if not os.path.exists(pic_folder):
            self.show_error("所选文件夹不存在！")
            return

        if not num_str:
            self.show_error("请输入生成数量序列（例如 5 5 6）！")
            return

        # 2. 解析数字序列
        try:
            counts = [int(x) for x in num_str.split()]
            # 检查是否有小于5的数字
            for c in counts:
                if c < 5:
                    self.show_error(f"单张图片数量不能少于5张（输入包含 {c}）")
                    return
        except ValueError:
            self.show_error("输入格式错误！请确保只包含数字和空格。")
            return

        # 3. 获取图片资源
        all_images = self.get_images_sorted(pic_folder)
        total_available = len(all_images)
        total_needed = sum(counts)

        if total_needed > total_available:
            self.show_error(f"图片数量不足！\n\n需要: {total_needed} 张\n实际: {total_available} 张")
            return

        # 4. 准备 Output 文件夹
        output_dir = os.path.join(pic_folder, "output")
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                self.show_error(f"无法创建 output 文件夹: {e}")
                return

        # 5. 开始生成逻辑
        # 禁用按钮防止重复点击
        self.btn_run.setEnabled(False)
        self.btn_run.setText("正在生成中，请稍候...")
        QApplication.processEvents() # 刷新界面，防止假死

        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        start_index = 0
        success_count = 0

        try:
            for i, count in enumerate(counts):
                # 切片
                end_index = start_index + count
                batch_imgs = all_images[start_index : end_index]
                
                # 构建输出路径
                filename = f"template_{count}_{timestamp}_{i+1}.png"
                output_path = os.path.join(output_dir, filename)

                # 调用核心引擎
                result = generate_poster_image(batch_imgs, output_path)
                
                if result:
                    success_count += 1
                else:
                    self.show_error(f"生成第 {i+1} 张海报时失败。")
                    # 恢复按钮并退出
                    self.btn_run.setEnabled(True)
                    self.btn_run.setText("开始生成图片")
                    return

                start_index = end_index

            # 全部完成
            self.show_success(f"成功处理！\n\n共生成 {success_count} 张海报。\n文件已保存至: {output_dir}")

        except Exception as e:
            self.show_error(f"发生未预期的错误: {e}")
        finally:
            # 恢复按钮状态
            self.btn_run.setEnabled(True)
            self.btn_run.setText("开始生成图片")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PosterGeneratorApp()
    window.show()
    sys.exit(app.exec())