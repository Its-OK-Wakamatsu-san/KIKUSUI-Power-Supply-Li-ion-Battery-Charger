# windows timer precision ... 15.625msec ... 1/64 second. 
import os
import os.path
import queue
import threading
import sys
import datetime
import time
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.ttk import Combobox
from tkinter import scrolledtext
from tkinter import messagebox, filedialog
import numpy as np
import pandas as pd
from numpy.linalg import solve
from matplotlib import cm
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy import interpolate
import KIKUSUI_PMX18_5A_module


# Constant Voltage Control
class Application(tk.Frame):
    def __init__(self, master):
        super(Application, self).__init__(master)
        
        self.ini_dir = os.path.dirname(__file__).replace(os.sep,'/')        # get present program directory
        self.str_time_full = datetime.datetime.now().strftime('%Y%m%d_%H%M%S') 
        #print(self.str_time ) 


        # Flag
        self.flag_exec      = False             #True  .. Executed  
        #self.flag_scheduled = False            #True  .. timed schedule_mode
        self.stop_threads   = False             #False .. Continue
        self.flag_trangent  = True              #True .. trangent(T) / stable(F)
        self.flag_remote    = False             #False .. Local
        self.flag_ready     = False             #False .. Disable
        self.flag_pause     = False             #True  .. Pause    False .. Resume
        self.flag_manual    = False             #True  .. Manual   

        self.master.geometry("1200x900+400+0")             # TK window size(width x height & Left Top)
        str_prog_name = os.path.basename(__file__)      # get present program name
        self.master.title( str_prog_name )

        #-----------------------------------------------
        # matplotlib配置用フレーム
        frame = tk.Frame(self.master) 
        plt.ion()
        # matplotlibの描画領域の作成
        fig = Figure(figsize=(7,4))
        # 座標軸の作成
        self.ax = fig.add_subplot(1, 1, 1)
        #Y軸　第2軸
        self.ax2= self.ax.twinx()       
        # matplotlibの描画領域とウィジェット(Frame)の関連付け
        self.fig_canvas = FigureCanvasTkAgg(fig, frame)
        # matplotlibのツールバーを作成
        self.toolbar = NavigationToolbar2Tk(self.fig_canvas, frame)
        # matplotlibのグラフをフレームに配置
        self.fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # plotフレームをウィンドウに配置
        frame.place(x=450, y=000)

        # Preset Color for Button(tkinter)
        self.color_green = str('#ccffaa') #green
        self.color_gray  = str('#f2f2f2') #gray(Back ground color)
        self.color_red   = str('#ffaacc') #red


        #tab instance
        tab=ttk.Notebook(root,width=400,height=950)
        #tabのフレーム作成
        self.tab1=tk.Frame(tab)
        self.tab2=tk.Frame(tab)

        tab.add(self.tab1,text='Power Supply Control',padding=3)
        tab.add(self.tab2,text='Power Supply Option ',padding=3) 
        tab.pack(anchor="nw")

        # Power Supply Control Panel
        self.Power_Supply_Control_Panel()
        self.Power_Supply_Option_Panel()

    

    def Power_Supply_Control_Panel(self):

        # ラベル &   # テキストボックス
        lbl_1  = tk.Label(self.tab1,text='Time Interval_trangent(sec)')
        lbl_1.grid(row=6, column=0, padx=5, pady=5)
        self.txt_1 = tk.Entry(self.tab1,width=15)
        self.txt_1.insert(0, '0.5')
        self.txt_1.grid(row=6, column=1, padx=5, pady=5)
        lbl_11  = tk.Label(self.tab1,text='Time Interval_stable state(sec)')
        lbl_11.grid(row=7, column=0, padx=5, pady=5)
        lbl_12  = tk.Label(self.tab1,text='pre-programed 10sec')
        lbl_12.grid(row=7, column=1, padx=5, pady=5)
        lbl_2  = tk.Label(self.tab1,text='Elapsed Time(s)')
        lbl_2.grid(row=8, column=0, padx=5, pady=5)
        self.txt_2 = tk.Entry(self.tab1,width=15)
        self.txt_2.grid(row=8, column=1, padx=5, pady=5)

        # Power Supply
        lbl_3  = tk.Label(self.tab1,text='Power Supply Satatus')
        lbl_3.grid(row=15, column=0, padx=5, pady=5)
        self.btn_31 = tk.Button(self.tab1, text=' Get Current & Voltage ', command=self.PS_Get_data_Cmd, height=1, bg = self.color_gray)
        self.btn_31.grid(row=15, column=1, padx=5, pady=5)

        lbl_33  = tk.Label(self.tab1,text='Power Supply Current(A)')
        lbl_33.grid(row=16, column=0, padx=5, pady=5)
        self.txt_33 = tk.Entry(self.tab1,width=15)
        self.txt_33.grid(row=16, column=1, padx=5, pady=5)
        lbl_34  = tk.Label(self.tab1,text='Power Supply Voltage(V)')
        lbl_34.grid(row=17, column=0, padx=5, pady=5)
        self.txt_34 = tk.Entry(self.tab1,width=15)
        self.txt_34.grid(row=17, column=1, padx=5, pady=5)
        
        #Button
        self.btn_1 = tk.Button(self.tab1, text='Enable Remote Mode', command=self.PS_Remote_Enable, height=1, bg = self.color_green)
        self.btn_1.grid(row=21, column=0, padx=5, pady=5)
        self.btn_11 = tk.Button(self.tab1, text='Back to Local Mode', command=self.PS_Change_Local, height=1, bg = self.color_red)
        self.btn_11.grid(row=21, column=1, padx=5, pady=5)
        self.btn_2 = tk.Button(self.tab1, text='PowerSupply Ready', command=self.PS_Ready_Cmd, height=1, bg = self.color_green)
        self.btn_2.grid(row=22, column=0, padx=5, pady=5)
        self.btn_21 = tk.Button(self.tab1, text='PowerSupply Disable', command=self.PS_Disable_Cmd, height=1, bg = self.color_red)
        self.btn_21.grid(row=22, column=1, padx=5, pady=5)

        self.btn_7 = tk.Button(self.tab1, text='Manual Mode(Voltage(V),rate=0.1V/interval)', command=self.PS_Manual_Mode, height=1, bg = self.color_green)
        self.btn_7.grid(row=27, column=0, padx=5, pady=5)
        self.txt_71 = tk.Entry(self.tab1,width=15)     #Manual input voltage
        self.txt_71.grid(row=27, column=1, padx=5, pady=5)
        self.txt_71.insert(0, '7.8')

        self.btn_50 = tk.Button(self.tab1, text='Start', command=self.Threading_Framework, height=1, bg = self.color_green)
        self.btn_50.grid(row=31, column=0, padx=5, pady=5)
        self.btn_51 = tk.Button(self.tab1, text='Stop', command=self.Terminate, height=1, bg = self.color_green)
        self.btn_51.grid(row=31, column=1, padx=5, pady=5)

        self.btn_6 = tk.Button(self.tab1, text='Pause//Resume', command=self.Pause_Resume_click, height=1, bg = self.color_green)
        self.btn_6.grid(row=36, column=0, padx=5, pady=5)

        self.btn_40 = tk.Button(self.tab1, text='Output File path', command=self.Set_File_path, height=1, bg = self.color_gray)
        self.btn_40.grid(row=41, column=0, padx=5, pady=5)
        self.btn_41 = tk.Button(self.tab1, text='Output File', command=self.__File_Out, height=1, bg = self.color_green)
        self.btn_41.grid(row=41, column=1, padx=5, pady=5)

        #ScrolledTextウィジェットを作成
        lbl_8  = tk.Label(self.tab1,text='Log')
        lbl_8.place(x=5, y=430)
        self.strings = scrolledtext.ScrolledText(self.tab1,  width=50,  height=30 , background=self.color_gray)
        self.strings.place(x=0, y=450)

        # Assign Instrument
        self.Assign_Instrument()

    def Power_Supply_Option_Panel(self):

        # Power Supply Limit
        lbl_90  = tk.Label(self.tab2,text='Voltage Protect Limit(%)')
        lbl_90.grid(row=6, column=0, padx=5, pady=5)
        lbl_90A  = tk.Label(self.tab2,text='(V)')
        lbl_90A.grid(row=6, column=3, padx=5, pady=5)
        self.txt_90 = tk.Entry(self.tab2,width=10)
        self.txt_90.insert(0, '105')
        self.txt_90.grid(row=6, column=1, padx=5, pady=5)
        self.txt_90A = tk.Entry(self.tab2,width=10)
        volt_prot_V = 18 * float(self.txt_90.get()) /100
        self.txt_90A.insert(0, volt_prot_V)
        self.txt_90A.grid(row=6, column=2, padx=5, pady=5)
        lbl_91  = tk.Label(self.tab2,text='Current Protect Limit(%)')
        lbl_91.grid(row=7, column=0, padx=5, pady=5)
        lbl_91A  = tk.Label(self.tab2,text='(A)')
        lbl_91A.grid(row=7, column=3, padx=5, pady=5)
        self.txt_91 = tk.Entry(self.tab2,width=10)
        self.txt_91.insert(0, '105')
        self.txt_91.grid(row=7, column=1, padx=5, pady=5)
        self.txt_91A = tk.Entry(self.tab2,width=10)
        curr_prot_A = 5 * float(self.txt_91.get()) /100
        self.txt_91A.insert(0, curr_prot_A)
        self.txt_91A.grid(row=7, column=2, padx=5, pady=5)
        
        #Button
        self.btn_90 = tk.Button(self.tab2, text='Set new Limit Voltage', command=self.PS_Voltage_Protect, height=1, bg = self.color_green)
        self.btn_90.grid(row=21, column=0, padx=5, pady=5)
        self.btn_91 = tk.Button(self.tab2, text='Set new Limit Current', command=self.PS_Current_Protect, height=1, bg = self.color_green)
        self.btn_91.grid(row=22, column=0, padx=5, pady=5)


    def Assign_Instrument(self):
        # Set Instrument module 
        try:        
            self.KIKUSUI_PS_USB = KIKUSUI_PMX18_5A_module.Application()
            str_comment = "利用可能なリソース:" + str(self.KIKUSUI_PS_USB.get_resources())
            print(str_comment)
            #print("利用可能なリソース:", self.KIKUSUI_PS_USB.get_resources())
            addr = self.KIKUSUI_PS_USB.get_resources()[0]
            ok, msg = self.KIKUSUI_PS_USB.Open(addr)
            print(msg)
            msg += str_comment 
            '''
            self.KIKUSUI_PS_USB = KIKUSUI_PMX18_5A_module.Application()
            foundResources = self.KIKUSUI_PS_USB.get_resources()
            print("利用可能なリソース:", foundResources)

            str_comment = "利用可能なリソース:\n" + str(foundResources) + '\n'
            # VISA Resourceラベルの配置
            label1 = ttk.Label(self.tab1, text='VISA Resource')
            label1.grid(row=0, column=0)

            # 制御装置一覧を表示するコンボボックスの配置
            cb1 = ttk.Combobox(self.tab1, values=foundResources)
            cb1.set(foundResources[0])
            cb1.grid(row=0, column=1, columnspan=2, sticky=tk.W+tk.E)

            # Openボタンの配置
            button1 = ttk.Button(self.tab1, text='Open', command=self.Kikusui_Open)
            button1.grid(row=1, column=0, sticky=tk.W+tk.E)

            addr = self.KIKUSUI_PS_USB.get_resources()[0]
            print("接続先アドレス:", addr)
            '''
            str_comment = ''
            str_comment += msg + '\n'

        except Exception as e:
            str_comment = 'KIKUSUI_PMX18_5A is Not Found.\n'
        self.strings.insert(tk.END, str_comment)
        self.strings.see('end')     #自動で最新までスクロール   
   
        return

        
    def Threading_Framework(self):
        # initialized
        self.btn_7.configure( bg = self.color_gray )
        self.flag_exec = True
        # set queues
        queue1 = queue.Queue()  # queue1 is on, when self.flag_exec= True.
        queue2 = queue.Queue()  # queue2 is on, when NI_USB6501 pin assignment start.
        queue3 = queue.Queue()  # queue3 is on, when Plot_A finished.

        tTC = threading.Thread(target=self.Time_Control, args=(queue1,queue3,))     # Time Controller
        tPA = threading.Thread(target=self.Asynchro_Plot_A, args=(queue1,queue3,))  # CV power supply is based on a time schedule.

        tTC.start()
        time.sleep(0.05)
        tPA.start()

        return
    
    def Time_Control(self,queue1,queue3):
        self.interval_t = float(self.txt_1.get())
        self.wait_time  = self.interval_t              #  adjust mili-seconds
        self.time_old = self.time_0 = time.time()
        self.Elapsed_time(self.time_0)
        
        while True:
            if self.stop_threads:
                # interval time set
                time.sleep(self.wait_time)
                return
            if self.flag_exec == False :
                 # interval time set
                time.sleep(self.wait_time)
                return
            
            #adjust interval time trnaget(short time)   stable(long time)
            if self.flag_trangent :
                self.interval_t = float(self.txt_1.get())
            else:
                self.interval_t = 10.0
            
            # threading  queue
            if self.flag_exec:
                queue1.put('from thread1') 
            
            # interval time set
            time.sleep(self.wait_time)
            # threading  queue
            queue3.get()
            
            # adjust wait_time
            time_instant = time.time()
            turnaround_time =  time_instant - self.time_old
            self.time_old = time_instant
            self.wait_time += (self.interval_t - turnaround_time)
            if self.wait_time <= 0.001:                                 # to prevent negative time
                self.wait_time = 0.001
            
        return

    def Asynchro_Plot_A(self,queue1,queue3):
        # Plot initialize   
        self.str_time_full = str(datetime.datetime.now()) 
        #self.str_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.str_time = datetime.datetime.now().strftime('%Y%m%d_%H%M')  
        #print(self.str_time ) 
        str_comment = self.str_time + '\n'
        self.strings.insert(tk.END, str_comment)
        self.strings.see('end')     #自動で最新までスクロール

        plt.ion()   #Interactive mode ON
        t_pause_m = 0.0
        voltage_t = voltage_t_old = 0.0
        self.num = 0
        self.x  = []
        self.t  = []
        self.y0 = []
        self.y1 = []
        self.y2 = []


        self.x.append(0.0)
        self.t.append(0.0)
        self.y0.append(0.0)
        self.y1.append(0.0)
        self.y2.append(0.0)

        Label_0 = 'Voltage(V)_req'
        Label_1 = 'Voltage(V)'
        Label_2 = 'Current(A)'
        self.ax.set_xlabel('time [$minutes$]')
        self.ax.set_ylabel('Voltage [$V$]')
        self.ax2.set_ylabel('Current [$A$]')
        self.ax.set_title('KIKUSUI Power Supply(Constant Voltage)')
        self.line0, = self.ax.plot(self.t, self.y0,color='C0', linestyle='--',label=Label_0)
        self.line1, = self.ax.plot(self.t, self.y1,color='C1', label=Label_1)
        self.line2, = self.ax2.plot(self.t, self.y2,color='C2', label=Label_2)

        #self.ax.legend()
        #self.ax2.legend()
        # 以下追加部分
        # -----------------------------------------
        lines_1, labels_1 = self.ax.get_legend_handles_labels()
        lines_2, labels_2 = self.ax2.get_legend_handles_labels()

        lines = lines_1 + lines_2
        labels = labels_1 + labels_2

        self.ax.legend(lines, labels)
        # -----------------------------------------

        while True:

            self.num += 1
            #print('self.num = ',self.num)
            # threading  queue
            queue1.get()

            #Pause//Resume
            if self.flag_pause :
                t_pause_m = t_pause_m + self.interval_t / 60              #pause time
                queue3.put('from thread4')
            else:
                #measurement
                self.Elapsed_time(self.time_0)
                self.elapsed_t_m = self.elapsed_t / 60                   #elapsed time(minutes)
                voltage_manual = abs(float(self.txt_71.get()))

                if self.flag_manual:
                    if self.flag_trangent :
                        voltage_manual = abs(float(self.txt_71.get()))
                    else:
                        voltage_manual = float(self.txt_71.get())
                    #print('voltage_manual = ', voltage_manual)
                    t_pause_m = t_pause_m + self.interval_t / 60          #pause time
                    str_comment  = ' Elapsed_time(min) = ' + str(t_pause_m) + '\n'
                    str_comment += ' target_voltage(V) = ' + str(voltage_manual) + '\n'
                    self.strings.insert(tk.END, str_comment)
                    self.strings.see('end')     #自動で最新までスクロール
                    
                    # manual voltage cmd makes ramp shape (0.1V/step)
                    if voltage_manual > voltage_t:
                        voltage_t += 0.1
                        self.flag_trangent = True
                        if voltage_t > voltage_manual:
                            voltage_t = voltage_manual
                            self.flag_trangent = False
                    elif voltage_manual < voltage_t:
                        voltage_t -= 0.1
                        self.flag_trangent = True
                        if voltage_t < voltage_manual:
                            voltage_t = voltage_manual
                            self.flag_trangent = False

                else:
                    '''
                    voltage_target = self.Function_voltage(self.elapsed_t_m - t_pause_m)    #voltage_target(adjust_time)

                    # make voltage cmd a ramp shape (0.1V/step) ... when gets back on timed schdule mode from manual mode
                    if (voltage_target - voltage_t_old) > 0.1:
                       voltage_target = voltage_t_old + 0.1
                    if (voltage_target - voltage_t_old) < -0.1:
                       voltage_target = voltage_t_old - 0.1
                    voltage_t =float( str(f'{voltage_target:.3f}'))
                    
                    '''
                    pass
                voltage_t_old = voltage_t    

                #Set voltage cmd
                self.PS_Set_Cmd(voltage_t)
                #Get Current & Voltage cmd
                buf1i,buf1v = self.PS_Get_data_Cmd()
                #print('elapsed_time(s) = ',self.elapsed_t)
                self.x.append(self.elapsed_t)
                self.t.append(self.elapsed_t_m)
                self.y0.append(voltage_t)
                self.y1.append(buf1v)
                self.y2.append(buf1i)

                if len(self.y1)>2:
                    # Axis ReScaling
                    x_max = np.max([self.t])
                    x_min = np.min([self.t])
                    x_diff = x_max-x_min
                    x_max  += 0.1 * x_diff  # add ±10%
                    x_min  -= 0.1 * x_diff
                    self.ax.set_xlim(x_min, x_max)
                    y_max =np.max([self.y0])
                    y_min =np.min([self.y0])
                    y_diff = y_max-y_min
                    y_max  += 0.1 * y_diff  # add ±10%
                    y_min  -= 0.1 * y_diff
                    self.ax.set_ylim(y_min, y_max)
                    # 2nd Axis ReScaling
                    y2_max =np.max([self.y2])
                    y2_min =np.min([self.y2])
                    y2_diff = y2_max-y2_min
                    y2_max  += 0.3 * y2_diff  # add +30%/-10%
                    y2_min  -= 0.1 * y2_diff
                    self.ax2.set_ylim(y2_min, y2_max)

                #line update
                self.line0.set_xdata(self.t)
                self.line0.set_ydata(self.y0)
                self.line1.set_xdata(self.t)
                self.line1.set_ydata(self.y1)
                self.line2.set_xdata(self.t)
                self.line2.set_ydata(self.y2)

                self.fig_canvas.draw()
                self.fig_canvas.flush_events()
                
                # threading  queue
                queue3.put('from thread4')

        return
     
   
    def __File_Out(self):
        # Header
        str_prog_name = os.path.basename(__file__) # get present program name
        #str_time      = str(datetime.datetime.now()) 
        str_row0   = "  ,  "+ str_prog_name + "  ,  " + self.str_time_full + str(self.txt_1)
        str_row1   = "  flowtime(min) , time(s)  , voltage_target(V) , Voltage(V) , Current(A) "
        str_header = str_row0 + " \n " + str_row1  # \n 改行
        # Data

        array_x  = np.array( self.x )
        array_t  = np.array( self.t )
        array_y0 = np.array( self.y0 )
        array_y1 = np.array( self.y1 )
        array_y2 = np.array( self.y2 )


        # Data  stack
        array_2 = np.column_stack(( array_x ,array_t, array_y0, array_y1 ,array_y2 ))
        #print(array_2)

        # CSV file Out put
        file_path = self.ini_dir + '/KIKUSUI_CV_' + self.str_time + '.csv'
        str_comment = str(file_path) + '\n'
        np.savetxt( file_path ,  array_2 , delimiter=',', header=str_header, comments='#',fmt=['%.6e', '%.6e', '%.6e', '%.6e', '%.6e',] )
        str_def_Func = sys._getframe().f_code.co_name           #Function name get
        print(  " def ", str_def_Func , " was finished " )   
        str_comment =   " def " + str_def_Func + " was finished "  +'\n'
        self.strings.insert (tk.END, str_comment)
        self.strings.see('end')     #自動で最新までスクロール
        self.btn_41.configure( bg = self.color_gray)
        return
    
    def Set_File_path(self):
        #20221108 add defaultextension = ""  ....「ファイルの種類」で指定された拡張子で、自動で拡張子が付加されます
        filename=filedialog.asksaveasfilename(initialdir=self.ini_dir, filetypes=self.typelist1, title="Set Output File path", defaultextension = "")
        if filename == "":
            return
        else:
            self.file_path1 = filename
            self.f_root, self.ext = os.path.splitext(self.file_path1)
            self.ini_dir = self.f_root
            print('Set Output File path =' , os.path.abspath(self.file_path1))
            str_comment =   'Set Output File path =' + os.path.abspath(self.file_path1)  +'\n'
            self.strings.insert (tk.END, str_comment)
            self.strings.see('end')     #自動で最新までスクロール
            return
        
    def Pause_Resume_click(self):
        #Flag change 
        if self.flag_pause  : 
            self.btn_6.configure(bg = self.color_green)
        else:
            self.btn_6.configure(bg = self.color_red)
        self.flag_pause = not self.flag_pause
        return
    
    def PS_Scheduled_Mode(self):
        self.flag_manual    = not self.flag_manual
        #Flag change 
        if self.flag_manual  : 
            self.btn_7.configure(bg = self.color_red)
        else:
            self.btn_7.configure(bg = self.color_gray)
        return
        
    def PS_Manual_Mode(self):
        self.flag_manual = not self.flag_manual
        #Flag change 
        if self.flag_manual  : 
            self.btn_7.configure(bg = self.color_red)
        else:
            self.btn_7.configure(bg = self.color_gray)
        return

    def PS_Remote_Enable(self):
        'SYST:REMOTE'       # Cmd Change Local to Remote
        self.KIKUSUI_PS_USB.Write_Command('SYST:REMOTE')
        self.flag_remote = True
        self.btn_1.configure( bg = self.color_gray)
        return
    
    def PS_Change_Local(self):
        'SYST:LOCAL'       # Cmd Change Remote to Local
        self.KIKUSUI_PS_USB.Write_Command('SYST:LOCAL')
        self.flag_remote = False
        self.btn_11.configure( bg = self.color_gray)
        return
    
    def PS_Ready_Cmd(self):
        '#AL VCN 100'   # Cmd Set Voltage CNTL(%)
        '#AL OCP 100'   # Cmd Set Over Current(%)
        '#AL ISET 0.0'  # Cmd Set Current 0.0(A)    ... Constant voltage Mode
        'OUTP ON'       # Cmd Switch on             ... 1..On
        #self.KIKUSUI_PS_USB.Write_Command('#AL VCN 100')
        #self.KIKUSUI_PS_USB.Write_Command('#AL OCP 100')
        #self.KIKUSUI_PS_USB.Write_Command('#AL ISET 0.0')
        self.KIKUSUI_PS_USB.Write_Command('CURR 0.001') #set minimum current 0.001(A)
        self.KIKUSUI_PS_USB.Write_Command('OUTP ON')
        self.KIKUSUI_PS_USB.Write_Command('VOLT 0.0')   #set voltage to 0.0(V)
        self.btn_2.configure( bg = self.color_gray)
        self.flag_ready = True
        return 
    
    def PS_Disable_Cmd(self):
        'VOLT 0'    # Cmd Set voltage 0.0(V)    ... Constant voltage Mode
        'OUTP OFF'  # Cmd Power Supply off      ... Off
        self.KIKUSUI_PS_USB.Write_Command('VOLT 0.0')
        self.KIKUSUI_PS_USB.Write_Command('OUTP OFF')
        self.btn_21.configure( bg = self.color_gray)
        self.flag_ready = False
        return
    

    def PS_Get_data_Cmd(self):
        'MEAS:CURR?'       # Query  current(A)
        'MEAS:VOLT?'       # Query  voltage(V)
        buf   = self.KIKUSUI_PS_USB.Query('MEAS:CURR?')
        buf1i = float(buf)
        buf   = self.KIKUSUI_PS_USB.Query('MEAS:VOLT?')
        buf1v = float(buf)
        self.txt_33.delete (0,'end')
        self.txt_33.insert(0, buf1i)
        self.txt_34.delete (0,'end')
        self.txt_34.insert(0, buf1v)
        return buf1i,buf1v
    
    def PS_Set_Cmd(self, volt_now):
        cmd = 'VOLT ' + str(volt_now)
        self.KIKUSUI_PS_USB.Write_Command(cmd)
        return
    
    def PS_Voltage_Protect(self):
        cmd = 'VOLT:PROT ' + str(self.txt_90.get())
        self.KIKUSUI_PS_USB.Write_Command(cmd)
        self.btn_90.configure( bg = self.color_gray)
        return
    
    def PS_Current_Protect(self):
        cmd = 'CURR:PROT ' + str(self.txt_91.get())
        self.KIKUSUI_PS_USB.Write_Command(cmd)
        self.btn_91.configure( bg = self.color_gray)
        return

    def Elapsed_time(self,time_0):
        # elapsed time
        time_1 = time.time()
        self.elapsed_t =time_1-time_0
        self.txt_2.delete(0,'end')
        self.txt_2.insert(tk.END , f'{self.elapsed_t:.3f}')   #  ←小数点以下3桁表示  
        return
        
    def Terminate(self):
        self.stop_threads = True 
        self.PS_Disable_Cmd()
        self.btn_51.configure( bg = self.color_gray)
        self.KIKUSUI_PS_USB.Close()
        return
    
if __name__ == '__main__':
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()