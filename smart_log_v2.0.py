import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import pandas as pd
from pandas import DateOffset
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

import matplotlib as mpl
mpl.rcParams['font.family'] = 'Microsoft YaHei'  # 微软雅黑
mpl.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

from matplotlib.dates import DateFormatter  # 修改时间格式




class LogAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart_log_日志数据分析工具 Powered by Zhou BY v2.0")
        self.root.geometry("1200x800")

         # 分离两种模式的参数存储
        self.selected_param_24h = tk.StringVar()
        self.selected_param_lt = tk.StringVar()
        
        self.secondary_params = []         # 24小时次要参数
        self.secondary_params_lt = []      # 长期次要参数

        # 初始化模式控制变量 ▼▲▼▲▼▲
        self.current_mode = tk.StringVar(value="24h")  # 当前模式：24h/longterm

        # 创建主容器框架
        self.container_frame = ttk.Frame(root)
        self.container_frame.pack(fill=tk.BOTH, expand=True)

        # ====== 公共变量初始化 ======
        self.selected_folder = tk.StringVar()
        self.start_time = tk.StringVar()
        self.end_time = tk.StringVar()
        self.selected_param = tk.StringVar()
        self.file_pattern = re.compile(r"^\d{10}\.csv$")
        self.file_cache = {}
        self.last_scan_folder = ""

        # 新增存储结构
        self.log_scale_settings = {}  # 存储各参数的对数坐标配置（参数名: 是否启用）

        # 字体和样式配置
        self.ctrl_font = ('Microsoft YaHei', 18)
        self.label_width = 15
    

        self.figure_24h = None
        self.ax_main = None
        self.ax_secondary = None
        self.figure_lt = None
        self.ax_lt = None
        
        # 新增事件管理变量 ▼▼▼
        self._event_cids = {'24h': None, 'longterm': None}

        # 创建两种模式的容器（新增）
        self.create_24h_container()   # 创建24小时模式布局
        self.create_longterm_container()  # 创建长期模式布局
    
        # 默认显示24小时布局
        self.show_container("24h")

        # 界面组件创建（拆分到不同方法）▼▲▼▲▼▲
        self.create_common_widgets()  # 创建公共组件
        self.init_24h_panel()         # 初始化24小时面板
        self.init_longterm_panel()    # 初始化长期面板
        self.switch_control_panel("24h")  # 默认显示24h面板

        # ====== 坐标系及绘图初始化 ======
        self.ax_main = None
        #self.ax_secondary = []
        self.active_axes = []
        # 新增存储变量
        self.axes_24h = {
            'main': None,
            'secondary': []
        }
        self.axes_longterm = {
            'main': None,
            'secondary': []
        }
        
        self.date_files = {}      # 长期模式文件结构
        self.file_cache = {}      # 24小时模式缓存
        self.last_scan_folder = ""
        
        self.color_cycle = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        if len(self.color_cycle) < 6:  # 确保最少有6种颜色
            self.color_cycle += plt.cm.tab20.colors[:6-len(self.color_cycle)]
        mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=self.color_cycle)
        
    
        # 长期模式特殊参数 ▼▲▼▲▼▲
        self.secondary_params_longterm = []  # 长期模式的次要参数
        self.param_combobox_longterm = None  # 长期模式参数下拉框

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def is_valid_date_folder(self, folder_name):
        """检查是否符合yyyy_mm_dd格式"""
        return re.match(r"^\d{4}_\d{2}_\d{2}$", folder_name) is not None

    def create_24h_container(self):
        """创建24小时模式的水平分栏容器"""
        # 创建水平分割容器
        self.paned_24h = ttk.PanedWindow(self.container_frame, orient=tk.HORIZONTAL)
    
        # 左边控制面板区域（保留原control_panel_24h）
        self.control_panel_24h = ttk.LabelFrame(self.paned_24h, text="24小时分析参数")
        self.paned_24h.add(self.control_panel_24h, weight=1)  # 占1/4宽度
    
        # 右边可视化区域（使用专属viz_frame）
        self.viz_frame_24h = ttk.Frame(self.paned_24h)
        self.paned_24h.add(self.viz_frame_24h, weight=3)  # 占3/4宽度
    
        # 初始化组件（原init_24h_panel逻辑无需修改）
        # 初始化可视化区域（新增方法）
        #self.init_24h_viz()

    def create_longterm_container(self):
        """创建长期模式的垂直分栏容器"""
        # 创建垂直分割容器
        self.paned_longterm = ttk.PanedWindow(self.container_frame, orient=tk.VERTICAL)
   
        # 顶部控制面板（使用新建的control_panel_longterm）
        self.control_panel_longterm = ttk.LabelFrame(self.paned_longterm, text="长期分析参数")
        self.paned_longterm.add(self.control_panel_longterm, weight=1)  # 占1/4高度
    
        # 底部可视化区域（独立于原viz_frame）
        self.viz_frame_longterm = ttk.Frame(self.paned_longterm)
        self.paned_longterm.add(self.viz_frame_longterm, weight=3)  # 占3/4高度
    
        # 初始化长期面板组件（需修改后的init_longterm_panel）
        #self.init_longterm_panel()
        # 初始化长期模式可视化（新增方法）
        #self.init_longterm_viz()

    def show_container(self, mode):
        """智能初始化模式的图形容器（核心修复）"""
        # 确保旧容器完全解绑
        self.paned_24h.pack_forget()  
        self.paned_longterm.pack_forget()

        # 根据模式动态初始化
        if mode == "24h":
            if not self.figure_24h:
                self.init_24h_viz()  # 首次显示时才初始化24h图表
            self.paned_24h.pack(fill=tk.BOTH, expand=True)
            self.current_mode.set("24h")
        else:
            if not self.figure_lt:
                self.init_longterm_viz() # 首次显示时才初始化长期图表
            self.paned_longterm.pack(fill=tk.BOTH, expand=True)
            self.current_mode.set("longterm")

        # 自动创建新figure（冗余保护）
        root.update_idletasks()  # 强制Tkinter更新显示状态
        self.bind_right_click()


    def init_24h_panel(self):
        """紧凑布局的24小时控制面板"""
        self.control_panel_24h.grid_remove()
    
        # 主网格布局容器 ▼▼▼ 采用Grid布局控制行间距
        content_frame = ttk.Frame(self.control_panel_24h)
        content_frame.pack(padx=10, pady=5, fill=tk.BOTH)
        content_frame.grid_columnconfigure(0, weight=1)

        # ====== 按行定义组件 ======
        current_row = 0
    
        # ---- 第一行：文件夹选择 ----
        folder_frame = ttk.Frame(content_frame)
        folder_frame.grid(row=current_row, column=0, pady=2, sticky='ew')
        current_row +=1
    
        ttk.Label(folder_frame, text="日志文件夹", 
                 width=self.label_width, 
                 font=self.ctrl_font).pack(side=tk.LEFT)
        ttk.Entry(folder_frame, 
                 textvariable=self.selected_folder, 
                 font=self.ctrl_font).pack(side=tk.LEFT, expand=1, fill=tk.X, padx=5)
        ttk.Button(folder_frame, text="浏览", 
                  command=self.select_folder).pack(side=tk.LEFT)

        # ---- 第二行：时间选择（紧凑双列布局） ----
        time_frame = ttk.Frame(content_frame)
        time_frame.grid(row=current_row, column=0, pady=2, sticky='ew')
        current_row +=1
    
        # 网格列配置 ▼▼▼
        #time_frame.grid_columnconfigure(1, weight=1)
        # 新增左侧占位列 ▼▼ 添加第0列并配置权重 ▼▼
        time_frame.grid_columnconfigure(0, minsize=30)  # 新增左侧缓冲区
        time_frame.grid_columnconfigure(1, minsize=40)    # 标签固定宽度
        time_frame.grid_columnconfigure(2, weight=1)    # 输入框扩展

        # Start time
        ttk.Label(time_frame, text="开始时间\n(mmddhhmm)", 
                 width=12,  # 更窄的标签宽度
                 font=self.ctrl_font).grid(row=0, column=0, sticky='w')
        ttk.Entry(time_frame, 
                 textvariable=self.start_time, 
                 font=self.ctrl_font).grid(row=0, column=2, sticky='ew', padx=5)

        # End time
        ttk.Label(time_frame, text="结束时间\n(mmddhhmm)", 
                 width=12,
                 font=self.ctrl_font).grid(row=1, column=0, sticky='w')
        ttk.Entry(time_frame, 
                 textvariable=self.end_time, 
                 font=self.ctrl_font).grid(row=1, column=2, sticky='ew', padx=5)

        # ---- 第三行：主参数选择 ----
        param_frame = ttk.Frame(content_frame)
        param_frame.grid(row=current_row, column=0, pady=2, sticky='ew')
        current_row +=1
    
        ttk.Label(param_frame, text="主参数", 
                 width=self.label_width, 
                 font=self.ctrl_font).pack(side=tk.LEFT)
        self.param_combobox = ttk.Combobox(
            param_frame, 
            textvariable=self.selected_param,
            font=self.ctrl_font,
            state="readonly"
        )
        
        self.param_combobox.pack(side=tk.LEFT, expand=1, fill=tk.X, padx=5)

        # ---- 第四行：添加次要参数按钮 ----
        self.secondary_btn = ttk.Button(
            content_frame, 
            text="+ 添加次要参数",
            command=self.add_secondary_param,
            style='TButton'
        )
        self.secondary_btn.grid(row=3, column=0, pady=(5,0), sticky='w')
        current_row +=1

        # ---- 第五行：操作按钮 ----
        btn_frame = ttk.Frame(content_frame)
        btn_frame.grid(row=4, column=0, pady=5, sticky='ew')
    
        ttk.Button(btn_frame, text="清空图像", 
                  command=lambda: self.clear_plots("24h")).pack(side=tk.LEFT, padx=2)
    
        ttk.Button(btn_frame, text="开始分析", 
                  command=self.analyze_data,
                  style='Accent.TButton').pack(side=tk.RIGHT, padx=2)
        
        # --- 新增滚动容器插入点 ---
        scroll_row = 5  # 确保在操作按钮之后的行
    
    
    
        # ==== 创建滚动容器为grid中的一行 ====
        self.scroll_container = ttk.Frame(content_frame)
        self.scroll_container.grid(row=scroll_row, column=0, sticky='nsew', pady=0)
        self.scroll_container.grid_remove()  # 初始隐藏
    
        # 配置行权重确保滚动区域扩展
        content_frame.rowconfigure(scroll_row, weight=1)
    
        # ==== 滚动区域初始化（同原redraw逻辑）====
        self.secondary_canvas = tk.Canvas(self.scroll_container, height=120)
        scrollbar = ttk.Scrollbar(self.scroll_container, orient="vertical", command=self.secondary_canvas.yview)
    
        canvas_frame = ttk.Frame(self.scroll_container)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
        self.secondary_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        self.scroll_frame = ttk.Frame(self.secondary_canvas)
        self.scroll_frame.bind("<Configure>", lambda e: self.secondary_canvas.configure(
            scrollregion=self.secondary_canvas.bbox("all"),
            height=min(120,e.height)
        ))
        self.secondary_canvas.create_window((0,0), window=self.scroll_frame, anchor="nw")
        self.secondary_canvas.configure(yscrollcommand=scrollbar.set)
    
        # ==== 修改后的redraw方法 ====
        def redraw_secondary_panel():
            self.scroll_container.grid()  # 显示滚动区域
        
            # 清空原有内容
            for widget in self.scroll_frame.winfo_children():
                widget.destroy()
        
            ttk.Label(self.scroll_frame, text="次要参数设置", 
                    font=('Microsoft YaHei', 16)).pack(anchor='w', pady=5)
        
            params = self.secondary_params if self.current_mode.get() == "24h" else self.secondary_params_lt
            for idx, var in enumerate(params):
                frame = ttk.Frame(self.scroll_frame)
                frame.pack(fill='x', pady=2)
            
                ttk.Label(frame, text=f"次参数{idx+1}:", 
                         font=self.ctrl_font).pack(side=tk.LEFT, padx=5)
            
                combo = ttk.Combobox(frame, textvariable=var,
                                    font=self.ctrl_font,
                                    values=self.param_combobox['values'],
                                    state="readonly")
                combo.pack(side=tk.LEFT, expand=True, fill='x')
    
        self.redraw_secondary_panel = redraw_secondary_panel



    def init_longterm_panel(self):
        """长期模式控制面板（全新代码）"""
    
        # ================== 步骤一：创建容器 ==================
        # 主内容容器（新增，解决布局拉伸问题） ▼▼▼
        content_frame = ttk.Frame(self.control_panel_longterm)
        content_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # ================== 步骤二：文件夹选择 ==================
        # 保留原有文件夹选择逻辑 ▼▼▼
        folder_frame = ttk.Frame(content_frame)
        folder_frame.pack(fill=tk.X, pady=5, anchor=tk.N)

        # 标签
        ttk.Label(
            folder_frame, 
            text="日志文件夹", 
            width=self.label_width,      # 保留原有的标签宽度配置
            font=self.ctrl_font          # 保留原字体设置
        ).pack(side=tk.LEFT)

        # 路径输入框
        ttk.Entry(
            folder_frame, 
            textvariable=self.selected_folder,  # 这里使用类中定义的StringVar变量
            font=self.ctrl_font
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # 浏览按钮
        ttk.Button(
            folder_frame, 
            text="浏览", 
            command=self.select_folder          # 保持原有选择文件夹的方法
        ).pack(side=tk.LEFT)

        # ================== 步骤三：参数选择 ==================
        param_frame = ttk.Frame(content_frame)
        param_frame.pack(fill=tk.X, pady=5)

        # 参数标签
        ttk.Label(
            param_frame, 
            text="分析参数",
            width=self.label_width,
            font=self.ctrl_font
        ).pack(side=tk.LEFT)

        # 参数下拉框（需新建独立实例） ▼▼▼
        self.param_combobox_lt = ttk.Combobox(  # 注意变量名带有_lt后缀区别于24h模式
            param_frame, 
            textvariable=self.selected_param_lt,   
            font=self.ctrl_font,
            state="readonly"
        )
        self.param_combobox_lt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.param_combobox_lt.bind("<<ComboboxSelected>>", lambda e: self.selected_param_lt.set(self.param_combobox_lt.get()))


        
        # ================== 步骤四：操作按钮 ==================
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(pady=10, fill=tk.X)

        self.secondary_btn_lt = ttk.Button(btn_frame, text="+ 添加次要参数", command=self.add_secondary_param)
        self.secondary_btn_lt.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="清空图像", command=self.clear_plots).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="开始分析", command=self.analyze_longterm, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

        # ================== 新增滚动容器区域 ==================
        
        self.scroll_container_lt = ttk.Frame(content_frame)
        self.scroll_container_lt.pack(fill=tk.BOTH, expand=True,anchor="w")  
        self.scroll_container_lt.pack_forget()                    

        # ▼▼▼ 按顺序初始化滚动区域组件 ▼▼▼
        self.secondary_canvas_lt = tk.Canvas(
            self.scroll_container_lt, 
            height=120, 
            width=500
            )
        
        scrollbar_lt = ttk.Scrollbar(self.scroll_container_lt, orient="vertical", command=self.secondary_canvas_lt.yview)

        self.scroll_frame_lt = ttk.Frame(self.secondary_canvas_lt)
        self.scroll_frame_lt.bind("<Configure>", 
            lambda e: self.secondary_canvas_lt.configure(
                scrollregion=self.secondary_canvas_lt.bbox("all"),
                height=min(120, e.height)
            )
        )

        self.secondary_canvas_lt.create_window((0,0), window=self.scroll_frame_lt, anchor="nw")
        self.secondary_canvas_lt.configure(yscrollcommand=scrollbar_lt.set)

        self.secondary_canvas_lt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_lt.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ==== 长期模式的独立重绘方法 ====
        def redraw_secondary_lt():
            self.scroll_container_lt.pack(anchor="w")  
        
            # 清空原有内容（仅影响长期区域）
            for widget in self.scroll_frame_lt.winfo_children():
                widget.destroy()
        
            # 长期专用标题
            ttk.Label(self.scroll_frame_lt, text="长期次要参数", 
                     font=('Microsoft YaHei', 16)).pack(anchor='w', pady=5, padx=5)
        
            # 仅处理长期参数
            for idx, var in enumerate(self.secondary_params_lt):
                frame = ttk.Frame(self.scroll_frame_lt)
                frame.pack(fill='x', pady=2, padx=5, anchor='w')
        
                ttk.Label(frame, text=f"次参{idx+1}:", 
                         font=self.ctrl_font).pack(side=tk.LEFT, padx=5)
        
                combo = ttk.Combobox(frame, textvariable=var,
                                    font=self.ctrl_font,
                                    values=self.param_combobox_lt['values'],
                                    state="readonly")
                combo.pack(side=tk.LEFT, expand=True, fill='x')
            
                
    
        # 存储独立方法
        self.redraw_secondary_lt = redraw_secondary_lt
    



    def create_common_widgets(self):
        """创建全局公共组件"""
        # 菜单栏
        menubar = tk.Menu(self.root, font=self.ctrl_font)
        mode_menu = tk.Menu(menubar, tearoff=0, font=self.ctrl_font)
        mode_menu.add_command(label="24小时模式", command=lambda: self.switch_control_panel("24h"))
        mode_menu.add_command(label="长期模式", command=lambda: self.switch_control_panel("longterm"))
        menubar.add_cascade(label="模式切换", menu=mode_menu)
        self.root.config(menu=menubar)

    
    def switch_control_panel(self, mode):
        """切换控制面板"""
        self.current_mode.set(mode)
        self.show_container(mode)  # 调用容器切换方法

        # 切换时强制清空画布
        self.clear_plots(mode)  # 需要改造clear_plots方法支持参数

    
    def on_param_selected(self, event):
        """当参数选择变更时的回调"""
        current_mode = self.current_mode.get()
        
        # 确保仅在参数有效时操作
        if current_mode == "24h":
            if not self.selected_param.get():
                return
            # 原24h模式的处理逻辑（如果有）
            pass  
        elif current_mode == "longterm":
            if not self.param_combobox_lt.get():
                return
            # 新增长期模式的处理逻辑 ▼▼▼
            try:
                selected = self.param_combobox_lt.get()
                self.analyze_longterm()  # 或其他需要触发的操作
            except Exception as e:
                messagebox.showerror("参数错误", f"参数解析失败: {str(e)}")


    def prepare_longterm_data(self):
        """长期模式的预处理方法"""
        folder = self.selected_folder.get()
        if not folder: 
             raise ValueError("未选择文件夹")
        # 触发文件扫描并保存结果
        self.date_files = self.scan_files(folder)  # 这个调用必须存在
        print(f"[DEBUG] 扫描到长期文件结构：{len(self.date_files)}个日期")



    def analyze_longterm(self):
        try:
            if not self.selected_param_lt.get():
                raise ValueError("请先选择分析参数")
            
            current_secondary = [var.get() for var in self.secondary_params_lt if var.get()]
            self.prepare_longterm_data()
            main_param = self.selected_param_lt.get()
            # 获取所有可用日期数据（无时间限制）
            dfs = self.load_all_data(main_param)
           # self.plot_longterm_data(dfs, main_param)
            self.plot_longterm_data(dfs, main_param, current_secondary)  # 传递实际参数
        except Exception as e:
            messagebox.showerror("分析错误", str(e))

    def parse_timestamp(self, base_date, time_str):
        """将日期对象和时间字符串合并为完整时间戳"""
        try:
            # 处理多冒号分隔的格式 hh:mm:ss:fff
            if time_str.count(":") == 3:
                h, m, s, f = time_str.split(":")
                return datetime(
                    base_date.year, base_date.month, base_date.day,
                    int(h), int(m), int(s), int(f.ljust(3, '0')[:3])  # 补齐3位毫秒
                )
            # 处理常规格式 hh:mm:ss
            else:
                return datetime.combine(
                    base_date,
                    datetime.strptime(time_str, "%H:%M:%S").time()
                )
        except ValueError:
            raise ValueError(f"无法解析时间格式: {time_str}")

    def load_all_data(self, param):
        """重构后的长期数据加载方法"""
        print(f"[DEBUG] 正在处理：{len(self.date_files)}个日期的数据")
        all_data = []

        # ▼▼▼ 确保 date_files 已存在 ▼▼▼
        if not hasattr(self, 'date_files'):
            raise RuntimeError("文件列表未初始化，请先选择文件夹")
    
        # Step 1: 遍历所有日期文件夹
        for date_str, hours in self.date_files.items():
            # 解析基准日期（例如'20240101' -> 2024/1/1）
            base_date = datetime.strptime(date_str, "%Y%m%d")
        
            # Step 2: 遍历每小时的CSV文件
            for hour_info in hours:
                file_path = hour_info["full_path"]
            
                with open(file_path, 'r', encoding='utf-8') as f:
                    headers = f.readline().strip().split(',')
                    units = f.readline()  # 单元行可能不需要
                
                   
                    try:
                        #time_col_index = headers.index("Timestamp")
                        time_col_index = 0
                    except ValueError:
                        raise Exception(f"文件 {file_path} 缺少Timestamp列")
                
               
                    try:
                        param_col_index = headers.index(param)
                    except ValueError:
                        continue  # 跳过不包含该参数的文件
                
                    # Step 3: 逐行读取数据
                    for line in f:
                        values = line.strip().split(',')
                        if len(values) < max(time_col_index, param_col_index)+1:
                            continue  # 数据行不完整时跳过
                    
                        try:
                            time_str = values[time_col_index].strip()
                            full_time = self.parse_timestamp(base_date, time_str)
                            value = float(values[param_col_index])
                        except (ValueError, IndexError) as e:
                            print(f"无效数据行: {line.strip()} | 错误: {str(e)}")
                            continue
    
                        all_data.append({
                                 'Timestamp': full_time,
                                 'Param': param,
                                 'Value': value
                         })
    
        return pd.DataFrame(all_data)

    
    def init_24h_viz(self):
        """24小时模式的绘图区域初始化"""
        self.figure_24h = plt.figure(figsize=(10,5))
        self.canvas_24h = FigureCanvasTkAgg(self.figure_24h, master=self.viz_frame_24h)
        self.canvas_24h.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def init_longterm_viz(self):
        """长期模式的绘图区域初始化"""
        self.figure_lt = plt.figure(figsize=(10,5))
        self.canvas_lt = FigureCanvasTkAgg(self.figure_lt, master=self.viz_frame_longterm)
        self.canvas_lt.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    
    def plot_longterm_data(self, df, main_param, secondary_params=None):
        self.figure_lt.clf()
        ax_main = self.figure_lt.add_subplot(111)  # 主坐标系对象换用更清晰的变量名
        secondary_axes = []  # 用来存储所有次坐标系
        self.active_axes = [ax_main]

        secondary_params = secondary_params or []

        # ====== 数据有效性验证 (保持原有) ======
        if df.empty:
            ax_main.text(0.5, 0.5, '没有找到有效数据', 
                        ha='center', va='center', 
                        fontsize=14, color='gray')
            self.canvas_lt.draw()
            return

        # ====== 数据预处理 (保持原有) ======
        clean_df = df[['Timestamp', 'Value']].dropna().copy()
        clean_df = clean_df.sort_values('Timestamp')  
        dates = mpl.dates.date2num(clean_df['Timestamp'])  
        values = clean_df['Value'].values

        # ====== 获取次要参数数据 (保持原有) ======
        all_dfs = {main_param: df}
        for param in secondary_params:
            try:
                df_sec = self.load_all_data(param)
                all_dfs[param] = df_sec
            except Exception as e:
                print(f"加载次要参数{param}失败: {str(e)}")

        try:
            # 使用类中统一颜色循环
            color_cycle = self.color_cycle
            main_color = color_cycle[0]

            # ====== 主参数绘制 (保持原有样式但改用ax_main) ======
            ax_main.plot(dates, values, 
                        marker='',         
                        linestyle='-',     
                        linewidth=1.5, 
                        color=main_color,   
                        alpha=0.8,
                        label=main_param)  # 添加label用于图例
            ax_main.xaxis_date()  

            ax_main.param_name = main_param

        
            # ====== 坐标格式设置 (保持原有) ======
             
            date_format = mpl.dates.DateFormatter('%m-%d %H:%M')  # longterm专属格式
            
            ax_main.xaxis.set_major_formatter(date_format)
            plt.setp(ax_main.get_xticklabels(), 
                    rotation=45, 
                    ha='right', 
                    rotation_mode='anchor')
            ax_main.tick_params(axis='both', which='major', labelsize=12)  

            ax_main.set_title(f"{main_param} 长期趋势分析", fontsize=18, pad=20, fontweight='bold')
            ax_main.set_xlabel("日期", fontsize=14)
            ax_main.set_ylabel(main_param, fontsize=14)
            ax_main.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)

            # ========= 核心修改部分：次要参数处理 =========
            # 使用独立颜色循环（跳过主参数使用的第一个颜色）
            colors = iter(plt.cm.tab20.colors)
            next(colors)  # 跳过主参数颜色
        
            # 遍历每个次要参数创建坐标系
            for idx, param in enumerate(secondary_params):
                if param not in all_dfs or param == main_param:
                    continue
                
                df_sec = all_dfs[param]
                sec_dates = mpl.dates.date2num(df_sec['Timestamp'])
                values_sec = df_sec['Value'].values

                # 为使每条曲线颜色唯一，取下一个颜色
                color = color_cycle[(idx+1) % len(color_cycle)]  # 严格和24小时模式的逻辑一致
            
                # ==== 创建次坐标系 ====
                ax_sec = ax_main.twinx()  # 创建共享x轴的新坐标系
            
                # ==== 坐标系位置调整 ====
                # 设置右侧坐标轴偏移（首个轴与主轴右边界对齐，后续依次右移）
                offset = 40 * idx  # 每个轴右移60points（约对应matplotlib坐标空间的0.15单位）
                ax_sec.spines['right'].set_position(('outward', offset))
            
                # ==== 绘制数据并设置颜色 ====
                ax_sec.plot(sec_dates, values_sec, 
                           color=color,
                           alpha=0.7, 
                           linewidth=1.2,
                           label=param)
            
                # ==== 坐标轴染色 ====
                ax_sec.yaxis.label.set_color(color)
                ax_sec.tick_params(axis='y', colors=color)
                ax_sec.spines['right'].set_color(color)

                ax_sec.tick_params(axis='y', labelsize=12) 
            
                # 设置次轴标签位置（防止重叠）
                ax_sec.yaxis.set_label_coords(1.1 + idx*0.05, 0.5)  # 动态调整位置

                ax_sec.param_name = param 
            
                secondary_axes.append(ax_sec)
                self.active_axes = [ax_main] + secondary_axes

            # ====== 自适应布局调整 ======
            # 根据次轴数量调整主图右侧边距
            right_margin = 0.85 - 0.03 * len(secondary_axes)  # 每个次轴缩减3%空间
            self.figure_lt.subplots_adjust(right=right_margin)

            # ====== 统一图例系统 ======
            lines = [ax_main.get_lines()[0]] + [ax.get_lines()[0] for ax in secondary_axes]
            labels = [line.get_label() for line in lines]

            # 动态布局方式（同24h模式）
            num_secondary = len(secondary_params)
            if num_secondary > 3:  # 多列布局防止溢出
                legend = ax_main.legend(
                    lines, labels,
                    loc='upper left',
                    bbox_to_anchor=(0.02, 0.98),
                    frameon=False,
                    fontsize=12,
                    ncol=2  # 大于3个参数显示两列
                )
            else:  # 单列布局
                legend = ax_main.legend(
                    lines, labels,
                    loc='upper left',
                    bbox_to_anchor=(0.02, 0.98),
                    frameon=False,
                    fontsize=12
                    )
                # 调整右侧边距保证图例可见
            self.figure_lt.subplots_adjust(right=0.82)  # 固定右侧边距

            # ====== 最终布局调整 ======
            self.figure_lt.tight_layout()

        except Exception as e:
            ax_main.clear()
            ax_main.text(0.5, 0.5, f'绘图错误: {str(e)}', 
                        ha='center', va='center', 
                        color='red', fontsize=12)
            raise
    
        finally:
            self.canvas_lt.draw()
            self.canvas_lt.flush_events()
            self.bind_right_click()


    
    def plot_24h_data(self, main_df, main_param, secondary_dfs):
        """24小时模式完整绘图流程"""
        try:
            # === 画布初始化 ===
            self.figure.clf()
            self.ax_main = self.figure.add_subplot(111)
            self.active_axes = [self.ax_main]
        
            # === 主参数渲染 ===
            main_line, = self.ax_main.plot(
                main_df['Timestamp'], main_df['Value'],
                color=self.color_cycle[0],
                linewidth=2,
                alpha=0.9,
                zorder=10,
                label=main_param
            )
            self.ax_main.set_ylabel(main_param, 
                              color=self.color_cycle[0], 
                              fontsize=14,
                              rotation=0,
                              labelpad=15)
        
            # === 时间轴格式化 ===
            self.ax_main.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            self.ax_main.tick_params(axis='x', labelsize=12)
            self.ax_main.grid(True, linestyle=':', alpha=0.5)
        
            # === 生成次级坐标轴 ===
            secondary_axes = []
            for idx, (param_name, df) in enumerate(secondary_dfs.items()):
                # 生成定位正确的坐标轴
                ax_sec = self.create_secondary_axis(self.ax_main, idx)
                line = ax_sec.plot(df['Timestamp'], df['Value'],
                              color=self.color_cycle[idx+1], 
                              linewidth=1.5,
                              alpha=0.8,
                              label=param_name)
            
                # 标签垂直排列防止重叠
                ax_sec.set_ylabel(param_name,
                            rotation=270,
                            va='bottom',
                            labelpad=25,
                            fontsize=12)
                secondary_axes.append(ax_sec)
                self.active_axes.append(ax_sec)
        
            # === 布局优化 ===
            self.adjust_dynamic_layout(len(secondary_dfs))
        
            # === 智能图例管理 ===
            self.create_unified_legend([main_line] + [ax.get_lines()[0] for ax in secondary_axes], len(secondary_dfs))
        
            #self.canvas.draw()
            current_mode = self.current_mode.get()
            if current_mode == "24h":
               self.canvas_24h.draw()
            else:
               self.canvas_lt.draw()

        except Exception as e:
            messagebox.showerror("绘图错误", f"渲染失败: {str(e)}")

    def create_unified_legend(self, lines, sec_count):
        """生成自适应图例"""
        # 根据参数数量选择布局方式
        if sec_count > 3:
            # 多列布局防止溢出
            ncol = 2 if sec_count < 5 else 3
            self.figure.legend(
                handles=lines,
                loc='upper center',
                bbox_to_anchor=(0.5, 1.05),
                ncol=ncol,
                fontsize=11,
                framealpha=0.95
            )
        else:
            # 常规右上角布局
            self.figure.legend(
                handles=lines,
                loc='upper right',
                bbox_to_anchor=(0.98, 0.98),
                fontsize=12
            )



    
    def create_secondary_axis(self, parent_ax, axis_index):
        """动态生成等距偏移的次坐标轴"""
        # 关键参数配置
        BASE_OFFSET = 1.0      # 起始偏移量
        STEP = 0.15            # 每个轴的间距（根据测试调整）
        MAX_AXIS = 5           # 最多支持5个次轴
    
        # 防止溢出并计算比例偏移
        effective_index = min(axis_index, MAX_AXIS-1)
        offset = BASE_OFFSET + effective_index * STEP
    
        # 创建坐标轴对象
        new_ax = parent_ax.twinx()
        new_ax.spines['right'].set_position(('axes', offset))
    
        # 颜色动态分配策略
        color = self.color_cycle[(effective_index+1) % len(self.color_cycle)]
        new_ax.spines['right'].set_color(color)
        new_ax.yaxis.label.set_color(color)
        new_ax.tick_params(axis='y', colors=color, labelsize=12)
    
        # 优化标签位置防止溢出
        new_ax.yaxis.set_label_coords(offset + 0.05, 0.5)  # 动态调整标签坐标
    
        return new_ax


    def smart_axis_config(self, target_ax):
        """智能化坐标配置界面"""
        dialog = tk.Toplevel(self.root)
        dialog.title("坐标轴配置")
        dialog.geometry("380x300")  # 优化对话框尺寸
    
        # 数据驱动配置
        current_min, current_max = target_ax.get_ylim()
        data_range = current_max - current_min
    
        # 智能计算推荐步长
        suggested_steps = self.calculate_step_suggestions(data_range)
    
        # 界面控件
        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
    
        # 范围设置
        ttk.Label(main_frame, text="最小值:", font=('微软雅黑',12)).grid(row=0, column=0, sticky='w')
        self.entry_min = ttk.Entry(main_frame, width=10)
        self.entry_min.insert(0, f"{current_min:.2f}")
        self.entry_min.grid(row=0, column=1, padx=5)
    
        ttk.Label(main_frame, text="最大值:", font=('微软雅黑',12)).grid(row=1, column=0, sticky='w')
        self.entry_max = ttk.Entry(main_frame, width=10)
        self.entry_max.insert(0, f"{current_max:.2f}")
        self.entry_max.grid(row=1, column=1, padx=5)
    
        # 智能步长推荐
        step_btn_frame = ttk.Frame(main_frame)
        step_btn_frame.grid(row=2, columnspan=2, pady=5)
        for step in suggested_steps:
            btn = ttk.Button(step_btn_frame, text=f"{step:.2f}", 
                        command=lambda s=step: self.entry_step.insert(0, str(s)),
                        width=6)
            btn.pack(side=tk.LEFT, padx=2)
    
        ttk.Label(main_frame, text="刻度间隔:", font=('微软雅黑',12)).grid(row=3, column=0, sticky='w')
        self.entry_step = ttk.Entry(main_frame, width=10)
        self.entry_step.insert(0, f"{(current_max-current_min)/5:.2f}")
        self.entry_step.grid(row=3, column=1, padx=5)
    
        # 验证和应用逻辑
        def apply_changes():
            try:
                new_min = float(self.entry_min.get())
                new_max = float(self.entry_max.get())
                step = float(self.entry_step.get())
            
                if new_min >= new_max:
                    raise ValueError("最小不能大于等于最大值")
                if step <= 0:
                    raise ValueError("步长必须为正值")
                
                target_ax.set_ylim(new_min, new_max)
                target_ax.set_yticks(np.arange(new_min, new_max + step, step))
                
                #self.canvas.draw()
                current_mode = self.current_mode.get()
                if current_mode == "24h":
                    self.canvas_24h.draw()
                else:
                    self.canvas_lt.draw()

                dialog.destroy()
            except Exception as e:
                messagebox.showerror("输入错误", str(e))
    
        ttk.Button(main_frame, text="应用", command=apply_changes).grid(row=4, columnspan=2, pady=10)



    def clear_plots(self, mode="24h"):
        """安全清除图形并重置轴"""
        # === 根据模式绑定变量 ===
        if mode == "24h":
            fig = self.figure_24h
            canvas = self.canvas_24h
            self.secondary_params.clear() 
        else:
            fig = self.figure_lt
            canvas = self.canvas_lt
            self.secondary_params_lt.clear()

        # ↓↓↓ 此处开始使用已绑定的变量 ↓↓↓
        # 增加图形对象存在性检查
        if fig is None or canvas is None:
            print(f"[DEBUG] {mode}模式的图形尚未初始化") 
            return  # 终止清除操作避免崩溃

        try:
            # === 清理残留的轴 ===
            fig.clf()  # 清除整个图形
        
            # === 重置所有轴上界变量 ===
            self.ax_main = None
            self.ax_secondary = None  # 次要坐标轴重置为None

            # === 重建基础轴 ===
            if mode == "24h":
                self.ax_main = fig.add_subplot(111)
                self.ax_secondary = None  # 初始时不显示次要轴
                self.ax_main.grid(True)
                self.ax_main.set_xlabel('时间轴', fontsize=14)
                self.ax_main.set_ylabel('主参数值', fontsize=14)
                self.ax_main.set_title("数据可视化图表", fontsize=16, pad=20)
                self.ax_main.text(0.5, 0.5, '点击「开始分析」显示数据',
                              ha='center', va='center',
                              fontsize=16, alpha=0.5)
            else:
                self.ax_lt = fig.add_subplot(111)
                self.ax_lt.grid(True)
                self.ax_lt.set_xlabel('日期', fontsize=14)
                self.ax_lt.set_ylabel('参数值', fontsize=14)
                self.ax_lt.set_title("长期趋势分析", fontsize=16, pad=20)
                self.ax_lt.text(0.5, 0.5, '点击「开始分析」显示数据',
                                ha='center', va='center',
                                fontsize=16, alpha=0.5)
                
            if mode == '24h':
                if self._event_cids['24h']:
                   self.canvas_24h.mpl_disconnect(self._event_cids['24h'])
                   self._event_cids['24h'] = None
            else:
                if self._event_cids['longterm']:
                   self.canvas_lt.mpl_disconnect(self._event_cids['longterm'])
                   self._event_cids['longterm'] = None

            # === 强制刷新画布 ===
            canvas.draw_idle()
            canvas.draw()

        except Exception as e:
         messagebox.showerror("清空失败", f"重置图形失败: {str(e)}")

    
    def add_secondary_param(self):
        """添加次要参数下拉框"""
        current_mode = self.current_mode.get()

        if current_mode == "24h":
            target = self.secondary_params
            # 24小时模式调用原有方法
            if len(target) >= 5:
                messagebox.showinfo("提示", "最多添加5个参数")
                return
            target.append(tk.StringVar())
            self.redraw_secondary_panel()  # 调用原始24h方法
        else:
            target = self.secondary_params_lt
            # 长期模式使用新方法
            if len(target) >= 5:
                messagebox.showinfo("提示", "最多添加5个参数")
                return
            target.append(tk.StringVar())
            self.redraw_secondary_lt()  # 调用长期专用方法

       



    
    def select_folder(self):
        mode = self.current_mode.get()
        folder = filedialog.askdirectory()
    
        if not folder:
            return
    
        if mode == "longterm":
            # 验证是否包含日期格式的子文件夹
            date_folders = [d for d in os.listdir(folder) 
                          if self.is_valid_date_folder(d) 
                          and os.path.isdir(os.path.join(folder, d))]
            if not date_folders:
                messagebox.showerror("错误", "该目录下未找到符合yyyy_mm_dd格式的日期文件夹")
                return
    
        self.selected_folder.set(folder)
        self.load_parameters()


    def load_parameters(self):
        """获取第一个有效文件的参数列表（支持长短期模式）"""
        folder = self.selected_folder.get()
        if not folder:
            return

        try:
            file_path = None  # 最终用于读取的文件路径

            # ======== 新增部分开始 ========
            if self.current_mode.get() == "longterm":
                # 长期模式：需要搜索日期子文件夹
                for date_folder in os.listdir(folder):
                    # 步骤1：验证是否符合日期格式
                    if not self.is_valid_date_folder(date_folder):  # 使用之前添加的验证方法
                        continue
                
                    # 步骤2：构建完整子路径
                    scan_data_path = os.path.join(
                        folder,
                        date_folder,
                        "Log",
                        "SamplingLog",
                        "ScanData"
                    )
                
                    # 步骤3：检查路径是否存在
                    if not os.path.exists(scan_data_path):
                        continue  # 跳过缺失路径的日期
                
                    # 步骤4：在该目录下寻找第一个有效文件
                    for filename in os.listdir(scan_data_path):
                        if self.file_pattern.match(filename):
                            file_path = os.path.join(scan_data_path, filename)
                            break  # 找到第一个文件后终止循环
                
                    if file_path:  # 如果找到文件则停止搜索
                        break
        
            else:
            # ======== 原有的24小时模式代码开始 ======== 
            
                for filename in os.listdir(folder):
                    if self.file_pattern.match(filename):
                        file_path = os.path.join(folder, filename)
                        break  
        

            # 检查是否找到有效文件
            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError("未找到符合格式的数据文件")

            # 从文件读取headers（这段保留原有逻辑）
            with open(file_path, 'r', encoding='utf-8') as f:
                headers = f.readline().strip().split(',')

            if headers:
                target_combobox = (
                    self.param_combobox_lt 
                    if self.current_mode.get() == "longterm" 
                    else self.param_combobox
                )
                target_variable = (
                    self.selected_param_lt 
                    if self.current_mode.get() == "longterm" 
                    else self.selected_param
                )
            
                # 更新下拉框选项
                target_combobox['values'] = headers
            
                # 设置默认参数（如果没有选中的时候）
                if not target_variable.get():
                    target_variable.set(headers[0])
                
        except Exception as e:
            messagebox.showerror("文件错误", f"读取参数失败：{str(e)}")


    def analyze_data(self):
        if not self.validate_inputs():
            return

        try:
            start_dt, end_dt = self.parse_time_range()
            main_param = self.selected_param.get()
            second_params = [var.get() for var in self.secondary_params if var.get()]  # 修正的获取方式

            if main_param in second_params:
                raise ValueError("主参数不能与次参数重复")

            # 加载主参数数据
            main_df = self.load_time_range_data(start_dt, end_dt)  # 使用正确的方法

            # 加载次参数数据
            second_dfs = {}
            for param in second_params:
                try:
                    temp_param = self.selected_param.get()
                    self.selected_param.set(param)  # 临时切换选中参数
                    second_dfs[param] = self.load_time_range_data(start_dt, end_dt)
                except KeyError as e:
                    raise ValueError(f"参数'{param}'不存在于文件中")
                finally:
                    self.selected_param.set(temp_param)  # 恢复主参数

            self.plot_data(main_df, main_param, second_dfs)

        except Exception as e:
            messagebox.showerror("分析错误", str(e))



    def validate_inputs(self):
        errors = []
        if not self.selected_folder.get():
            errors.append("请选择日志目录")
        if not self.start_time.get():
            errors.append("请输入起始时间")
        if not self.end_time.get():
            errors.append("请输入结束时间")
        if not self.selected_param.get():
            errors.append("请选择分析参数")
        
        if errors:
            messagebox.showwarning("输入不完整", "\n".join(errors))

        if len(self.secondary_params) > 5:
            errors.append("最多允许添加5个次要参数")
        
        # 修正返回逻辑
        if errors:
            messagebox.showwarning("输入不完整", "\n".join(errors))
            return False
        return True  # 只有全部验证通过才返回True

    def parse_time_range(self):
        """解析新时间格式mmddhhmm"""
        def parse_time(s):
            try:
                # 验证输入格式
                if len(s) != 8 or not s.isdigit():
                    raise ValueError("必须为8位数字（如02251430）")
                
                mm = int(s[0:2])
                dd = int(s[2:4])
                hh = int(s[4:6])
                mi = int(s[6:8])

                current_year = datetime.now().year
                dt = datetime(current_year, mm, dd, hh, mi)
                
                # 检查datetime是否维持原始输入值
                if (dt.month, dt.day, dt.hour, dt.minute) != (mm, dd, hh, mi):
                    raise ValueError("日期时间值不合法")
                return dt
            except ValueError as e:
                raise ValueError(f"无效时间格式: {s} | {str(e)}")

        start_dt = parse_time(self.start_time.get())
        end_dt = parse_time(self.end_time.get())
        
        if start_dt >= end_dt:
            raise ValueError("结束时间必须晚于起始时间")
            
        return start_dt, end_dt

    def load_time_range_data(self, start_dt, end_dt):
        """加载时间范围数据（优化缓存）"""
        if self.selected_folder.get() == self.last_scan_folder:
            date_files = self.file_cache.get(self.selected_folder.get(), {})
        else:
            date_files = self.scan_files(self.selected_folder.get())
    
        all_data = []
        param_index = None
        current_year = datetime.now().year
    
        start_ymd = start_dt.strftime("%Y%m%d")
        end_ymd = end_dt.strftime("%Y%m%d")

        for date_str, hours in date_files.items():
            # +++ 新增判断：24小时模式时才执行日期范围过滤 +++
            if self.current_mode.get() == "24h":
                if date_str < start_ymd or date_str > end_ymd:
                    continue

            for hour_info in hours:  # 变量名从hour改为hour_info更清晰
                # +++ 根据模式选择文件路径构建方式 +++
                if self.current_mode.get() == "longterm":
                    # 长期模式：从字典获取路径
                    file_path = hour_info["full_path"]
                    hour = hour_info["hour"]
                else:
                    # 24小时模式：保持原路径拼接方式
                    hour = hour_info  # 原来就是字符串格式
                    filename = f"{date_str}{hour}.csv"
                    file_path = os.path.join(self.selected_folder.get(), filename)
            
                try:
                     with open(file_path, 'r', encoding='utf-8') as f:
                          headers = f.readline().strip().split(',')
                          f.readline()  # 跳过单位行

                          # 获取参数索引
                          selected_param = self.selected_param.get()
                          if param_index is None:
                             param_index = headers.index(selected_param)
            
                          # 不同模式的日期处理方式保持一致
                          file_date_str = date_str  # 改用扫描时获得的date_str
                          base_date = datetime.strptime(file_date_str, "%Y%m%d")
        
                          for line in f:
                              values = line.strip().split(',')
                              # 合并文件名中的日期和时间列的时间部分
                              raw_time = values[0]
            
                              # 时间格式转换逻辑
                              if raw_time.count(":") == 3:
                                 time_parts = raw_time.split(":")
                              # 转换格式：hh:mm:ss.fff
                                 formatted_time = f"{time_parts[0]}:{time_parts[1]}:{time_parts[2]}.{time_parts[3]}"
                              else:
                                  formatted_time = raw_time  # 兼容非毫秒格式
            
                              # 组合完整时间
                              try:
                                  time_with_date = datetime.combine(
                                     base_date,
                                     datetime.strptime(formatted_time, "%H:%M:%S.%f").time()
                                  )
                              except ValueError:
                                   time_with_date = datetime.combine(
                                      base_date,
                                      datetime.strptime(formatted_time, "%H:%M:%S").time()
                                   )
            
                              # 验证并存储数据
                              if start_dt <= time_with_date <= end_dt:
                                 all_data.append({
                                    'Timestamp': time_with_date,
                                    'Value': float(values[param_index])
                                  })
                except FileNotFoundError:
                    continue
                except Exception as e:
                    raise RuntimeError(f"文件{filename}读取错误: {str(e)}")

        return pd.DataFrame({
           'Timestamp': [d['Timestamp'] for d in all_data],
           'Value': [d['Value'] for d in all_data]
        })


    def scan_files(self, folder):
        """根据模式扫描文件"""
        if self.current_mode.get() == "longterm":
            return self.scan_longterm_files(folder)
        else:
            return self.scan_24h_files(folder)

    def scan_24h_files(self, folder):
        """24小时模式文件扫描"""
        date_files = {}
        for filename in os.listdir(folder):
            if self.file_pattern.match(filename):
                date_str = filename[:8]
                hour_str = filename[8:10]
                date_files.setdefault(date_str, []).append(hour_str)
        return date_files

    def scan_longterm_files(self, parent_folder):
        """长期模式文件扫描"""
        date_files = {}
    
        # 遍历所有日期格式的子文件夹
        for date_folder in os.listdir(parent_folder):
            if not self.is_valid_date_folder(date_folder):
                continue
            
            scan_data_path = os.path.join(
                parent_folder,
                date_folder,
                "Log",
                "SamplingLog",
                "ScanData"
            )
        
            # 检测路径是否存在
            if not os.path.exists(scan_data_path):
                continue
            
            # 扫描该日期下的数据文件
            date_str = date_folder.replace("_", "")
            for filename in os.listdir(scan_data_path):
                if self.file_pattern.match(filename):
                    hour_str = filename[8:10]
                    full_path = os.path.join(scan_data_path, filename)
                    date_files.setdefault(date_str, []).append({
                        "hour": hour_str,
                        "full_path": full_path
                    })
    
        return date_files


    def plot_data(self, main_df, main_param, second_dfs):
        """全参数自适应布局绘图方法"""
        
        # 根据当前模式重置轴列表
        current_mode = self.current_mode.get()
        self.active_axes = [self.ax_main] if current_mode == "24h" else [self.ax_lt]

        try:
            current_mode = self.current_mode.get()
            if current_mode == "24h":
                fig = self.figure_24h
                canvas = self.canvas_24h
                fig.set_size_inches(12, 6)
            else:
                fig = self.figure_lt
                canvas = self.canvas_lt

            # 初始化画布
            fig.clf()
            self.ax_main = fig.add_subplot(111)
            self.active_axes = [self.ax_main]

            # === 主参数绘图 ===
            main_line, = self.ax_main.plot(
                main_df['Timestamp'], main_df['Value'],
                color='tab:blue',
                linewidth=2.5,
                label=main_param,
                zorder=100
            )

            # === 智能次坐标轴管理 ===
            secondary_axes = []
            RIGHT_EDGE_BASE = 0.95  # 基础右侧边距
            AXIS_STEP = 0.030       # 次轴间距系数
            MAX_SECONDARY = 5       # 最大支持次轴数

            for idx, (param_name, df) in enumerate(second_dfs.items()):
                if idx >= MAX_SECONDARY:
                    break

                # 动态偏移算法：仅在有多个次轴时启用偏移
                offset = 1.0 + idx*AXIS_STEP if len(second_dfs) > 1 else 1.0

                ax = self.ax_main.twinx()
                ax.spines['right'].set_position(('axes', offset))

                # 颜色分配策略（保障与主色对比）
                color = self.color_cycle[(idx+1) % len(self.color_cycle)]

                ax.plot(df['Timestamp'], df['Value'],
                        color=color,
                        linewidth=1.8,
                        alpha=0.9,
                        label=param_name)
            
                # 紧凑标签配置
                #ax.set_ylabel(param_name,
                #             color=color,
                #             rotation=0,
                #             va='center',
                #             ha='left',
                #             labelpad=10 + idx*5,
                #             fontsize=10)

                ax.yaxis.set_label_coords(1.02 + idx*0.02, 0.5)  # 标签位置动态调整
                ax.tick_params(axis='y', labelsize=14, labelcolor=color)

                secondary_axes.append(ax)
                self.active_axes.append(ax)

            # === 主坐标设置 ===
            self.ax_main.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            self.ax_main.tick_params(axis='x', labelsize=10, rotation=30)

            self.active_axes = [self.ax_main] + secondary_axes  # 维护当前激活坐标系

            self.ax_main.set_xlabel("时间 (HH:MM)", fontsize=12)
            self.ax_main.set_ylabel(main_param, color='tab:blue', fontsize=12)
            self.ax_main.grid(True, alpha=0.3)

            # === 动态布局计算 ===
            num_secondary = min(len(second_dfs), MAX_SECONDARY)
        
            # 非线性右侧边距调整公式：
            right_adjust = num_secondary ** 0.7 * 0.03
            right_margin = RIGHT_EDGE_BASE - right_adjust

            # 主布局参数
            fig.subplots_adjust(
                left=0.08,       # 固定左侧边距
                right=right_margin,
                top=0.88,        # 顶部预留图例空间
                bottom=0.12
            )

            # === 图例系统智能布局 ===
            handles, labels = [], []
            for ax in self.active_axes:
                h, l = ax.get_legend_handles_labels()
                handles.extend(h)
                labels.extend(l)

            # 根据元素数量自动布局
            if len(handles) <= 5:  # 紧凑布局
                legend = self.ax_main.legend(
                    handles, labels,
                    loc='upper left',
                    bbox_to_anchor=(0.02, 0.98),
                    frameon=False,
                    fontsize=11,
                    handlelength=1.2,
                    borderaxespad=0.5
                )
            else:  # 多列布局
                legend = fig.legend(
                    handles, labels,
                    loc='upper center',
                    bbox_to_anchor=(0.5, 1.05),
                    ncol=2,
                    fontsize=10,
                    columnspacing=1,
                    framealpha=0.9
                )

            # 检查图例是否超出画布
            canvas.draw()
            
            self.bind_right_click()

            renderer = canvas.get_renderer()
            legend_bbox = legend.get_window_extent(renderer)
            fig_bbox = fig.get_window_extent(renderer)

            # 动态调整主图位置
            if legend_bbox.y1 > fig_bbox.y1:
                fig.subplots_adjust(top=0.88 - (legend_bbox.height/fig_bbox.height))
                canvas.draw()

            canvas.draw_idle()

        except Exception as e:
            error_msg = f"绘图失败：{str(e)}\n跟踪信息："
            error_msg += f"\n- 主参数数据量：{len(main_df)}条"
            error_msg += f"\n- 次参数数量：{len(second_dfs)}个"
            messagebox.showerror("绘图错误", error_msg)

        

    

    
    def adjust_dynamic_layout(self, total_secondary):
        """智能分配绘图区域空间"""
        LEFT_MARGIN = 0.08         # 固定左侧留白
        BASE_RIGHT = 0.92          # 基础右侧边界
        MARGIN_PER_AXIS = 0.08     # 每个次轴需要的额外空间
    
        if total_secondary == 0:
            right_pos = BASE_RIGHT
        else:
            required = MARGIN_PER_AXIS * total_secondary
            max_allow = 0.4        # 最多允许占用40%的右侧空间
            right_pos = BASE_RIGHT - min(required, max_allow)
    
        # 应用布局参数（同时设置其他边距）
        self.figure.subplots_adjust(
            left=LEFT_MARGIN,
            right=right_pos,
            top=0.92,
            bottom=0.12,
            hspace=0  # 横向间距清零
        )

    def bind_right_click(self):
        """按当前模式重新绑定右键事件"""
        current_mode = self.current_mode.get()
        target_canvas = self.canvas_24h if current_mode == "24h" else self.canvas_lt

        # ▼ 移除旧绑定 ▼
        if self._event_cids[current_mode] is not None:
            target_canvas.mpl_disconnect(
                self._event_cids[current_mode]
            )
       
        
        # ▼ 绑定新事件 ▼
        new_cid = target_canvas.mpl_connect("button_press_event", self.on_right_click)
        self._event_cids[current_mode] = new_cid


    
    def on_right_click(self, event):
        """右键点击事件处理"""
        if event.button != 3 or event.inaxes is None:  # 新增inaxes检查  # 仅响应鼠标右键
            return
        
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()

        # 创建右键菜单
        menu = tk.Menu(self.root, tearoff=0, font=self.ctrl_font)
    
        # 总是显示X轴选项
        menu.add_command(
            label="修改x轴坐标范围/间距",
            command=lambda: self.show_xaxis_config(self.active_axes[0])
        )
    
        # 主要参数Y轴
        menu.add_command(
            label="修改主要参数坐标范围/间距",
            command=lambda: self.show_axis_config(self.active_axes[0])
        )
    
        # 动态添加次要参数（从第二个轴开始）
        for idx, ax in enumerate(self.active_axes[1:]):
            menu.add_command(
                label=f"修改第{idx+1}个次要参数坐标范围/间距",
                command=lambda ax=ax: self.show_axis_config(ax)
            )
    
        # 显示菜单
        try:
            menu.tk_popup(x,y)
        finally:
            menu.grab_release()


    
    def show_axis_config(self, ax):
         dialog = tk.Toplevel(self.root)
         dialog.title("坐标轴设置")
    
         # 统一使用大号字体 ▼▼▼
         entry_font = ('Microsoft YaHei', 16)
         label_font = ('Microsoft YaHei', 16, 'bold')
    
         # ▼ 主框架设置 ▼
         main_frame = ttk.Frame(dialog, padding=(15, 15))
         main_frame.pack()
    
         # 当前范围值默认显示
         ymin, ymax = ax.get_ylim()
         current_step = ax.yaxis.get_ticklocs()[1] - ax.yaxis.get_ticklocs()[0] if len(ax.yaxis.get_ticklocs()) > 1 else (ymax - ymin)/5
    
         #  ▼▼▼ 使用统一的字体设置 ▼▼▼
         ttk.Label(main_frame, text="最小值:", font=label_font).grid(row=0, column=0, sticky="w", pady=5)
         min_entry = ttk.Entry(main_frame, font=entry_font)
         min_entry.insert(0, f"{ymin:.2f}")
         min_entry.grid(row=0, column=1, padx=10, pady=5)

         ttk.Label(main_frame, text="最大值:", font=label_font).grid(row=1, column=0, sticky="w", pady=5)
         max_entry = ttk.Entry(main_frame, font=entry_font)
         max_entry.insert(0, f"{ymax:.2f}")
         max_entry.grid(row=1, column=1, padx=10, pady=5)

         ttk.Label(main_frame, text="刻度间隔:", font=label_font).grid(row=2, column=0, sticky="w", pady=5)
         step_entry = ttk.Entry(main_frame, font=entry_font)
         step_entry.insert(0, f"{current_step:.2f}")
         step_entry.grid(row=2, column=1, padx=10, pady=5)


         log_frame = ttk.Frame(main_frame)
         log_frame.grid(row=3, columnspan=2, pady=5, sticky='w')
         is_log_var = tk.BooleanVar(value=(ax.get_yscale() == 'log'))
         ttk.Checkbutton(log_frame, text="对数坐标轴", 
                        variable=is_log_var).pack(side=tk.LEFT) 
        


         def apply_changes():
            try:
                new_min = float(min_entry.get())
                new_max = float(max_entry.get())
                step = float(step_entry.get())

                if new_min >= new_max:
                    raise ValueError("最小值不能大于等于最大值")

                ax.set_ylim(new_min, new_max)
                ax.set_yticks(np.arange(new_min, new_max + step, step))
                
                #self.canvas.draw()
                current_mode = self.current_mode.get()
                if current_mode == "24h":
                   self.canvas_24h.draw()
                else:
                   self.canvas_lt.draw()
                
                dialog.destroy()
                
                # ▲▲▲新添加验证和设置▲▲▲
                is_log = is_log_var.get()
                if is_log and (new_min <=0 or new_max <=0):
                    raise ValueError("对数坐标需要所有值大于零")

                # 关联参数名称（需参数名与坐标轴绑定）
                param_name = getattr(ax, 'param_name', None)
                if param_name:
                    self.log_scale_settings[param_name] = is_log

                ax.set_yscale('log' if is_log else 'linear')

            except Exception as e:
                messagebox.showerror("输入错误", str(e))

        # ▼▼▼ 应用按钮调整 ▼▼▼
         btn_frame = ttk.Frame(main_frame)
         btn_frame.grid(row=3, columnspan=2, pady=15)
         
         
         btn = ttk.Button(btn_frame, text="应用", command=apply_changes,  # 现在函数已定义
                    style='Accent.TButton', width=10)
         btn.pack(padx=5, ipadx=10, ipady=5)

         

    
    def show_xaxis_config(self, ax):
        dialog = tk.Toplevel(self.root)
        dialog.title("X轴设置")
        current_mode = self.current_mode.get()  # 获取当前模式
    
        # 根据模式设置不同窗口尺寸
        dialog.geometry("500x400" if current_mode == "longterm" else "450x350")
    
        # 统一字体设置
        label_font = ('Microsoft YaHei', 16, 'bold')
        entry_font = ('Microsoft YaHei', 16)
    
        main_frame = ttk.Frame(dialog, padding=(15, 15))
        main_frame.pack(fill=tk.BOTH, expand=True)

        xmin_num, xmax_num = ax.get_xlim()
        xmin = mpl.dates.num2date(xmin_num)
        xmax = mpl.dates.num2date(xmax_num)

        # ====== 长期模式专属设置 ======
        if current_mode == "longterm":
            # ▼▼▼ 长期模式显示格式 ▼▼▼
            def format_mmddhhmm(dt):
                return dt.strftime("%m-%d %H:%M")

            # 输入标签设置
            ttk.Label(main_frame, text="开始时间\n(mm-dd hh:mm)", 
                     font=label_font).grid(row=0, column=0, sticky="w", pady=5, padx=5)
            ttk.Label(main_frame, text="结束时间\n(mm-dd hh:mm)", 
                     font=label_font).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        
            # 输入框时间格式（包含月份和日期）
            start_entry = ttk.Entry(main_frame, font=entry_font)
            start_entry.insert(0, format_mmddhhmm(xmin))
            start_entry.grid(row=0, column=1, padx=5, pady=5)

            end_entry = ttk.Entry(main_frame, font=entry_font)
            end_entry.insert(0, format_mmddhhmm(xmax))
            end_entry.grid(row=1, column=1, padx=5, pady=5)

            # 刻度间隔（小时）
            tick_locs = ax.xaxis.get_ticklocs()
            current_interval = int((tick_locs[1]-tick_locs[0])*24) if len(tick_locs) >1 else 24
            ttk.Label(main_frame, text="间隔小时数:", font=label_font).grid(row=2, column=0, sticky="w", pady=5, padx=5)
            interval_entry = ttk.Entry(main_frame, font=entry_font)
            interval_entry.insert(0, str(current_interval))
            interval_entry.grid(row=2, column=1, padx=5, pady=5)

        # ====== 24小时模式保持原有逻辑 ======    
        else:
            # ▼▼▼ 原24小时模式代码 ▼▼▼
            def format_hhmm(dt):
                return dt.strftime("%H:%M")

            # 刻度间隔（分钟）
            tick_locs = ax.xaxis.get_ticklocs()
            current_minutes = int(24*60*(tick_locs[1]-tick_locs[0])) if len(tick_locs) >1 else 60
        
            ttk.Label(main_frame, text="间隔分钟数:", font=label_font).grid(row=0, column=0, sticky="w", pady=5, padx=5)
            interval_entry = ttk.Entry(main_frame, font=entry_font)
            interval_entry.insert(0, str(current_minutes))
            interval_entry.grid(row=0, column=1, padx=5, pady=5)

            ttk.Label(main_frame, text="开始时间:", font=label_font).grid(row=1, column=0, sticky="w", pady=5, padx=5)
            start_entry = ttk.Entry(main_frame, font=entry_font)
            start_entry.insert(0, format_hhmm(xmin))
            start_entry.grid(row=1, column=1, padx=5, pady=5)

            ttk.Label(main_frame, text="结束时间:", font=label_font).grid(row=2, column=0, sticky="w", pady=5, padx=5)
            end_entry = ttk.Entry(main_frame, font=entry_font)
            end_entry.insert(0, format_hhmm(xmax))
            end_entry.grid(row=2, column=1, padx=5, pady=5)

        def apply_changes():
            try:
                if current_mode == "longterm":
                    # ▼▼▼ 长期模式解析逻辑 ▼▼▼
                    # 转换输入时间为datetime对象（处理年份自动保留）
                    start_dt = datetime.strptime(start_entry.get(), "%m-%d %H:%M").replace(year=xmin.year)
                    end_dt = datetime.strptime(end_entry.get(), "%m-%d %H:%M").replace(year=xmax.year)
                
                    # 如果开始时间晚于结束时间则增加一年（处理跨年数据）
                    if start_dt > end_dt:
                        end_dt = end_dt.replace(year=start_dt.year + 1)

                    # 设置时间范围和刻度
                    ax.set_xlim(start_dt, end_dt)
                    ax.xaxis.set_major_locator(mpl.dates.HourLocator(interval=int(interval_entry.get())))
                    ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%m-%d %H:%M"))
                
                else:
                    # ▼▼▼ 原24小时模式逻辑 ▼▼▼
                    start_time = datetime.strptime(start_entry.get(), "%H:%M").time()
                    end_time = datetime.strptime(end_entry.get(), "%H:%M").time()
                
                    # 合并日期（保持原日期不变）
                    new_start = datetime.combine(xmin.date(), start_time)
                    new_end = datetime.combine(
                        xmin.date() + pd.DateOffset(days=1) if end_time <= start_time else xmin.date(),
                        end_time
                    )

                    ax.set_xlim(new_start, new_end)
                    ax.xaxis.set_major_locator(
                        mpl.dates.MinuteLocator(interval=int(interval_entry.get()))
                    )
                    ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%H:%M"))

                # 刷新对应画布
                if current_mode == "24h":
                    self.canvas_24h.draw()
                else:
                    self.canvas_lt.draw()
                
                dialog.destroy()

            except Exception as e:
                error_type = "时间格式" if "does not match format" in str(e) else "配置错误"
                messagebox.showerror("输入错误", 
                    f"{error_type}:\n长期模式应使用 mm-dd hh:mm 格式\n示例: 06-15 08:00" if current_mode == "longterm" else str(e))

        # ▼▼▼ 应用按钮 ▼▼▼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4 if current_mode == "longterm" else 3, 
                      columnspan=2, pady=20, sticky='se')
    
        ttk.Button(btn_frame, text="应用", 
                  command=apply_changes,
                  style='Accent.TButton').pack(padx=10, ipadx=15)

    

    def clear_cache(self):
        """安全清空所有缓存数据"""
        self.file_cache.clear()          # 清空文件扫描缓存
        self.last_scan_folder = ""       # 重置扫描标记
        self.selected_folder.set("")     # 清空选中文件夹显示
        
        # 清空24小时模式的参数选择
        if self.param_combobox['values']:
            self.param_combobox.set('')
        
        # 清空长期模式的参数选择
        if self.param_combobox_lt['values']:
            self.param_combobox_lt.set('')
        
        messagebox.showinfo("系统提示", "所有缓存已成功清除")

 
    def on_close(self):
        plt.close('all')  # 关闭所有matplotlib图形
        self.root.destroy()  # 彻底销毁窗口

