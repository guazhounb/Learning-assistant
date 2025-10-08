import os
import json
import datetime
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
from typing import List, Dict, Optional, Tuple
import time

# 确保中文显示正常
def setup_matplotlib_font():
    try:
        font_candidates = [
            "SimHei", "WenQuanYi Micro Hei", "Heiti TC", 
            "Microsoft YaHei", "PingFang SC", "SimSun", 
            "Arial Unicode MS", "sans-serif"
        ]
        plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False
        print(f"已设置matplotlib字体：{plt.rcParams['font.family']}")
    except Exception as e:
        plt.rcParams["font.family"] = ["Arial Unicode MS", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False
        print(f"字体设置警告：{str(e)}，已使用备选字体")

setup_matplotlib_font()

# 全局常见科目列表
COMMON_SUBJECTS = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]

class Task:
    def __init__(self, subject: str, content: str, deadline: str, priority: int = 1, study_mode: str = "normal", time_limit: int = 0):
        self.id = self._generate_id()
        self.subject = subject
        self.content = content
        self.deadline = deadline
        self.priority = max(1, min(5, priority))
        self.completed = False
        self.created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.completed_at = None
        self.study_mode = study_mode  # normal/study_mode
        self.time_limit = time_limit  # 学霸模式任务时间限制（分钟）
        self.start_time = None  # 学霸模式任务开始时间
        self.close_attempts = 0  # 记录用户尝试关闭窗口的次数

    def _generate_id(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return f"task_{timestamp}_{random.randint(100, 999)}"

    def start_study_mode(self) -> None:
        """开始学霸模式任务计时"""
        if self.study_mode == "study_mode" and not self.start_time:
            self.start_time = datetime.datetime.now()

    def complete(self) -> bool:
        """标记任务为已完成（学霸模式需检查时间限制）"""
        if self.study_mode == "study_mode" and self.time_limit > 0:
            if not self.start_time:
                messagebox.showerror("错误", "学霸模式任务未开始计时，无法完成")
                return False
            # 计算已用时（分钟）
            used_time = (datetime.datetime.now() - self.start_time).total_seconds() / 60
            if used_time < self.time_limit:
                remaining = self.time_limit - used_time
                messagebox.showerror("时间未到", f"学霸模式任务需完成{self.time_limit}分钟，还需{remaining:.1f}分钟")
                return False
        if not self.completed:
            self.completed = True
            self.completed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return True
    
    def record_close_attempt(self) -> int:
        """记录关闭窗口尝试并返回次数"""
        self.close_attempts += 1
        return self.close_attempts

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "content": self.content,
            "deadline": self.deadline,
            "priority": self.priority,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "study_mode": self.study_mode,
            "time_limit": self.time_limit,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "close_attempts": self.close_attempts
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        task = cls(
            subject=data["subject"],
            content=data["content"],
            deadline=data["deadline"],
            priority=data["priority"],
            study_mode=data.get("study_mode", "normal"),
            time_limit=data.get("time_limit", 0)
        )
        task.id = data["id"]
        task.completed = data["completed"]
        task.created_at = data["created_at"]
        task.completed_at = data["completed_at"]
        task.close_attempts = data.get("close_attempts", 0)
        if data.get("start_time"):
            task.start_time = datetime.datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
        return task

class 错题:
    def __init__(self, subject: str, question: str, answer: str, mistake: str, category: str):
        self.id = self._generate_id()
        self.subject = subject
        self.question = question
        self.answer = answer
        self.mistake = mistake
        self.category = category
        self.created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.review_count = 0
        self.last_reviewed = None

    def _generate_id(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return f"error_{timestamp}_{random.randint(100, 999)}"

    def review(self) -> None:
        self.review_count += 1
        self.last_reviewed = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "question": self.question,
            "answer": self.answer,
            "mistake": self.mistake,
            "category": self.category,
            "created_at": self.created_at,
            "review_count": self.review_count,
            "last_reviewed": self.last_reviewed
        }

    @classmethod
    def from_dict(cls, data: Dict) -> '错题':
        error = cls(
            subject=data["subject"],
            question=data["question"],
            answer=data["answer"],
            mistake=data["mistake"],
            category=data["category"]
        )
        error.id = data["id"]
        error.created_at = data["created_at"]
        error.review_count = data["review_count"]
        error.last_reviewed = data["last_reviewed"]
        return error

class StudyHelper:
    def __init__(self, data_dir: str = "study_data"):
        self.data_dir = data_dir
        self.tasks_file = os.path.join(data_dir, "tasks.json")
        self.errors_file = os.path.join(data_dir, "errors.json")
        
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        self.tasks = self._load_tasks()
        self.errors = self._load_errors()

    def _load_tasks(self) -> List[Task]:
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [Task.from_dict(item) for item in data]
            except:
                return []
        return []

    def _load_errors(self) -> List[错题]:
        if os.path.exists(self.errors_file):
            try:
                with open(self.errors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [错题.from_dict(item) for item in data]
            except:
                return []
        return []

    def _save_tasks(self) -> None:
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump([task.to_dict() for task in self.tasks], f, ensure_ascii=False, indent=2)

    def _save_errors(self) -> None:
        with open(self.errors_file, 'w', encoding='utf-8') as f:
            json.dump([error.to_dict() for error in self.errors], f, ensure_ascii=False, indent=2)

    # 任务管理（新增学霸模式参数）
    def add_task(self, subject: str, content: str, deadline: str, priority: int = 1, study_mode: str = "normal", time_limit: int = 0) -> Task:
        task = Task(subject, content, deadline, priority, study_mode, time_limit)
        self.tasks.append(task)
        self._save_tasks()
        return task

    def start_study_mode_task(self, task_id: str) -> bool:
        """开始学霸模式任务计时"""
        for task in self.tasks:
            if task.id == task_id and task.study_mode == "study_mode" and not task.start_time:
                task.start_study_mode()
                self._save_tasks()
                return True
        return False

    def complete_task(self, task_id: str) -> bool:
        for task in self.tasks:
            if task.id == task_id:
                if task.complete():  # 调用Task类的complete方法（含时间检查）
                    self._save_tasks()
                    return True
                return False
        return False
    
    def record_close_attempt(self, task_id: str) -> int:
        """记录关闭窗口尝试"""
        for task in self.tasks:
            if task.id == task_id:
                attempts = task.record_close_attempt()
                self._save_tasks()
                return attempts
        return 0

    # 其他原有方法保持不变
    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks if not task.completed]

    def get_completed_tasks(self) -> List[Task]:
        return [task for task in self.tasks if task.completed]

    def delete_task(self, task_id: str) -> bool:
        initial_count = len(self.tasks)
        self.tasks = [task for task in self.tasks if task.id != task_id]
        if len(self.tasks) < initial_count:
            self._save_tasks()
            return True
        return False

    def add_error(self, subject: str, question: str, answer: str, mistake: str, category: str) -> 错题:
        error = 错题(subject, question, answer, mistake, category)
        self.errors.append(error)
        self._save_errors()
        return error

    def review_error(self, error_id: str) -> bool:
        for error in self.errors:
            if error.id == error_id:
                error.review()
                self._save_errors()
                return True
        return False

    def get_errors_by_subject(self, subject: str) -> List[错题]:
        if not subject:
            return self.errors.copy()
        return [error for error in self.errors if error.subject == subject]

    def delete_error(self, error_id: str) -> bool:
        initial_count = len(self.errors)
        self.errors = [error for error in self.errors if error.id != error_id]
        if len(self.errors) < initial_count:
            self._save_errors()
            return True
        return False

    def get_task_stats(self, days: int = 7) -> Tuple[Dict, int, int, float]:
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        recent_tasks = []
        for task in self.tasks:
            created_date = datetime.datetime.strptime(task.created_at.split()[0], "%Y-%m-%d")
            if start_date <= created_date <= end_date:
                recent_tasks.append(task)
        
        if not recent_tasks:
            return {}, 0, 0, 0.0
        
        total = len(recent_tasks)
        completed = len([t for t in recent_tasks if t.completed])
        completion_rate = (completed / total) * 100 if total > 0 else 0
        
        subject_stats = {}
        for task in recent_tasks:
            if task.subject not in subject_stats:
                subject_stats[task.subject] = {"total": 0, "completed": 0}
            subject_stats[task.subject]["total"] += 1
            if task.completed:
                subject_stats[task.subject]["completed"] += 1
        
        return subject_stats, total, completed, completion_rate

    def get_error_stats(self) -> Dict:
        if not self.errors:
            return {}
        
        subject_stats = {}
        for error in self.errors:
            if error.subject not in subject_stats:
                subject_stats[error.subject] = {"count": 0, "categories": {}}
            subject_stats[error.subject]["count"] += 1
            
            if error.category not in subject_stats[error.subject]["categories"]:
                subject_stats[error.subject]["categories"][error.category] = 0
            subject_stats[error.subject]["categories"][error.category] += 1
        
        return subject_stats

class StudyHelperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("高中生学习助手")
        self.root.geometry("1400x750")
        self.root.resizable(True, True)
        
        # 保存原始窗口状态，用于退出全屏时恢复
        self.original_geometry = "1400x750"
        self.is_fullscreen = False
        
        # 密码设置 - 默认密码123456
        self.unlock_password = "123456"
        self.unlock_dialog = None  # 密码对话框引用
        
        # 学霸模式状态管理
        self.current_mode = tk.StringVar(value="normal")  # normal/study_mode
        self.running_study_task_id = None  # 正在进行的学霸模式任务ID
        self.countdown_label = None  # 倒计时显示标签
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("微软雅黑", 10), borderwidth=2, relief="solid")
        self.style.configure("TLabel", font=("微软雅黑", 10))
        self.style.configure("TNotebook.Tab", font=("微软雅黑", 10))
        self.style.configure("Header.TLabel", font=("微软雅黑", 12, "bold"))
        self.style.configure("StudyMode.TLabel", font=("微软雅黑", 11, "bold"), foreground="red")
        self.style.map("TButton",
                      foreground=[('active', 'blue'), ('pressed', 'red')],
                      background=[('active', '#e0e0e0')])
        
        # 创建模式切换栏（最上方）
        self.create_mode_switch_bar()
        
        self.helper = StudyHelper()
        self.create_main_interface()
        self.refresh_task_lists()
        self.refresh_error_list()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.handle_close)

    def create_mode_switch_bar(self):
        """创建顶部模式切换栏"""
        mode_frame = ttk.Frame(self.root, padding=5)
        mode_frame.pack(fill=tk.X, side=tk.TOP, anchor=tk.N)
        
        # 模式标题
        ttk.Label(mode_frame, text="当前模式：", font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=5)
        
        # 模式切换单选按钮
        self.normal_mode_radio = ttk.Radiobutton(
            mode_frame, text="普通模式", variable=self.current_mode, value="normal",
            command=self.switch_mode
        )
        self.normal_mode_radio.pack(side=tk.LEFT, padx=10)
        
        self.study_mode_radio = ttk.Radiobutton(
            mode_frame, text="学霸模式", variable=self.current_mode, value="study_mode",
            command=self.switch_mode
        )
        self.study_mode_radio.pack(side=tk.LEFT, padx=10)
        
        # 学霸模式状态显示（倒计时/任务信息）
        self.study_mode_status = ttk.Label(mode_frame, text="", style="StudyMode.TLabel")
        self.study_mode_status.pack(side=tk.LEFT, padx=20)
        
        # 锁定提示（学霸模式运行时显示）
        self.lock_label = ttk.Label(mode_frame, text="", style="StudyMode.TLabel")
        self.lock_label.pack(side=tk.RIGHT, padx=10)

    def switch_mode(self):
        """切换模式（普通/学霸）"""
        new_mode = self.current_mode.get()
        current_mode = self.current_mode.get()
        
        # 检查是否在学霸模式任务进行中且尝试切换到普通模式
        if new_mode == "normal" and self.running_study_task_id:
            task = next((t for t in self.helper.tasks if t.id == self.running_study_task_id), None)
            if task and task.start_time:
                # 计算已用时（分钟）
                used_time = (datetime.datetime.now() - task.start_time).total_seconds() / 60
                if used_time < task.time_limit:
                    messagebox.showerror("模式切换失败", "学霸模式任务尚未完成，无法切换到普通模式")
                    # 强制保持学霸模式
                    self.current_mode.set("study_mode")
                    return
        
        if new_mode == "study_mode":
            # 切换到学霸模式：检查是否有未完成的学霸任务
            pending_study_tasks = [t for t in self.helper.get_pending_tasks() if t.study_mode == "study_mode"]
            if pending_study_tasks:
                task = pending_study_tasks[0]
                self.running_study_task_id = task.id
                self.start_countdown(task)
                self.lock_label.config(text="⚠️ 学霸模式运行中，无法关闭窗口")
            else:
                messagebox.showinfo("提示", "学霸模式：新增任务将带有时间限制，需完成指定时间才能结束")
                self.lock_label.config(text="")
        else:
            # 切换到普通模式：解除锁定
            self.running_study_task_id = None
            if self.countdown_label:
                self.countdown_label.destroy()
                self.countdown_label = None
            self.study_mode_status.config(text="")
            self.lock_label.config(text="")
            # 退出全屏
            if self.is_fullscreen:
                self.exit_fullscreen()
        
        # 刷新任务列表（显示模式标识）
        self.refresh_task_lists()

    def start_countdown(self, task: Task):
        """启动学霸模式任务倒计时"""
        if not task.start_time:
            self.helper.start_study_mode_task(task.id)
            task.start_time = datetime.datetime.now()
        
        # 计算结束时间
        end_time = task.start_time + datetime.timedelta(minutes=task.time_limit)
        
        def update_countdown():
            if self.current_mode.get() != "study_mode" or self.running_study_task_id != task.id:
                return
            
            now = datetime.datetime.now()
            if now < end_time:
                remaining = end_time - now
                minutes = remaining.seconds // 60
                seconds = remaining.seconds % 60
                self.study_mode_status.config(
                    text=f"学霸任务：{task.subject} - 剩余时间：{minutes}分{seconds}秒"
                )
                self.root.after(1000, update_countdown)
            else:
                self.study_mode_status.config(
                    text=f"✅ 学霸任务：{task.subject} - 时间已达标，可标记完成"
                )
        
        update_countdown()

    def handle_close(self):
        """处理窗口关闭事件"""
        if self.running_study_task_id and self.current_mode.get() == "study_mode":
            # 记录关闭尝试
            attempts = self.helper.record_close_attempt(self.running_study_task_id)
            
            # 第一次尝试：警告
            if attempts <= 1:
                messagebox.showerror("禁止关闭", "学霸模式任务正在运行，需完成指定时间后才能关闭窗口")
            # 多次尝试：全屏警告
            else:
                messagebox.showerror("警告", f"已尝试关闭{attempts}次！继续尝试将强制全屏模式！")
                # 三次及以上尝试：强制全屏
                if attempts >= 3:
                    self.enter_fullscreen()
            return
        
        # 普通模式下正常关闭
        if messagebox.askyesno("确认关闭", "确定要退出学习助手吗？"):
            self.root.destroy()

    def enter_fullscreen(self):
        """进入全屏模式并覆盖其他窗口，添加密码锁定"""
        self.original_geometry = self.root.geometry()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)  # 窗口置顶
        self.is_fullscreen = True
        self.lock_label.config(text="⚠️ 强制全屏模式：完成任务或输入密码才能退出")
        
        # 显示密码解锁窗口
        self.show_unlock_dialog()

    def exit_fullscreen(self):
        """退出全屏模式，恢复原始窗口状态"""
        self.root.attributes("-fullscreen", False)
        self.root.attributes("-topmost", False)
        self.root.geometry(self.original_geometry)
        self.is_fullscreen = False
        
        # 关闭密码对话框
        if hasattr(self, 'unlock_dialog') and self.unlock_dialog and self.unlock_dialog.winfo_exists():
            self.unlock_dialog.destroy()
            self.unlock_dialog = None

    def show_unlock_dialog(self):
        """显示密码解锁窗口"""
        # 如果已经有解锁窗口则不重复创建
        if hasattr(self, 'unlock_dialog') and self.unlock_dialog and self.unlock_dialog.winfo_exists():
            return
            
        self.unlock_dialog = tk.Toplevel(self.root)
        self.unlock_dialog.title("解锁全屏模式")
        self.unlock_dialog.geometry("300x150")
        self.unlock_dialog.resizable(False, False)
        self.unlock_dialog.transient(self.root)
        self.unlock_dialog.grab_set()  # 模态窗口，阻止操作主窗口
        self.unlock_dialog.attributes("-topmost", True)  # 确保在最上层
        
        # 密码错误次数
        self.wrong_attempts = 0
        
        frame = ttk.Frame(self.unlock_dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请输入解锁密码:", font=("微软雅黑", 11)).grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=self.password_var, show="*", width=20, font=("微软雅黑", 11))
        password_entry.grid(row=1, column=0, pady=10, padx=(0, 10))
        password_entry.focus_set()  # 自动获取焦点
        
        unlock_btn = ttk.Button(frame, text="解锁", command=self.check_password)
        unlock_btn.grid(row=1, column=1)
        
        self.error_label = ttk.Label(frame, text="", foreground="red", font=("微软雅黑", 10))
        self.error_label.grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 绑定回车键解锁
        self.unlock_dialog.bind('<Return>', lambda event: self.check_password())

    def check_password(self):
        """验证解锁密码"""
        entered_password = self.password_var.get()
        
        if entered_password == self.unlock_password:
            self.exit_fullscreen()
            messagebox.showinfo("解锁成功", "全屏模式已解锁")
        else:
            self.wrong_attempts += 1
            remaining = 3 - self.wrong_attempts
            if remaining > 0:
                self.error_label.config(text=f"密码错误，还有{remaining}次机会")
                self.password_var.set("")
            else:
                self.error_label.config(text="密码错误次数过多，窗口将保持锁定")
                # 禁用输入和按钮
                for widget in self.unlock_dialog.winfo_children():
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Entry) or isinstance(child, ttk.Button):
                            child.configure(state="disabled")
                # 5秒后重新启用
                self.root.after(5000, self.reset_unlock_dialog)

    def reset_unlock_dialog(self):
        """重置解锁对话框"""
        if hasattr(self, 'unlock_dialog') and self.unlock_dialog and self.unlock_dialog.winfo_exists():
            self.password_var.set("")
            self.error_label.config(text="")
            self.wrong_attempts = 0
            # 重新启用输入和按钮
            for widget in self.unlock_dialog.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry) or isinstance(child, ttk.Button):
                        child.configure(state="normal")
            # 重新获取焦点
            for widget in self.unlock_dialog.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry):
                        child.focus_set()
                        break

    def create_main_interface(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.task_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.task_frame, text="任务管理")
        self.create_task_tab()
        
        self.error_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.error_frame, text="错题本")
        self.create_error_tab()
        
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="学习统计")
        self.create_stats_tab()

    def create_task_tab(self):
        top_frame = ttk.Frame(self.task_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(top_frame, text="添加新任务", command=self.show_add_task_dialog).pack(side=tk.LEFT, padx=5)
        
        paned_window = ttk.PanedWindow(self.task_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        pending_frame = ttk.LabelFrame(paned_window, text="未完成任务")
        paned_window.add(pending_frame, weight=1)
        
        # 新增模式列，显示任务所属模式
        columns = ("id", "mode", "subject", "content", "deadline", "priority", "actions")
        self.pending_tree = ttk.Treeview(pending_frame, columns=columns, show="headings")
        
        self.pending_tree.heading("id", text="ID")
        self.pending_tree.heading("mode", text="模式")
        self.pending_tree.heading("subject", text="科目")
        self.pending_tree.heading("content", text="内容")
        self.pending_tree.heading("deadline", text="截止日期")
        self.pending_tree.heading("priority", text="优先级")
        self.pending_tree.heading("actions", text="操作")
        
        self.pending_tree.column("id", width=70, anchor=tk.CENTER)
        self.pending_tree.column("mode", width=80, anchor=tk.CENTER)  # 模式列
        self.pending_tree.column("subject", width=90, anchor=tk.CENTER)
        self.pending_tree.column("content", width=250, anchor=tk.W)
        self.pending_tree.column("deadline", width=110, anchor=tk.CENTER)
        self.pending_tree.column("priority", width=90, anchor=tk.CENTER)
        self.pending_tree.column("actions", width=160, anchor=tk.CENTER)  # 增加操作列宽度（新增开始按钮）
        
        pending_scroll = ttk.Scrollbar(pending_frame, orient=tk.VERTICAL, command=self.pending_tree.yview)
        self.pending_tree.configure(yscrollcommand=pending_scroll.set)
        
        pending_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pending_tree.pack(fill=tk.BOTH, expand=True)
        
        completed_frame = ttk.LabelFrame(paned_window, text="已完成任务")
        paned_window.add(completed_frame, weight=1)
        
        self.completed_tree = ttk.Treeview(completed_frame, columns=columns, show="headings")
        self.completed_tree.heading("id", text="ID")
        self.completed_tree.heading("mode", text="模式")
        self.completed_tree.heading("subject", text="科目")
        self.completed_tree.heading("content", text="内容")
        self.completed_tree.heading("deadline", text="截止日期")
        self.completed_tree.heading("priority", text="优先级")
        self.completed_tree.heading("actions", text="操作")
        
        self.completed_tree.column("id", width=70, anchor=tk.CENTER)
        self.completed_tree.column("mode", width=80, anchor=tk.CENTER)
        self.completed_tree.column("subject", width=90, anchor=tk.CENTER)
        self.completed_tree.column("content", width=250, anchor=tk.W)
        self.completed_tree.column("deadline", width=110, anchor=tk.CENTER)
        self.completed_tree.column("priority", width=90, anchor=tk.CENTER)
        self.completed_tree.column("actions", width=140, anchor=tk.CENTER)
        
        completed_scroll = ttk.Scrollbar(completed_frame, orient=tk.VERTICAL, command=self.completed_tree.yview)
        self.completed_tree.configure(yscrollcommand=completed_scroll.set)
        
        completed_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.completed_tree.pack(fill=tk.BOTH, expand=True)

    def create_error_tab(self):
        top_frame = ttk.Frame(self.error_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(top_frame, text="添加新错题", command=self.show_add_error_dialog).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(top_frame, text="按科目筛选:").pack(side=tk.LEFT, padx=5)
        self.error_subject_var = tk.StringVar()
        # 科目筛选下拉框：包含常见科目
        self.error_subject_combobox = ttk.Combobox(
            top_frame, 
            textvariable=self.error_subject_var,
            state="readonly",
            width=10,
            values=["所有科目"] + COMMON_SUBJECTS
        )
        self.error_subject_combobox.pack(side=tk.LEFT, padx=5)
        self.error_subject_combobox.current(0)
        
        ttk.Button(top_frame, text="刷新列表", command=self.refresh_error_list).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.Frame(self.error_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("id", "subject", "question", "category", "review_count", "actions")
        self.error_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        self.error_tree.heading("id", text="ID")
        self.error_tree.heading("subject", text="科目")
        self.error_tree.heading("question", text="题目")
        self.error_tree.heading("category", text="知识点")
        self.error_tree.heading("review_count", text="复习次数")
        self.error_tree.heading("actions", text="操作")
        
        self.error_tree.column("id", width=80, anchor=tk.CENTER)
        self.error_tree.column("subject", width=80, anchor=tk.CENTER)
        self.error_tree.column("question", width=500, anchor=tk.W)
        self.error_tree.column("category", width=100, anchor=tk.CENTER)
        self.error_tree.column("review_count", width=80, anchor=tk.CENTER)
        self.error_tree.column("actions", width=180, anchor=tk.CENTER)
        
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.error_tree.yview)
        self.error_tree.configure(yscrollcommand=scroll.set)
        
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.error_tree.pack(fill=tk.BOTH, expand=True)
        
        self.error_tree.bind("<Double-1>", self.show_error_details)

    def create_stats_tab(self):
        top_frame = ttk.Frame(self.stats_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        task_stats_frame = ttk.LabelFrame(top_frame, text="任务统计")
        task_stats_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        ttk.Label(task_stats_frame, text="统计天数:").pack(side=tk.LEFT, padx=5)
        self.stats_days_var = tk.StringVar(value="7")
        days_combobox = ttk.Combobox(
            task_stats_frame, 
            textvariable=self.stats_days_var,
            values=["7", "14", "30", "90"],
            width=5,
            state="readonly"
        )
        days_combobox.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(task_stats_frame, text="生成任务报告", command=self.generate_task_report).pack(side=tk.LEFT, padx=5)
        
        error_stats_frame = ttk.LabelFrame(top_frame, text="错题统计")
        error_stats_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.X, expand=True)
        
        ttk.Button(error_stats_frame, text="生成错题报告", command=self.generate_error_report).pack(side=tk.LEFT, padx=5)
        
        self.stats_display_frame = ttk.Frame(self.stats_frame)
        self.stats_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.stats_info_label = ttk.Label(
            self.stats_display_frame, 
            text="请选择统计类型并点击生成报告按钮",
            font=("微软雅黑", 12)
        )
        self.stats_info_label.pack(expand=True)
        
        self.chart_frame = None

    def refresh_task_lists(self):
        """刷新任务列表（显示模式标识和学霸任务操作）"""
        # 清空列表
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)
        for item in self.completed_tree.get_children():
            self.completed_tree.delete(item)
        
        # 填充未完成任务
        pending_tasks = self.helper.get_pending_tasks()
        for task in pending_tasks:
            mode_text = "学霸" if task.study_mode == "study_mode" else "普通"
            priority_stars = "★" * task.priority + "☆" * (5 - task.priority)
            display_content = task.content[:30] + "..." if len(task.content) > 30 else task.content
            
            # 学霸模式任务显示"开始/完成/删除"，普通模式显示"完成/删除"
            if task.study_mode == "study_mode":
                actions = "开始 | 完成 | 删除"
            else:
                actions = "完成 | 删除"
            
            self.pending_tree.insert("", tk.END, values=(
                task.id[-6:],
                mode_text,
                task.subject,
                display_content,
                task.deadline,
                priority_stars,
                actions
            ))
        
        # 填充已完成任务
        completed_tasks = self.helper.get_completed_tasks()
        for task in completed_tasks:
            mode_text = "学霸" if task.study_mode == "study_mode" else "普通"
            priority_stars = "★" * task.priority + "☆" * (5 - task.priority)
            display_content = task.content[:30] + "..." if len(task.content) > 30 else task.content
            
            self.completed_tree.insert("", tk.END, values=(
                task.id[-6:],
                mode_text,
                task.subject,
                display_content,
                task.deadline,
                priority_stars,
                "删除"
            ))
        
        # 绑定事件
        self.pending_tree.bind(f"<<TreeviewSelect>>", self.on_task_select)
        self.completed_tree.bind(f"<<TreeviewSelect>>", self.on_task_select)

    def on_task_select(self, event):
        """处理任务操作（新增学霸任务开始功能）"""
        tree = event.widget
        selected_items = tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        column = tree.identify_column(tree.winfo_pointerx() - tree.winfo_rootx())
        item_values = tree.item(item, "values")
        short_id = item_values[0]
        full_id = next((t.id for t in self.helper.tasks if t.id.endswith(short_id)), None)
        
        if not full_id:
            return
            
        if column == "#7":  # 操作列（新增模式列后索引变为7）
            x, y, width, height = tree.bbox(item, column)
            click_x = tree.winfo_pointerx() - tree.winfo_rootx()
            task = next((t for t in self.helper.tasks if t.id == full_id), None)
            
            if not task:
                return
            
            # 学霸模式任务：3个操作（开始/完成/删除）
            if task.study_mode == "study_mode":
                if click_x < x + width/3:  # 开始按钮
                    self.helper.start_study_mode_task(full_id)
                    self.running_study_task_id = full_id
                    self.start_countdown(task)
                    self.lock_label.config(text="⚠️ 学霸模式运行中，无法关闭窗口")
                    messagebox.showinfo("成功", "学霸模式任务已开始计时")
                    self.refresh_task_lists()
                elif click_x < x + 2*width/3:  # 完成按钮
                    if self.helper.complete_task(full_id):
                        messagebox.showinfo("成功", "任务已标记为完成")
                        self.running_study_task_id = None
                        self.study_mode_status.config(text="")
                        self.lock_label.config(text="")
                        # 如果处于全屏模式，退出全屏
                        if self.is_fullscreen:
                            self.exit_fullscreen()
                        self.refresh_task_lists()
                else:  # 删除按钮
                    if messagebox.askyesno("确认删除", "确定要删除这个学霸任务吗？"):
                        self.helper.delete_task(full_id)
                        self.running_study_task_id = None
                        self.study_mode_status.config(text="")
                        self.lock_label.config(text="")
                        # 如果处于全屏模式，退出全屏
                        if self.is_fullscreen:
                            self.exit_fullscreen()
                        messagebox.showinfo("成功", "任务已删除")
                        self.refresh_task_lists()
            # 普通模式任务：2个操作（完成/删除）
            else:
                if click_x < x + width/2:  # 完成按钮
                    if self.helper.complete_task(full_id):
                        messagebox.showinfo("成功", "任务已标记为完成")
                        self.refresh_task_lists()
                else:  # 删除按钮
                    if messagebox.askyesno("确认删除", "确定要删除这个任务吗？"):
                        self.helper.delete_task(full_id)
                        messagebox.showinfo("成功", "任务已删除")
                        self.refresh_task_lists()

    # 科目选择优化：支持下拉选择+手动输入
    def show_add_task_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("添加新任务")
        dialog.geometry("700x550")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 学霸模式下禁止关闭对话框
        def handle_dialog_close():
            if self.current_mode.get() == "study_mode":
                messagebox.showerror("禁止关闭", "学霸模式下必须完成任务创建")
                return
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", handle_dialog_close)
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 科目：下拉选择+手动输入
        ttk.Label(frame, text="科目:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.task_subject_var = tk.StringVar()
        # 可编辑的下拉框（支持选择/手动输入）
        self.task_subject_combobox = ttk.Combobox(
            frame,
            textvariable=self.task_subject_var,
            values=COMMON_SUBJECTS,
            width=50,
            state="normal"  # 允许手动输入
        )
        self.task_subject_combobox.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 学霸模式时间限制（当前模式为学霸时显示）
        self.time_limit_frame = ttk.Frame(frame)
        study_mode = self.current_mode.get()
        if study_mode == "study_mode":
            ttk.Label(self.time_limit_frame, text="时间限制（分钟）:").grid(row=0, column=0, sticky=tk.W, pady=5)
            
            # 时间选择框架（下拉+手动输入）
            time_frame = ttk.Frame(self.time_limit_frame)
            time_frame.grid(row=0, column=1, sticky=tk.W)
            
            self.time_limit_var = tk.StringVar(value="30")
            # 下拉选择常用时间
            ttk.Combobox(
                time_frame,
                textvariable=self.time_limit_var,
                values=["15", "30", "45", "60", "90", "120"],
                width=8,
                state="readonly"
            ).pack(side=tk.LEFT, padx=5)
            
            # 手动输入框
            ttk.Label(time_frame, text="或手动输入:").pack(side=tk.LEFT, padx=5)
            self.time_limit_manual = tk.StringVar()
            ttk.Entry(time_frame, textvariable=self.time_limit_manual, width=8).pack(side=tk.LEFT, padx=5)
            
            # 绑定手动输入事件
            def update_time_from_manual(*args):
                if self.time_limit_manual.get():
                    try:
                        # 验证输入是否为数字
                        int(self.time_limit_manual.get())
                        self.time_limit_var.set("")
                    except ValueError:
                        messagebox.showerror("输入错误", "请输入有效的分钟数")
                        self.time_limit_manual.set("")
            
            self.time_limit_manual.trace_add("write", update_time_from_manual)
            
            # 绑定下拉选择事件
            def update_time_from_combobox(*args):
                if self.time_limit_var.get():
                    self.time_limit_manual.set("")
            
            self.time_limit_var.trace_add("write", update_time_from_combobox)
            
        self.time_limit_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Label(frame, text="任务内容:").grid(row=2, column=0, sticky=tk.NW, pady=5)
        content_text = scrolledtext.ScrolledText(frame, width=60, height=12, wrap=tk.WORD, font=("微软雅黑", 10))
        content_text.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 自动识别任务信息
        def auto_recognize(*args):
            content = content_text.get("1.0", tk.END).strip()
            if content:
                # 识别科目
                for subj in COMMON_SUBJECTS:
                    if subj in content and not self.task_subject_var.get():
                        self.task_subject_var.set(subj)
                        break
        
        content_text.bind("<KeyRelease>", auto_recognize)
        
        ttk.Label(frame, text="截止日期 (YYYY-MM-DD):").grid(row=3, column=0, sticky=tk.W, pady=5)
        deadline_var = tk.StringVar()
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        deadline_var.set(tomorrow)
        ttk.Entry(frame, textvariable=deadline_var, width=20).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="优先级 (1-5):").grid(row=4, column=0, sticky=tk.W, pady=5)
        priority_var = tk.IntVar(value=3)
        ttk.Combobox(
            frame, 
            textvariable=priority_var,
            values=[1, 2, 3, 4, 5],
            width=5,
            state="readonly"
        ).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        def save_task():
            subject = self.task_subject_var.get().strip()
            content = content_text.get("1.0", tk.END).strip()
            deadline = deadline_var.get().strip()
            priority = priority_var.get()
            
            if not subject or not content or not deadline:
                messagebox.showerror("错误", "科目、任务内容和截止日期不能为空")
                return
            
            # 学霸模式任务添加时间限制
            study_mode = self.current_mode.get()
            time_limit = 0
            
            if study_mode == "study_mode":
                # 获取时间限制（优先手动输入）
                if self.time_limit_manual.get():
                    try:
                        time_limit = int(self.time_limit_manual.get())
                        if time_limit <= 0:
                            raise ValueError
                    except ValueError:
                        messagebox.showerror("错误", "请输入有效的正整数分钟数")
                        return
                elif self.time_limit_var.get():
                    time_limit = int(self.time_limit_var.get())
                else:
                    messagebox.showerror("错误", "请选择或输入时间限制")
                    return
            
            try:
                datetime.datetime.strptime(deadline, "%Y-%m-%d")
                self.helper.add_task(subject, content, deadline, priority, study_mode, time_limit)
                messagebox.showinfo("成功", f"{study_mode == 'study_mode' and '学霸模式' or '普通'}任务添加成功")
                dialog.destroy()
                self.refresh_task_lists()
            except ValueError:
                messagebox.showerror("错误", "日期格式不正确，请使用YYYY-MM-DD")
        
        ttk.Button(btn_frame, text="保存", command=save_task).pack(side=tk.LEFT, padx=10)
        
        # 学霸模式下隐藏取消按钮
        if study_mode != "study_mode":
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    # 错题科目同样支持选择+手动输入
    def show_add_error_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("添加新错题")
        dialog.geometry("750x650")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 学霸模式下禁止关闭对话框
        def handle_dialog_close():
            if self.current_mode.get() == "study_mode" and self.running_study_task_id:
                messagebox.showerror("禁止关闭", "学霸模式任务进行中，不能关闭对话框")
                return
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", handle_dialog_close)
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 科目：下拉选择+手动输入
        ttk.Label(frame, text="科目:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.error_subject_input_var = tk.StringVar()
        self.error_subject_input_combobox = ttk.Combobox(
            frame,
            textvariable=self.error_subject_input_var,
            values=COMMON_SUBJECTS,
            width=50,
            state="normal"  # 允许手动输入
        )
        self.error_subject_input_combobox.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="题目:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        question_text = scrolledtext.ScrolledText(frame, width=60, height=10, wrap=tk.WORD, font=("微软雅黑", 10))
        question_text.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 自动识别科目
        def auto_recognize(*args):
            question = question_text.get("1.0", tk.END).strip()
            if question and not self.error_subject_input_var.get():
                for subj in COMMON_SUBJECTS:
                    if subj in question:
                        self.error_subject_input_var.set(subj)
                        break
        
        question_text.bind("<KeyRelease>", auto_recognize)
        
        ttk.Label(frame, text="正确答案:").grid(row=2, column=0, sticky=tk.NW, pady=5)
        answer_text = scrolledtext.ScrolledText(frame, width=60, height=10, wrap=tk.WORD, font=("微软雅黑", 10))
        answer_text.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="错误原因:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        mistake_text = scrolledtext.ScrolledText(frame, width=60, height=5, wrap=tk.WORD, font=("微软雅黑", 10))
        mistake_text.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="知识点/类别:").grid(row=4, column=0, sticky=tk.W, pady=5)
        category_var = tk.StringVar()
        ttk.Entry(frame, textvariable=category_var, width=50).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        def save_error():
            subject = self.error_subject_input_var.get().strip()
            question = question_text.get("1.0", tk.END).strip()
            answer = answer_text.get("1.0", tk.END).strip()
            mistake = mistake_text.get("1.0", tk.END).strip()
            category = category_var.get().strip()
            
            if not subject or not question or not answer or not mistake:
                messagebox.showerror("错误", "科目、题目、正确答案和错误原因不能为空")
                return
                
            self.helper.add_error(subject, question, answer, mistake, category)
            messagebox.showinfo("成功", "错题添加成功")
            dialog.destroy()
            self.refresh_error_list()
            self.update_error_subjects()
        
        ttk.Button(btn_frame, text="保存", command=save_error).pack(side=tk.LEFT, padx=10)
        
        # 学霸模式下隐藏取消按钮
        if not (self.current_mode.get() == "study_mode" and self.running_study_task_id):
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    # 以下为原有方法，保持不变
    def update_error_subjects(self):
        subjects = list(set([error.subject for error in self.helper.errors]))
        subjects.insert(0, "所有科目")
        self.error_subject_combobox['values'] = subjects
        self.error_subject_combobox.current(0)

    def refresh_error_list(self):
        for item in self.error_tree.get_children():
            self.error_tree.delete(item)
        
        selected_subject = self.error_subject_var.get()
        subject = selected_subject if selected_subject != "所有科目" else ""
        
        errors = self.helper.get_errors_by_subject(subject)
        
        for error in errors:
            display_question = error.question[:60] + "..." if len(error.question) > 60 else error.question
            self.error_tree.insert("", tk.END, values=(
                error.id[-6:],
                error.subject,
                display_question,
                error.category,
                error.review_count,
                "复习 | 删除 | 详情"
            ))
        
        self.error_tree.bind(f"<<TreeviewSelect>>", self.on_error_select)

    def on_error_select(self, event):
        tree = event.widget
        selected_items = tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        column = tree.identify_column(tree.winfo_pointerx() - tree.winfo_rootx())
        item_values = tree.item(item, "values")
        
        short_id = item_values[0]
        full_id = next((e.id for e in self.helper.errors if e.id.endswith(short_id)), None)
        
        if not full_id:
            return
            
        if column == "#6":
            x, y, width, height = tree.bbox(item, column)
            click_x = tree.winfo_pointerx() - tree.winfo_rootx()
            
            if click_x < x + width/3:
                self.helper.review_error(full_id)
                messagebox.showinfo("成功", "已记录一次复习")
                self.refresh_error_list()
            elif click_x < x + 2*width/3:
                if messagebox.askyesno("确认删除", "确定要删除这道错题吗？"):
                    self.helper.delete_error(full_id)
                    messagebox.showinfo("成功", "错题已删除")
                    self.refresh_error_list()
                    self.update_error_subjects()
            else:
                self.show_error_details_by_id(full_id)

    def show_error_details(self, event):
        tree = event.widget
        selected_items = tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        item_values = tree.item(item, "values")
        
        short_id = item_values[0]
        full_id = next((e.id for e in self.helper.errors if e.id.endswith(short_id)), None)
        
        if full_id:
            self.show_error_details_by_id(full_id)

    def show_error_details_by_id(self, error_id):
        error = next((e for e in self.helper.errors if e.id == error_id), None)
        if not error:
            return
            
        detail_window = tk.Toplevel(self.root)
        detail_window.title("错题详情")
        detail_window.geometry("700x550")
        detail_window.resizable(False, False)
        detail_window.transient(self.root)
        detail_window.grab_set()
        
        # 学霸模式下禁止关闭详情窗口
        def handle_detail_close():
            if self.current_mode.get() == "study_mode" and self.running_study_task_id:
                messagebox.showerror("禁止关闭", "学霸模式任务进行中，不能关闭详情窗口")
                return
            detail_window.destroy()
            
        detail_window.protocol("WM_DELETE_WINDOW", handle_detail_close)
        
        frame = ttk.Frame(detail_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="科目:", style="Header.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=error.subject).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="题目:", style="Header.TLabel").grid(row=1, column=0, sticky=tk.NW, pady=5)
        question_text = scrolledtext.ScrolledText(frame, width=60, height=10, wrap=tk.WORD)
        question_text.grid(row=1, column=1, sticky=tk.W, pady=5)
        question_text.insert(tk.END, error.question)
        question_text.config(state=tk.DISABLED)
        
        ttk.Label(frame, text="正确答案:", style="Header.TLabel").grid(row=2, column=0, sticky=tk.NW, pady=5)
        answer_text = scrolledtext.ScrolledText(frame, width=60, height=10, wrap=tk.WORD)
        answer_text.grid(row=2, column=1, sticky=tk.W, pady=5)
        answer_text.insert(tk.END, error.answer)
        answer_text.config(state=tk.DISABLED)
        
        ttk.Label(frame, text="错误原因:", style="Header.TLabel").grid(row=3, column=0, sticky=tk.NW, pady=5)
        mistake_text = scrolledtext.ScrolledText(frame, width=60, height=5, wrap=tk.WORD)
        mistake_text.grid(row=3, column=1, sticky=tk.W, pady=5)
        mistake_text.insert(tk.END, error.mistake)
        mistake_text.config(state=tk.DISABLED)
        
        ttk.Label(frame, text="知识点:", style="Header.TLabel").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=error.category).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="复习次数:", style="Header.TLabel").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=str(error.review_count)).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="标记为复习", 
                  command=lambda: [self.helper.review_error(error_id), 
                                  messagebox.showinfo("成功", "已记录一次复习"),
                                  detail_window.destroy(),
                                  self.refresh_error_list()]).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="删除", 
                  command=lambda: [
                      detail_window.destroy(),
                      self.helper.delete_error(error_id),
                      messagebox.showinfo("成功", "错题已删除"),
                      self.refresh_error_list(),
                      self.update_error_subjects()
                  ]).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="关闭", command=handle_detail_close).pack(side=tk.LEFT, padx=10)

    def _auto_recognize_task_info(self, content):
        subject_patterns = {
            '数学': ['数学', '代数', '几何', '函数', '方程'],
            '语文': ['语文', '作文', '阅读', '文言文'],
            '英语': ['英语', '单词', '语法', '阅读', '听力'],
            '物理': ['物理', '力学', '电学', '光学'],
            '化学': ['化学', '元素', '反应', '方程式']
        }
        
        subject = ""
        for subj, keywords in subject_patterns.items():
            for keyword in keywords:
                if keyword in content:
                    subject = subj
                    break
            if subject:
                break
                
        date_pattern = r'\b(?:\d{4}-\d{2}-\d{2}|\d{2}-\d{2})\b'
        dates = re.findall(date_pattern, content)
        deadline = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if dates:
            try:
                if len(dates[0]) == 5:
                    year = datetime.datetime.now().year
                    deadline = f"{year}-{dates[0]}"
                else:
                    deadline = dates[0]
                datetime.datetime.strptime(deadline, "%Y-%m-%d")
            except:
                pass
                
        priority = 3
        if '紧急' in content or '重要' in content or '高' in content:
            priority = 5
        elif '一般' in content or '中' in content:
            priority = 3
        elif '低' in content:
            priority = 1
            
        return subject, deadline, priority

    def _auto_recognize_error_info(self, question):
        subject_patterns = {
            '数学': ['数学', '计算', '证明', '图形', '公式'],
            '语文': ['词语', '句子', '文章', '作者', '朝代'],
            '英语': ['单词', '语法', '时态', '阅读', '听力'],
            '物理': ['力', '电', '光', '运动', '能量'],
            '化学': ['元素', '反应', '实验', '物质', '周期表']
        }
        
        subject = ""
        for subj, keywords in subject_patterns.items():
            for keyword in keywords:
                if keyword in question:
                    subject = subj
                    break
            if subject:
                break
                
        category = ""
        math_categories = ['代数', '几何', '函数', '概率', '统计']
        for cat in math_categories:
            if cat in question and subject == '数学':
                category = cat
                break
                
        return subject, category

    def generate_task_report(self):
        for widget in self.stats_display_frame.winfo_children():
            widget.destroy()
            
        days = int(self.stats_days_var.get())
        subject_stats, total, completed, completion_rate = self.helper.get_task_stats(days)
        
        stats_text = f"{days}天内任务统计：\n"
        stats_text += f"总任务数：{total}\n"
        stats_text += f"已完成：{completed}\n"
        stats_text += f"完成率：{completion_rate:.1f}%\n\n"
        
        for subject, data in subject_stats.items():
            stats_text += f"{subject}：总{data['total']}，已完成{data['completed']}，完成率{data['completed']/data['total']*100:.1f}%\n"
        
        ttk.Label(self.stats_display_frame, text=stats_text, font=("微软雅黑", 10), justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=10)
        
        if subject_stats:
            fig, ax = plt.subplots(figsize=(8, 4))
            
            plt.rcParams["font.size"] = 10
            plt.rcParams["font.family"] = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC', 'sans-serif']
            
            subjects = list(subject_stats.keys())
            completed = [subject_stats[s]['completed'] for s in subjects]
            pending = [subject_stats[s]['total'] - subject_stats[s]['completed'] for s in subjects]
            
            x = range(len(subjects))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], completed, width, label='已完成')
            ax.bar([i + width/2 for i in x], pending, width, label='未完成')
            
            ax.set_xlabel('科目')
            ax.set_ylabel('任务数量')
            ax.set_title(f'{days}天内任务完成情况')
            ax.set_xticks(x)
            ax.set_xticklabels(subjects)
            ax.legend()
            
            canvas = FigureCanvasTkAgg(fig, master=self.stats_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def generate_error_report(self):
        for widget in self.stats_display_frame.winfo_children():
            widget.destroy()
            
        error_stats = self.helper.get_error_stats()
        
        if not error_stats:
            ttk.Label(self.stats_display_frame, text="暂无错题数据", font=("微软雅黑", 12)).pack(expand=True)
            return
            
        stats_text = "错题统计：\n\n"
        total_errors = sum(data["count"] for data in error_stats.values())
        stats_text += f"总错题数：{total_errors}\n\n"
        
        for subject, data in error_stats.items():
            stats_text += f"{subject}：{data['count']}题\n"
            for category, count in data['categories'].items():
                stats_text += f"  - {category}：{count}题\n"
        
        ttk.Label(self.stats_display_frame, text=stats_text, font=("微软雅黑", 10), justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=10)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        plt.rcParams["font.size"] = 10
        plt.rcParams["font.family"] = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC', 'sans-serif']
        
        subjects = list(error_stats.keys())
        counts = [error_stats[s]['count'] for s in subjects]
        ax1.pie(counts, labels=subjects, autopct='%1.1f%%', startangle=90)
        ax1.set_title('错题科目分布')
        
        first_subject = subjects[0]
        categories = list(error_stats[first_subject]['categories'].keys())
        cat_counts = list(error_stats[first_subject]['categories'].values())
        ax2.bar(categories, cat_counts)
        ax2.set_title(f'{first_subject}知识点分布')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.stats_display_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

def verify_code():
    """验证代码核心功能是否正常"""
    try:
        # 验证核心类是否存在
        assert 'Task' in globals(), "Task类未定义"
        assert '错题' in globals(), "错题类未定义"
        assert 'StudyHelper' in globals(), "StudyHelper类未定义"
        assert 'StudyHelperGUI' in globals(), "StudyHelperGUI类未定义"
        
        # 验证Task类基本功能
        task = Task("数学", "测试任务", "2023-12-31", 3)
        assert task.id.startswith("task_"), "Task ID生成错误"
        assert task.completed is False, "Task初始状态错误"
        assert task.complete() is True, "Task完成功能错误"
        assert task.completed is True, "Task完成状态更新错误"
        
        # 验证错题类基本功能
        error = 错题("数学", "1+1=?", "2", "计算错误", "基础运算")
        assert error.id.startswith("error_"), "错题ID生成错误"
        assert error.review_count == 0, "错题初始复习次数错误"
        error.review()
        assert error.review_count == 1, "错题复习功能错误"
        
        # 验证StudyHelper基本功能
        helper = StudyHelper("test_data")
        assert len(helper.get_pending_tasks()) == 0, "StudyHelper初始任务列表错误"
        new_task = helper.add_task("语文", "测试任务2", "2023-12-31")
        assert len(helper.get_pending_tasks()) == 1, "StudyHelper添加任务错误"
        assert helper.delete_task(new_task.id) is True, "StudyHelper删除任务错误"
        
        print("代码验证通过")
        return True
    except AssertionError as e:
        print(f"代码验证失败: {e}")
        return False
    except Exception as e:
        print(f"代码验证过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    # 先执行代码验证
    verify_code()  # 仅执行验证，不根据结果退出
    
    # 无论验证结果如何，都正常启动程序
    root = tk.Tk()
    app = StudyHelperGUI(root)
    root.mainloop()