if __name__ == "__main__":
    root = tk.Tk()
    
    # 设置窗口图标（路径必须是 .ico 文件）
    root.iconbitmap('smart_log.ico')

    # 统一配置所有组件样式（新增LabelFrame样式）
    style = ttk.Style()
    style.theme_use('clam')
    # 配置LabelFrame标题字体（新增部分）
    style.configure('TLabelframe', 
                   font=('Microsoft YaHei', 20),
                   relief='raised')
    style.configure('TLabelframe.Label',
                   font=('Microsoft YaHei', 20, 'bold'),
                   foreground='#2c3e50')  # 标题文字颜色
    
    # 原有按钮样式配置
    style.configure('TButton', font=('Microsoft YaHei', 18), padding=5)
    style.configure('Accent.TButton', 
                   font=('Microsoft YaHei', 18, 'bold'), 
                   foreground='white', 
                   background='#4a90e2')
    
     # 新增 Combobox 字体配置（关键修改部分）
    style.configure('TCombobox',
                    font=('Microsoft YaHei', 18),            # 输入框字体
                    fieldbackground='white',                 # 输入框背景色（可选）
                    selectbackground='#4a90e2')              # 选中项背景色（可选）

    # 下拉菜单列表项字体需要单独配置（部分主题支持）
    style.configure('TCombobox.Listbox',
                    font=('Microsoft YaHei', 18),            # 下拉列表字体  
                    relief='flat')                           # 去除边框（可选）
    
    # 如果使用 "clam" 主题还需以下偏移调整（预防文字截断）
    style.configure('TCombobox', postoffset=(0,0,0,5))       # 调整下拉框底部间距

    style.configure('TMenu', 
               font=('Microsoft YaHei', 16),
               background='#f0f0f0')
    style.configure('TMenu.Label', 
               font=('Microsoft YaHei', 16))
    
    app = LogAnalyzerApp(root)
    root.mainloop()