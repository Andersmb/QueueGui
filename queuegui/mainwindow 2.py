import tkinter as tk
from tkinter import simpledialog, messagebox
from collections import OrderedDict
from datetime import datetime, timedelta
import shutil
import os
import re
import requests
import paramiko as pmk
import subprocess
import matplotlib
matplotlib.use("tkagg")
import matplotlib.pyplot as plt

from preferences import Preferences
from toolbox import ToolBox
from convertme import ConvertMe
from job import Job
import helpers

from output_parsers.gaussian import GaussianOut
from output_parsers.orca import OrcaOut
from output_parsers.mrchem import MrchemOut


#TODO use the Job class get job info throughout the code



class MainWindow(tk.Frame):
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.parent = parent
        self.winfo_toplevel().title(f"QueueGui: <{self.parent.user.get()}@{self.parent.cluster_data[self.parent.host.get()]['hostname']}>")

        # Define variables
        self.do_queue_monitoring = tk.BooleanVar()
        self.do_queue_monitoring.set(False)
        self.status = tk.StringVar()
        self.selected_text = tk.StringVar()
        self.user = tk.StringVar()
        self.jobhisfilter = tk.StringVar()
        self.job_starttime = tk.StringVar()
        self.selected_text = tk.StringVar()
        self.current_file = tk.StringVar()
        self.output_last_update = tk.StringVar()
        self.url_readme = "https://raw.githubusercontent.com/Andersmb/QueueGui/master/README.md"

        # We have to once again establish the connection to the remote cluster
        # (apparently the established connection from Login does not hold)
        hostname = self.parent.cluster_data[self.parent.host.get()]["hostname"]
        self.ssh_client = pmk.SSHClient()

        self.ssh_client.set_missing_host_key_policy(pmk.AutoAddPolicy())
        self.ssh_client.connect(hostname=hostname,
                                username=self.parent.user.get(),
                                password=self.parent.pwd.get())
        transport = pmk.Transport((hostname, 22))
        transport.connect(None, self.parent.user.get(), self.parent.pwd.get())
        self.sftp_client = pmk.SFTPClient.from_transport(transport)

        # Place the widgets
        self.place_widgets()

        # Print the queue and start monitoring functions
        self.print_q()
        self.monitor_q()
        self.monitor_selected_text()
        self.log_update(f"Welcome to {self.parent.name}!")

    def place_widgets(self):
        # Configure columns and rows. Allow for resizing in appropriate directions
        self.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Set up the grids
        self["bg"] = self.parent.background_color.get()
        self.topleft = tk.Frame(self, bg=self.parent.background_color.get())
        self.topright = tk.Frame(self, bg=self.parent.background_color.get())
        self.mid = tk.Frame(self, bg=self.parent.background_color.get())
        self.bot = tk.Frame(self, bg=self.parent.background_color.get())

        self.topleft.grid(row=0, column=0, sticky="w")
        self.topright.grid(row=0, column=1, sticky="nsew")
        self.mid.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.bot.grid(row=2, column=0, columnspan=2, sticky="sw")

        self.topright.columnconfigure(0, weight=1)
        self.mid.columnconfigure(0, weight=1)
        self.mid.rowconfigure(0, weight=1)

        # Define options and set defaults
        self.jobhisfilter.set("")
        self.job_starttime_options = [datetime.now().date() - timedelta(days=i) for i in
                                      range(self.parent.job_history_length.get())]
        self.job_starttime.set(datetime.now().date())

        self.status_options = OrderedDict()
        self.status_options["All Jobs"] = "all"
        self.status_options["Running Jobs"] = "r"
        self.status_options["Pending Jobs"] = "pd"
        self.status_options["Completed Jobs"] = "cd"
        self.status_options["Cancelled Jobs"] = "ca"
        self.status_options["Timeouted Jobs"] = "to"
        self.status.set(list(self.status_options.keys())[0])  # set default value to "All Jobs"

        # Define the top menu bar
        menubar = tk.Menu(self.parent)
        systemmenu = tk.Menu(menubar)
        systemmenu.add_command(label="Preferences", command=self.launch_preferences)
        systemmenu.add_command(label="Log out", command=self.logout)
        systemmenu.add_separator()
        systemmenu.add_command(label="Quit", command=self.parent.destroy)

        toolmenu = tk.Menu(menubar)
        toolmenu.add_command(label="Check CPU Usage", command=self.cpu_usage)
        toolmenu.add_command(label="Print Orca SCF convergence", command=self.orca_scf_convergence)
        toolmenu.add_command(label="Plot Orca SCF convergence")
        toolmenu.add_separator()
        toolmenu.add_command(label="Kill job range", command=self.kill_range)

        helpmenu = tk.Menu(menubar)
        helpmenu.add_command(label="User Manual", command=self.show_user_manual)
        helpmenu.add_command(label=f"About {self.parent.name}", command=self.show_about_page)

        menubar.add_cascade(label="System", menu=systemmenu)
        menubar.add_cascade(label="Tools", menu=toolmenu)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.master.configure(menu=menubar)

        # Buttons
        tk.Button(self.topleft,
                  text="Get queue",
                  command=self.print_q,
                  font=self.parent.main_font).grid(row=1, column=0, sticky="ew", pady=5, padx=5)
        tk.Button(self.topleft,
                  text="Output file",
                  command=self.open_output,
                  font=self.parent.main_font).grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        tk.Button(self.topleft,
                  text="Input file",
                  command=self.open_input,
                  font=self.parent.main_font).grid(row=1, column=2, sticky="ew", pady=5, padx=5)
        tk.Button(self.topleft,
                  text="Job script",
                  command=self.open_submitscript,
                  font=self.parent.main_font).grid(row=2, column=0)
        tk.Button(self.topleft, text="Job info", command=self.open_jobinfo, font=self.parent.main_font).grid(row=2, column=1)
        tk.Button(self.topleft,
                  text="Job History",
                  command=self.get_jobhistory,
                  font=self.parent.main_font).grid(row=2, column=2)
        tk.Button(self.topleft,
                  text="Check CPU usage",
                  command=self.cpu_usage,
                  font=self.parent.main_font).grid(row=0, column=2, sticky="ew", pady=5, padx=5)
        tk.Button(self.topleft,
                  text="Geometry converg.",
                  command=self.geometry_convergence,
                  font=self.parent.main_font).grid(row=1, column=3, sticky="ew", pady=5, padx=5)
        tk.Button(self.topleft,
                  text="Visualizer",
                  command=self.open_visualizer,
                  font=self.parent.main_font).grid(row=0, column=3, sticky="ew", pady=5, padx=5)
        tk.Button(self.topleft,
                  text="SCF converg.",
                  command=self.mrchem_plot_convergence,
                  font=self.parent.main_font).grid(row=3, column=3, pady=5, padx=5, sticky="ew")
        tk.Button(self.topleft,
                  text="Open .err",
                  command=self.open_error,
                  font=self.parent.main_font).grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        tk.Button(self.topleft,
                  text="MRC CHK",
                  command=self.store_mrchem_checkpoint,
                  font=self.parent.main_font).grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)
        tk.Button(self.bot,
                  text="Quit",
                  command=self.master.destroy,
                  font=self.parent.main_font,
                  fg="red",
                  bg="black").grid(row=0, column=0, pady=5, padx=5)
        tk.Button(self.bot,
                  text="Kill Selected Job",
                  command=self.kill_job,
                  font=self.parent.main_font).grid(row=0, column=1, pady=5, padx=5)
        tk.Button(self.bot,
                  text="Kill All Jobs",
                  command=self.kill_all_jobs,
                  font=self.parent.main_font).grid(row=0, column=2, pady=5, padx=5)
        tk.Button(self.bot,
                  text="ConvertMe!",
                  command=self.launch_convertme,
                  font=self.parent.main_font).grid(row=0, column=3, pady=5, padx=5)
        tk.Button(self.bot,
                  text="ToolBox",
                  command=self.launch_toolbox,
                  font=self.parent.main_font).grid(row=0, column=4, pady=5, padx=5)
        tk.Button(self.bot,
                  text="Backup scratch",
                  command=self.backup_scratch_files,
                  font=self.parent.main_font).grid(row=0, column=5, pady=5, padx=5)
        tk.Button(self.bot,
                  text="Update curr. file",
                  command=self.update_current_file,
                  font=self.parent.main_font).grid(row=0, column=6, pady=5, padx=5)

        # Option Menus
        optionmenu_jobhis_starttime = tk.OptionMenu(self.topleft, self.job_starttime, *self.job_starttime_options)
        optionmenu_jobhis_starttime.grid(row=2, column=3, sticky="ew")
        optionmenu_jobhis_starttime.config(font=self.parent.main_font)
        optionmenu_jobhis_starttime["menu"].config(font=self.parent.main_font)

        optionmenu_jobstatus = tk.OptionMenu(self.topleft, self.status, *self.status_options.keys())
        optionmenu_jobstatus.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        optionmenu_jobstatus.config(font=self.parent.main_font)
        optionmenu_jobstatus["menu"].config(font=self.parent.main_font)

        # Entries
        self.entry_user = tk.Entry(self.topleft, width=10)
        self.entry_user.grid(row=0, column=0, sticky="ew", pady=5, padx=5)
        self.entry_user.insert(0, self.parent.user.get())
        self.entry_user.bind("<Return>", self.print_q)

        self.entry_filter = tk.Entry(self.topleft, width=10)
        self.entry_filter.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        self.entry_filter.insert(0, self.jobhisfilter.get())
        self.entry_filter.bind("<Return>", self.filter_textbox)

        # Labels
        self.label_filter = tk.Label(self.topleft,
                                     font=self.parent.main_font,
                                     bg=self.master.background_color.get())
        self.label_filter["text"] = "Filter in ALL mode:" if self.parent.filter_mode.get() == 0 else "Filter in ANY mode:"
        self.label_filter.grid(row=3, column=0, sticky="ew", pady=5, padx=5)
        self.label_filter.bind("<Button-1>", self.update_filter_mode)

        self.filter_mode_gen = helpers.modulo_generator(length=1500, mod=2)
        next(self.filter_mode_gen)  # Get rid of first element

        self.label_selected_text = tk.Label(self.topleft,
                                            justify=tk.LEFT,
                                            text="<Selected PID goes here>",
                                            bg=self.master.background_color.get(),
                                            font=self.parent.main_font)
        self.label_output_last_update = tk.Label(self.topleft,
                                                 justify=tk.LEFT,
                                                 textvariable=self.output_last_update,
                                                 bg=self.master.background_color.get(),
                                                 font=self.parent.main_font).grid(row=4, column=3)

        self.label_selected_text.grid(row=4, column=0)
        self.label_selected_text.bind("<Button-2>", self.update_job)

        self.label_monitor_q = tk.Label(self.topleft,
                                        text="Running: 0\nPending: 0",
                                        bg=self.master.background_color.get())
        self.label_monitor_q.grid(row=4, column=1)

        # Current file
        tk.Label(self.topleft,
                 textvar=self.current_file,
                 bg=self.master.background_color.get(),
                 font=self.parent.main_font).grid(row=5, column=0, columnspan=3, pady=5, padx=5)

        # Check buttons
        tk.Checkbutton(self.topleft,
                       text="Monitor queue",
                       variable=self.do_queue_monitoring,
                       bg=self.master.background_color.get(),
                       command=self.monitor_q,
                       onvalue=True,
                       offvalue=False).grid(row=4, column=2)

        # Scroll bars
        q_yscrollbar = tk.Scrollbar(self.mid)
        q_yscrollbar.grid(row=0, column=1, sticky="ns", pady=2, padx=2)
        q_xscrollbar = tk.Scrollbar(self.mid, orient="horizontal")
        q_xscrollbar.grid(row=1, column=0, sticky="ew", pady=2, padx=2)

        log_yscrollbar = tk.Scrollbar(self.topright)
        log_yscrollbar.grid(row=0, rowspan=3, column=1, pady=2, padx=2, sticky="ns")

        # Text boxes
        self.txt = tk.Text(self.mid,
                           wrap=tk.NONE,
                           xscrollcommand=q_xscrollbar.set,
                           yscrollcommand=q_yscrollbar.set,
                           bg="black",
                           fg="white")
        self.txt.grid(row=0, column=0, sticky="nsew", pady=5, padx=5)
        self.txt.config(font=self.parent.queue_font, insertbackground='white')

        self.log = tk.Text(self.topright,
                           yscrollcommand=log_yscrollbar.set,
                           bg="black",
                           fg="white",
                           height=7,
                           width=90)
        self.log.grid(row=0, rowspan=3, column=0, pady=5, padx=5, sticky="nsew")
        self.log.config(font=self.parent.log_font)

        # Now apply the scroll bars, which must be done after the Text widgets have been properly set up
        q_yscrollbar.config(command=self.txt.yview)
        q_xscrollbar.config(command=self.txt.xview)
        log_yscrollbar.config(command=self.log.yview)

        # Set up tags for color coding various outputs in the main Text box
        self.txt.tag_configure("job_completed", foreground="#59aeff")
        self.txt.tag_configure("job_pending", foreground="#fdbf2c")
        self.txt.tag_configure("job_running", foreground="#34ffcc")
        self.txt.tag_configure("job_timeout", foreground="#FF0000")
        self.txt.tag_configure("job_cancelled", foreground="#e52de5")
        self.txt.tag_configure("about_page", font=self.parent.about_font)
        self.txt.tag_configure("special_user", foreground="#FF0000")
        self.txt.tag_configure("superspecial_user", foreground="#fdbf2c")
        self.txt.tag_raise(tk.SEL)

        # Bind keyboard shortcuts to the most important buttons
        self.parent.bind("<Control-o>", self.open_output)
        self.parent.bind("<Control-i>", self.open_input)
        self.parent.bind("<Control-g>", self.geometry_convergence)
        self.parent.bind("<Control-q>", self.print_q)
        self.parent.bind("<Control-j>", self.get_jobhistory)
        self.parent.bind("<Control-c>", self.cpu_usage)
        self.parent.bind("<Control-v>", self.open_visualizer)
        self.parent.bind("<Control-s>", self.open_submitscript)
        self.parent.bind("<Control-x>", self.kill_job)
        self.parent.bind("<Control-X>", self.kill_all_jobs)
        self.parent.bind("<Control-p>", self.launch_preferences)
        self.parent.bind("<Control-l>", self.logout)

        # Bind shortcut for opening a textbox dialog for entering simple shell commands that
        # will be passed to the cluster
        self.parent.bind("<Shift-Return>", self.shellmulator)

        # Bind keyboard shortcuts for quickly switching between clusters, using number buttons
        # (The numbers correspond to the cluster ordering in Login)
        self.parent.bind("<Control-Key-1>", lambda event: self.switch_cluster("stallo", event))  # Stallo
        self.parent.bind("<Control-Key-2>", lambda event: self.switch_cluster("fram", event))  # Fram
        self.parent.bind("<Control-Key-3>", lambda event: self.switch_cluster("saga", event))  # Saga
        self.parent.bind("<Control-Key-4>", lambda event: self.switch_cluster("betzy", event))  # Betzy

    def shellmulator(self, *args):
        # Dangerous to use certain commands remotely, so we forbid them
        # (not perfect, but it adds a slight safeguard against thoughtless commands
        forbidden_commands = ["rm ", "mv ", "mkdir ", "cp ", "rmdir "]

        def send_command(widget):
            cmd = entry.get()
            if any([cmd.startswith(c) for c in forbidden_commands]):
                MSG = """
                 mmmmmm  mmmm  mmmmm  mmmmm  mmmmm  mmmm   mmmm   mmmmmm mm   m
                 #      m"  "m #   "# #    #   #    #   "m #   "m #      #"m  #
                 #mmmmm #    # #mmmm" #mmmm"   #    #    # #    # #mmmmm # #m #
                 #      #    # #   "m #    #   #    #    # #    # #      #  # #
                 #       #mm#  #    " #mmmm" mm#mm  #mmm"  #mmm"  #mmmmm #   ##
                """
                self.txt.delete("1.0", tk.END)
                self.txt.insert(tk.END, MSG)
                widget.destroy()
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
            if stderr.read():
                error = stderr.read().decode("ascii")
                self.log_update(f"Error!")
                self.log_update(error)
            else:
                self.txt.delete(1.0, tk.END)
                self.txt.insert(tk.END, f"$ {cmd}\n")
                self.txt.insert(tk.END, stdout.read().decode("ascii"))

                widget.destroy()

        t = tk.Toplevel(self)
        t.bind("<Return>", lambda event: send_command(t))

        f = tk.Frame(t)
        f.grid(row=0, column=0)
        entry = tk.Entry(f)
        entry.grid(row=0, column=0)
        entry.focus()

    def switch_cluster(self, cluster, *args):
        self.destroy()
        self.parent.login_window.authorize(cluster)

    def logout(self, *args):
        """
        Close ssh connection and show the Login window.

        :param args: event from keyboard shortcut
        :return:
        """
        self.ssh_client.close()
        self.parent.show_login()

    def update_filter_mode(self, *args):
        self.parent.filter_mode.set(next(self.filter_mode_gen))
        self.label_filter["text"] = "Filter in ALL mode:" if self.parent.filter_mode.get() == 0 else "Filter in ANY mode:"

    def monitor_selected_text(self):
        """
        Run in the background, update label each time a valid integer is selected.
        :return:
        """
        s_old = self.selected_text.get()
        s_new = self.select_text()
        try:
            int(s_new)
            if s_new != s_old:
                self.selected_text.set(s_new)
                self.label_selected_text["text"] = f"Last selected job: {s_new}"

                outputfile = self.locate_output_file(s_new)
                self.output_last_update.set(self.get_last_update(outputfile))
        except (ValueError, TypeError):
            pass

        self.master.after(300, self.monitor_selected_text)

    def launch_preferences(self, *args):
        """
        Make instance of Preferences.
        :param args: Event from keyboard combinations
        :return:
        """
        return Preferences(self)

    def get_last_update(self, f):
        cmd = f"ls -ltr {f}"
        _, stdout, _ = self.ssh_client.exec_command(cmd)
        return stdout.read().decode("ascii").split()[5:8]

    def show_user_manual(self):
        self.current_file.set("")
        self.current_file.set("")
        with requests.session() as s:
            readme = s.get(self.url_readme).content.decode('utf-8')

        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        for line in readme:
            self.txt.insert(tk.END, line)

    def apply_settings(self):
        # Update the start time options
        self.job_starttime_options = [datetime.now().date() - timedelta(days=i) for i in range(self.master.job_history_length.get())]

        # Update all widgets by re-placing them
        self.place_widgets()

    def show_about_page(self):
        about = f"""\n
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    {self.parent.name} - A simple Graphical User Interface for the SLURM queuing system
                (only tested on Stallo and Fram)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Author: Anders Brakestad
            PhD Candidate at UiT The Arctic University of Norway
            anders.m.brakestad@uit.no
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Please report bugs here: https://github.com/Andersmb/QueueGui/issues
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    User Manual: https://github.com/Andersmb/QueueGui
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Keyboard shortcuts:
    Ctrl-q      Get queue
    Ctrl-c      Get CPU usage
    Ctrl-p      Open Preferences
    Ctrl-j      Get job history
    Ctrl-x      Kill selected job
    Ctrl-X      Kill all jobs
    Ctrl-o      Open output file
    Ctrl-i      Open input file
    Ctrl-g      Geometry convergence
    Ctrl-v      Open visualizer
    Ctrl-s      Open job script
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """
        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        self.txt.insert(tk.END, about)
        self.txt.tag_add("about_page", 1.0, tk.END)

    def monitor_q(self, *args):
        """
        Monitor the number of pending and running jobs. If check button is selected,
        then print queue.
        :param args: Event from Check box
        :return:
        """
        cmd = f"squeue -u {self.parent.user.get()} -o '%.20T'"
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        q = stdout.readlines()
        status = map(lambda x: x.strip(), q[1:])

        running, pending = 0, 0
        for s in status:
            if s == "RUNNING":
                running += 1
            elif s == "PENDING":
                pending += 1

        if self.do_queue_monitoring.get():
            self.print_q()

        self.label_monitor_q["text"] = f"Running: {running}\nPending: {pending}"
        self.master.after(self.parent.queue_monitor_update_frequency.get(), self.monitor_q)

    def print_q(self, *args):
        """
        Print queue to main text box
        :param args: Event from keyboard combination
        :return:
        """
        self.current_file.set("")
        self.user.set(self.entry_user.get())
        self.status.set(self.status_options[self.status.get()])

        if self.user.get().strip() == "":
            self.log_update("No user specified.")
            # now make sure the current status shown in the drop down menu corresponds to the same status used for the last job history command
            for stat, opt in self.status_options.items():
                if self.status.get() == opt:
                    self.status.set(stat)
                    break
            return

        # First determine the longest job name and pid length so that we can
        # adjust the squeue command to fit all job names
        cmd = "squeue -t {} -u {} -o '%.20i %.300j'".format(self.status.get(), self.user.get())
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        q = stdout.readlines()

        namelengths, pidlengths = [], []
        for line in q:
            pidlengths.append(len(line.split()[0].strip()))
            namelengths.append(len(line.split()[1].strip()))
        maxname = max(namelengths)
        maxpid = max(pidlengths)

        # Now get the actual queue that we want, and color code based on status
        if self.user.get() == "all":
            cmd = "squeue -t {} -S i -o '%.40j %.{}i %.9P %.8T %.8u %.10M %.10l %.6D %R'".format(self.status.get(),
                                                                                                 maxpid + 1)
        else:
            cmd = "squeue -u {} -t {} -S i -o '%.{}j %.{}i %.9P %.8T %.8u %.10M %.10l %.6D %R'".format(self.user.get(),
                                                                                                       self.status.get(),
                                                                                                       maxname + 1,
                                                                                                       maxpid + 1)

        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        q = stdout.readlines()

        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        for i, job in enumerate(q):
            self.txt.insert(tk.END, job)

            if "RUNN" in job.split()[3]:
                self.txt.tag_add("job_running", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
            elif "PEND" in job.split()[3]:
                self.txt.tag_add("job_pending", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
            elif "TIME" in job.split()[3]:
                self.txt.tag_add("job_timeout", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
            elif "COMPL" in job.split()[3]:
                self.txt.tag_add("job_completed", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
            elif "CANCEL" in job.split()[3]:
                self.txt.tag_add("job_cancelled", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))

        # now make sure the current status shown in the drop down menu corresponds to the same status used for the last job history command
        for stat, opt in self.status_options.items():
            if self.status.get() == opt:
                self.status.set(stat)
                break

    def get_jobhistory(self, *args):
        """
        Print user job history in main Text box.
        :param args: Event from keyboard combination
        :return:
        """
        self.user.set(self.entry_user.get())
        self.status.set(self.status_options[self.status.get()])
        self.jobhisfilter.set(self.entry_filter.get())

        self.log_update("Showing job history for {} starting from {}".format(self.user.get(), self.job_starttime.get()))

        # obtain the length of the job with the longest name
        cmd = "sacct -u {} --format='JobName%300,JobID%40' --starttime {}".format(self.user.get(),
                                                                                  self.job_starttime.get())
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        jobhis = stdout.readlines()

        namelengths = []
        pidlengths = []
        for job in jobhis[2:]:
            namelengths.append(len(job.split()[0].strip()))
            if "proxy" not in job.split()[0] and ".batch" not in job.split()[1]:
                pidlengths.append(len(job.split()[1].strip()))

        if len(namelengths) == 0:
            self.log_update(
                "Job history is empty. Try selecting an earlier start time in the drop down menu. ErrorCode_hyx916")

            # now make sure the current status shown in the drop down menu corresponds
            # to the same status used for the last job history command
            for stat, opt in self.status_options.items():
                if self.status.get() == opt:
                    self.status.set(stat)
                break
            return "ErrorCode_hyx916"
        maxname = max(namelengths)
        maxpid = max(pidlengths)

        if self.user.get().strip() == "":
            self.log_update("No user selected. ErrorCode_hus28")
            return "ErrorCode_hus28"

        if self.status.get() == self.status_options["All Jobs"]:
            cmd = "sacct -u {} --starttime {} --format='Jobname%{},JobID%{},User,state%10,time,nnodes%3,CPUTime,elapsed,Start,End'".format(
                self.user.get(), self.job_starttime.get(), maxname + 1, maxpid + 1)
        else:
            cmd = "sacct -u {} -s {} --starttime {} --format='Jobname%{},JobID%{},User,state%10,time,nnodes%3,CPUTime,elapsed,Start,End'".format(
                self.user.get(), self.status.get(), self.job_starttime.get(), maxname + 1, maxpid + 1)

        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        jh = stdout.readlines()

        # now get rid of useless lines in the history
        history = [jh[0]]  # start with the header present in the list
        for line in jh:
            try:
                int(line.split()[1])
                history.append(line)
            except ValueError:
                if "." in line.split()[1]:
                    continue
                elif "proxy" in line.split()[0]:
                    continue
                elif "batch" in line.split()[0]:
                    continue
                else:
                    history.append(line)

        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)

        # make sure the header will be printed regardless  of filter options
        self.txt.insert(tk.END, history[0])

        for i, line in enumerate(history[2:]):
            # if entry filter is empty
            if self.jobhisfilter.get().strip() == "":
                self.txt.insert(tk.END, line)
            # if filter is to be applied
            else:
                for f in self.jobhisfilter.get().strip().split():
                    if f in line:
                        self.txt.insert(tk.END, line)

        for i, line in enumerate(self.txt.get(1.0, tk.END).splitlines()):
            try:
                if "RUNN" in line.split()[3]:
                    self.txt.tag_add("job_running", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
                elif "PENDI" in line.split()[3]:
                    self.txt.tag_add("job_pending", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
                elif "TIMEO" in line.split()[3]:
                    self.txt.tag_add("job_timeout", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
                elif "COMPLE" in line.split()[3]:
                    self.txt.tag_add("job_completed", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
                elif "CANCEL" in line.split()[3]:
                    self.txt.tag_add("job_cancelled", "{}.0".format(i + 1), "{}.{}".format(i + 1, tk.END))
            except IndexError:
                continue

        # now make sure the current status shown in the drop down menu corresponds
        # to the same status used for the last job history command
        for stat, opt in self.status_options.items():
            if self.status.get() == opt:
                self.status.set(stat)
                break

    def download_file(self, f):
        """
        Download the file to the temporary directory
        :param f: str, path to file to download
        :return: str, path to downloaded file
        """
        destination = os.path.join(self.parent.tmp, helpers.remote_stem(f))
        self.sftp_client.get(f, destination)

        return destination

    def geometry_convergence(self, *args):
        self.parent.debug(f"INSPECTING GEOMETRY CONVERGENCE", header=True)
        pid = self.selected_text.get()
        outputfile = self.locate_output_file(pid)
        destination = os.path.join(self.master.tmp, os.path.basename(outputfile))

        self.sftp_client.get(outputfile, destination)

        G, O, M = self.determine_job_software(destination)

        if M:
            self.parent.debug(f"...MRChem job detected. Geometry convergence not supported.")
            self.log_update("Geometry convergence not supported by MRChem jobs.")

        # Collect data to be plotted
        if G:
            self.parent.debug("...Gaussian output file detected")
            output = GaussianOut(destination)
        elif O:
            self.parent.debug("...ORCA output file detected")
            output = OrcaOut(destination)
        else:
            self.parent.debug("...Output file not recognized. Inspect code!")
            self.log_update("Output file not recognized. Inspect code!")
            return

        energies = output.scf_energy()
        energies_relative = [(e - energies[0]) * 627.509 for e in energies]
        energies_delta = [abs(energies[i] - energies[i-1]) for i, e in enumerate(energies[1:])]
        no_scf_iter = output.no_scfcycles()
        maxforce = output.maxforce()
        rmsforce = output.rmsforce()
        maxstep = output.maxstep()
        rmsstep = output.rmsstep()

        tol_maxforce = output.tol_maxforce()
        tol_rmsforce = output.tol_rmsforce()
        tol_maxstep = output.tol_maxstep()
        tol_rmsstep = output.tol_rmsstep()

        xs_scf = [i for i in range(1, len(no_scf_iter) + 1)]

        # Set up figure
        FS = 14
        fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(10, 5), dpi=100)

        axes[0, 1].set_yscale("log")
        axes[0, 2].set_yscale("log")
        axes[1, 2].set_yscale("log")

        axes[0, 0].set_title("No. SCF iter")
        axes[0, 1].set_title("Forces (au)")
        axes[0, 2].set_title("Step (au)")
        axes[1, 0].set_title("Absolute Energy (au)")
        axes[1, 1].set_title("Relative Energy (kcal/mol)")
        axes[1, 2].set_title("Energy change (au)")

        for row in axes:
            for ax in row:
                ax.tick_params("both", labelsize=FS)
                ax.grid(True)

        axes[0, 0].bar(xs_scf, no_scf_iter, color="Skyblue")

        axes[0, 1].plot(maxforce, lw=2, color="red")
        axes[0, 1].plot(rmsforce, lw=2, color="blue")
        axes[0, 1].plot([tol_maxforce for _ in range(len(maxforce))], ls="--", color="red")
        axes[0, 1].plot([tol_rmsforce for _ in range(len(rmsforce))], ls="--", color="blue")

        axes[0, 2].plot(maxstep, lw=2, color="red")
        axes[0, 2].plot(rmsstep, lw=2, color="blue")
        axes[0, 2].plot([tol_maxstep for _ in range(len(maxstep))], ls="--", color="red")
        axes[0, 2].plot([tol_rmsstep for _ in range(len(rmsstep))], ls="--", color="blue")

        axes[1, 0].plot(energies, lw=2, color="black")
        axes[1, 1].plot(energies_relative, lw=2, color="black")
        axes[1, 2].plot(energies_delta, lw=2, color="black")
        if O:
            tol_echange = output.scf_convergence_tol_e()
            axes[1, 2].plot([tol_echange for _ in range(len(energies_delta))], ls="--", color="black")

        plt.tight_layout()

        return plt.show()

    def scf_convergence(self, *args):
        self.log_update("Not implemented")

    def cpu_usage(self, *args):
        """
        Count the number of running and pending CPUS for all users, and display
        in a table.
        :param args: event from keyboard combination
        :return:
        """
        """
        Count the number of running and pending CPUS for all users, and display
        in a table.
        :return:
        """
        self.current_file.set("")
        cmd = "squeue -o '%u %C %t'"
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        q = stdout.readlines()

        cpus_total = self.parent.cluster_data[self.master.host.get()]["number_of_cpus"]

        # Get jobs in queue
        jobs_all = [line.split() for line in q]
        jobs_running = [job for job in jobs_all if job[-1] == "R"]
        jobs_pending = [job for job in jobs_all if job[-1] == "PD"]

        # Initialize list to contain the users from all jobs
        users = sorted(set([job[0] for job in jobs_all]))

        # Initialize a dict in which the sum of all CPUs will be accumulated
        cpu_running = {user: 0 for user in users}
        cpu_pending = {user: 0 for user in users}

        # perform the sum for running cpus
        for job in jobs_running:
            for user in cpu_running.keys():
                if user in job:
                    cpu_running[user] += int(job[1])
        # and for pending cpus
        for job in jobs_pending:
            for user in cpu_running.keys():
                if user in job:
                    cpu_pending[user] += int(job[1])

        # Zip list of users, list of running cpus, and list of pending cpus.
        # Then sort based on list of running cpus.
        zipped = sorted(
            zip(cpu_running.keys(), [c for user, c in cpu_running.items()], [c for user, c in cpu_pending.items()]),
            key=lambda x: x[1], reverse=True)

        # Unzip
        user, cpu_running, cpu_pending = zip(*zipped)

        # get ratio of running cpus to cluster's total to 4 digits
        oftotal = [str(float(i) / cpus_total * 100)[:5] for i in cpu_running]

        # Get the users to highlight
        user_special = self.parent.cpu_usage_highlight_users.get().split()

        # Now insert data
        # In order to align the columns, we find the longes names in each column
        maxlen = (max(len(x) for x in user),
                  max(len(str(x)) for x in cpu_running),
                  max(len(str(x)) for x in oftotal),
                  max(len(str(x)) for x in cpu_pending))

        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        self.txt.insert(tk.END, "-"*(18 + maxlen[0] - 4 + maxlen[1] - 3 + maxlen[2] - 1) + "\n")
        self.txt.insert(tk.END, f"User {' '*(maxlen[0] - 4)} Run {' '*(maxlen[1] - 3)} % {' '*(maxlen[2] - 1)} Pend\n")
        self.txt.insert(tk.END, "-"*(18 + maxlen[0] - 4 + maxlen[1] - 3 + maxlen[2] - 1) + "\n")

        for i, u in enumerate(user):
            self.txt.insert(tk.END, "{} {} {} {} {} {} {}\n".format(u,
                                                                    (maxlen[0] - len(user[i])) * " ",
                                                                    cpu_running[i],
                                                                    (maxlen[1] - len(str(cpu_running[i]))) * " ",
                                                                    oftotal[i],
                                                                    (maxlen[2] - len(oftotal[i])) * " ",
                                                                    cpu_pending[i]))
            if u in user_special:  # make special users red
                self.txt.tag_add("special_user", "{}.0".format(i + 4), "{}.{}".format(i + 4, tk.END))
                if u == user_special[0]:  # make first special user green
                    self.txt.tag_add("superspecial_user", "{}.0".format(i + 4), "{}.{}".format(i + 4, tk.END))

        self.txt.insert(tk.END, "-"*(18 + maxlen[0] - 4 + maxlen[1] - 3 + maxlen[2] - 1) + "\n")

        # convert back to floats for the summation
        oftotal = [float(t) for t in oftotal]
        self.txt.insert(tk.END, "SUM: {} {} {} {} {} {}\n".format((maxlen[0] - 4) * " ",
                                                                  str(sum(cpu_running))[:5],
                                                                  (maxlen[1] - len(str(sum(cpu_running)))) * " ",
                                                                  str(sum(oftotal))[:5],
                                                                  (maxlen[2] - len(str(sum(oftotal)))) * " ",
                                                                  str(sum(cpu_pending))[:5]))
        self.txt.insert(tk.END, "-"*(18 + maxlen[0] - 4 + maxlen[1] - 3 + maxlen[2] - 1) + "\n")

    def locate_output_file(self, pid):
        """
        Try to locate the output file in the scratch area. It is assumed that the scratch directory
        ends with the Job ID
        :param pid: Job ID for job
        :return: Path, path to identified output file
        """
        self.user.set(self.entry_user.get())
        scratch_location = self.get_scratch()
        jobname = self.get_jobname(pid)

        self.parent.debug("----------------------------------------")
        self.parent.debug("Locating output file")
        self.parent.debug(f"User: {self.user.get()}")
        self.parent.debug(f"Scratch location: {scratch_location}")

        try:
            all_scratch_dirs = self.sftp_client.listdir(scratch_location)
            self.parent.debug(f"{len(all_scratch_dirs)} scratch directories will be searched.")
        except IOError:
            self.parent.debug(f"This scratch location was not found: {scratch_location}")
            self.log_update(f"Scratch location '{scratch_location}' not found. ErrorCode_jut81")
            return "ErrorCode_jut81"

        self.parent.debug(f"Searching for scratch directories that ends with pid={pid}:")
        for scratch in all_scratch_dirs:
            if scratch.endswith(pid):
                self.parent.debug(f"Match found: {scratch}")
                scratchdir = helpers.remote_join(scratch_location, scratch)
                break
        else:
            self.parent.debug(f"No scratch directories ended with pid={pid}")
            self.log_update(f"Scratch directory for job {pid} not found. ErrorCode_hoq998")
            return "ErrorCode_hoq998"

        # Now loop over extensions and look for a hit on an outputfile
        # Warning: if one of the user set extensions is used as something else than an output file
        # then you may get a false positive here, and the incorrect file is returned.
        # Be careful with what type of extensions you use.
        outputfile_ext = self.parent.current_settings["extensions"]["output"].split()
        self.parent.debug(f"Searching for output files with these extensions: {', '.join(outputfile_ext)}")

        for ext in outputfile_ext:
            outputfile = helpers.remote_join(scratchdir, jobname+ext)
            self.parent.debug(f"Output file to attempt: {outputfile}")

            try:
                self.sftp_client.stat(outputfile)
                self.parent.debug(f"Found output file: {outputfile}")
                return outputfile
            except IOError:
                self.parent.debug(f"Did not find {outputfile}")
                continue
        else:
            self.parent.debug(f"No output files found.")
            self.log_update(f"No output file was found using these extensions: {', '.join(outputfile_ext)}")
            self.log_update("ErrorCode_fov28")
            return "ErrorCode_fov28"

    def locate_input_file(self):
        self.user.set(self.entry_user.get())
        pid = self.selected_text.get()

        # Get input file from the submit directory
        jobname = self.get_jobname(pid)
        workdir = self.get_workdir(pid)

        self.parent.debug("----------------------------------------")
        self.parent.debug("Locating input file")
        self.parent.debug(f"Jobname: {jobname}")
        self.parent.debug(f"Work directory: {workdir}")

        # Determine the correct extension for the input file
        inputfile_ext = self.parent.current_settings["extensions"]["input"].split()
        self.parent.debug(f"Searching for input files with these extensions: {', '.join(inputfile_ext)}")

        for ext in inputfile_ext:
            inputfile = helpers.remote_join(workdir, jobname+ext)
            self.parent.debug(f"Input file attempt: {inputfile}")
            try:
                self.sftp_client.stat(inputfile)
                self.parent.debug(f"Found {inputfile}")
                return inputfile
            except:
                self.parent.debug(f"Did not find {inputfile}")
                continue

        self.log_update("Input file not found. ErrorCode_juq81")
        return "ErrorCode_juq81"

    def open_output(self, *args):
        self.current_file.set("")
        self.parent.debug(f"OPENING OUTPUT FILE", header=True)
        pid = self.selected_text.get()
        outputfile = self.locate_output_file(pid)

        # It is significantly faster to actually download the output file
        # and open it locally (especially if the file is large).
        self.log_update(f"Opening {outputfile}")
        destination = self.download_file(outputfile)

        with open(destination) as f:
            lines = f.readlines()

        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        for line in lines:
            self.txt.insert(tk.END, line)

        if self.parent.skip_end_output.get():
            self.txt.see("end")

    def open_visualizer(self, *args):
        self.parent.debug(f"OPENING OUTPUT IN VISUALIZER", header=True)
        pid = self.selected_text.get()
        outputfile = self.locate_output_file(pid)
        destination = os.path.join(self.master.tmp, os.path.basename(outputfile))

        self.sftp_client.get(outputfile, destination)

        G, O, M = self.determine_job_software(destination)

        if M:
            self.log_update("Not implemented for MRChem jobs.")
            return

        # Visualizer modes:
        # 0: simple path to executable
        # 1: shell script to be executed
        # 2: python script to be executed
        self.log_update("Visualizer mode: {}".format(self.master.visualizer_mode.get()))

        if self.master.visualizer_mode.get() == 0:
            cmd = [self.master.path_to_visualizer.get(), destination]

        elif self.master.visualizer_mode.get() == 1:
            cmd = ["open", "-a", self.master.path_to_visualizer.get(), destination]
            self.log_update("hit on mode 1")

        elif self.master.visualizer_mode.get() == 2:
            return self.log_update("Not implemented yet!")

        self.log_update(" ".join(cmd))
        subprocess.call(cmd)

    def mrchem_plot_convergence(self):
        pid = self.selected_text.get()
        self.jobhisfilter.set(self.entry_filter.get())
        self.user.set(self.entry_user.get())

        outputfile = self.locate_output_file(pid)
        destination = os.path.join(self.parent.tmp, os.path.basename(outputfile))
        self.sftp_client.get(outputfile, destination)
        return MrchemOut(destination).plot_scf_energy(title=pid)

    def orca_scf_convergence(self):
        pid = self.selected_text.get()
        outputfile = self.locate_output_file(pid)
        destination = os.path.join(self.master.temp_dir, os.path.basename(outputfile))

        self.sftp_client.get(outputfile, destination)

        data = OrcaOut(destination).scf_convergences()
        self.txt.delete(1.0, tk.END)
        for cycle in data:
            for scf in cycle:
                self.txt.insert(tk.END, scf+"\n")
            self.txt.insert(tk.END, "\n")

    def get_scratch(self):
        if self.master.host.get() == "stallo":
            return helpers.remote_join(self.parent.current_settings["paths"]["scratch_stallo"], self.user.get())
        elif self.master.host.get() == "fram":
            return self.parent.current_settings["paths"]["scratch_fram"]
        elif self.master.host.get() == "saga":
            return self.parent.current_settings["paths"]["scratch_saga"]

        self.log_update("Scratch not found. ErrorCode_lib73")
        return "ErrorCode_lib73"

    def open_error(self):
        self.parent.debug("OPENING ERROR FILE", header=True)
        errorfile = self.locate_input_file().split(".")[0]+".err"
        if "ErrorCode_" in errorfile:
            return errorfile

        with self.sftp_client.open(errorfile) as f:
            lines = f.readlines()

        self.log_update(f"Opening {errorfile}")
        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)

        for line in lines:
            self.txt.insert(tk.END, line)

    def open_input(self, *args):
        self.parent.debug(f"OPENING INPUT FILE", header=True)
        inputfile = self.locate_input_file()
        self.current_file.set(inputfile)
        if "ErrorCode_" in inputfile:
            return inputfile

        with self.sftp_client.open(inputfile, "r") as f:
            lines = f.readlines()

        self.log_update("Opening {}".format(inputfile))
        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)

        for line in lines:
            self.txt.insert(tk.END, line)

    def open_submitscript(self, *args):
        self.user.set(self.entry_user.get())
        pid = self.selected_text.get()

        jobname = self.get_jobname(pid)
        workdir = self.get_workdir(pid)

        # Locate the submit script file. Common extensions are "job" and "launch"
        slurmscript_extensions = [".job", ".launch"]
        for ext in slurmscript_extensions:
            jobfile = helpers.remote_join(workdir, jobname+ext)
            self.current_file.set(jobfile)
            try:
                with self.sftp_client.open(jobfile) as f:
                    content = f.read()
                    self.log_update("Opening {}".format(jobfile))
                    self.txt.configure(state=tk.NORMAL)
                    self.txt.delete(1.0, tk.END)
                    self.txt.insert(1.0, content)
                    break
            except IOError:
                if ext == slurmscript_extensions[-1]:
                    self.log_update("Submit script file not found. ErrorCode_juq91")
                    return "ErrorCode_juq91"

    def open_jobinfo(self):
        self.current_file.set("")
        pid = self.selected_text.get()
        jobinfo = self.get_jobinfo(pid)

        self.log_update("scontrol show jobid {}".format(pid))
        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        self.txt.insert(tk.END, jobinfo)

    def filter_textbox(self, *args):
        self.current_file.set("")
        self.jobhisfilter.set(self.entry_filter.get())
        if self.jobhisfilter.get().strip() == "":
            return self.log_update("The filter is empty")

        # Collect whatever is currently in the textbox, and loop over it to filter
        current = self.txt.get(1.0, tk.END).splitlines()
        _filter = self.entry_filter.get().split()

        # Filter based on the current filter mode
        # This can be set by the user by clicking on the
        # filter label in MainWindow
        if self.parent.filter_mode.get() == 0:
            new = [line for line in current if all([f in line for f in _filter])]
        else:
            new = [line for line in current if any([f in line for f in _filter])]

        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)

        for i, line in enumerate(new):
            self.txt.insert(tk.END, line+"\n")
            try:
                if "RUNN" in line.split()[3]:
                    self.txt.tag_add("job_running", "{}.0".format(i+1), "{}.{}".format(i+1, tk.END))
                elif "PEND" in line.split()[3]:
                    self.txt.tag_add("job_pending", "{}.0".format(i+1), "{}.{}".format(i+1, tk.END))
                elif "TIME" in line.split()[3]:
                    self.txt.tag_add("job_timeout", "{}.0".format(i+1), "{}.{}".format(i+1, tk.END))
                elif "COMPL" in line.split()[3]:
                    self.txt.tag_add("job_completed", "{}.0".format(i+1), "{}.{}".format(i+1, tk.END))
                elif "CANCEL" in line.split()[3]:
                    self.txt.tag_add("job_cancelled", "{}.0".format(i+1), "{}.{}".format(i+1, tk.END))
            except IndexError:
                continue

    def kill_job(self, *args):
        pid = self.selected_text.get()
        cmd = "scancel {}".format(pid)

        result = messagebox.askyesno(self.parent.name, f"Are you sure you want to kill JobID {pid}?")

        if result is True:
            self.log_update(cmd)
            self.ssh_client.exec_command(cmd)
            self.print_q()
        else:
            return

    def kill_all_jobs(self, *args):
        self.user.set(self.entry_user.get())
        cmd = "scancel -u {}".format(self.user.get())

        result = messagebox.askyesno(self.parent.name, "Are you sure you want to kill all jobs for user {}".format(self.user.get()))
        if result:
            result2 = messagebox.askyesno(self.parent.name, "Are you mad?")

        if result and result2:
            self.log_update(cmd)
            self.ssh_client.exec_command(cmd)
        else:
            return

    def kill_range(self):
        """
        Kill all jobs with IDs inspecified range
        :return:
        """
        start = simpledialog.askinteger(self.parent.name, "Give start of range:")
        stop = simpledialog.askinteger(self.parent.name, "Give end of range:")

        if messagebox.askyesno(self.parent.name, f"Are you sure you want to kill jobs in range {start} to {stop}?"):
            self.log_update(f"Killing all jobs in range {start} to {stop}")
            for job in range(start, stop+1):
                self.ssh_client.exec_command(f"scancel {job}")
        else:
            self.log_update("Kill aborted!")

    def launch_convertme(self):
        return ConvertMe(self)

    def launch_toolbox(self):
        return ToolBox(self)

    def select_text(self):
        try:
            return self.txt.get(tk.SEL_FIRST, tk.SEL_LAST)
        except:
            return "ErrorCode_pol98"

    def get_jobname(self, pid):
        self.parent.debug(header=True)
        self.parent.debug(f"Searching for job name for pid={pid}")

        cmd = "scontrol show jobid {}".format(pid)
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        info = stdout.read().decode('ascii').splitlines()

        for line in info:
            if line.strip().startswith("StdOut=/"):
                jobname = os.path.splitext(os.path.basename(line.split("=", 1)[1]))[0]
                self.parent.debug(f"Jobname found: {jobname}")
                return jobname

    def get_workdir(self, pid):
        self.parent.debug(s="Searching for work directory", header=True)
        cmd = "scontrol show jobid {}".format(pid)
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        output = stdout.read().decode('ascii').splitlines()

        for line in output:
            if line.strip().startswith("WorkDir"):
                workdir = line.split("=", 1)[1]
                self.parent.debug(f"Work directory found: {workdir}")
                return workdir
        else:
            self.log_update("WorkDir not found. ErrorCode_nut62")
            return "ErrorCode_nut62"

    def get_jobstatus(self, pid):
        cmd = f"scontrol show jobid {pid}"
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        output = stdout.read().decode('ascii').splitlines()

        status = None
        for line in output:
            for el in line.split():
                if "JobState" in el:
                    status = el.split("=")[1]
        if status == None:
            self.log_update("Job Status not found. ErrorCode_mel34")
            return "ErrorCode_mel34"
        else:
            return status

    def log_update(self, msg):
        """
        Print message in log window.
        :param msg:
        :return:
        """
        time = str(datetime.now().time()).split(".")[0]
        logmsg = f"[{time}] {msg}\n"
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, logmsg)
        self.log.see("end")
        return

    def get_jobinfo(self, pid):
        cmd = "scontrol show jobid {}".format(pid)
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        return stdout.read().decode('ascii')

    def determine_job_software(self, outputfile):
        """
        This method determines whether the given output file was generated by Gaussian, ORCA, or MRChem.

        :param outputfile: str
        :return: tuple

        (gaussian, orca, mrchem)
        """
        with open(outputfile) as f:
            lines = f.readlines()[:100]

        for line in lines:
            # Test if Gaussian
            if "Entering Gaussian System" in line.strip():
                #self.log_update("Gaussian file detected")
                self.parent.debug("Gaussian output detected")
                return True, False, False
            # Test if ORCA
            elif "Directorship: Frank Neese" in line.strip():
                #self.log_update("ORCA file detected")
                self.parent.debug("ORCA output detected")
                return False, True, False
            # Test if MRChem
            elif "Stig Rune Jensen" in line:
                #self.log_update("MRChem file detected")
                self.parent.debug("MRChem output detected")
                return False, False, True
        else:
            self.log_update("Source of output not found. ErrorCode kux81")
            return "ErrorCode kux81"

    def update_job(self, event):
        return UpdateJob(self, self.selected_text.get(), self.parent.user.get())

    def backup_scratch_files(self):
        """Copy all important files back to the workdir. This can be done if
        there is danger of the job not completing within the timelimit."""
        self.parent.debug("INITIATING BACKUP OF SCRATCH FILES", header=True)
        pid = self.selected_text.get()

        outputfile = self.locate_output_file(pid)
        destination = os.path.join(self.master.tmp, os.path.basename(outputfile))
        self.sftp_client.get(outputfile, destination)

        G, O, M = self.determine_job_software(destination)

        scratch = os.path.dirname(outputfile)
        jobname = self.get_jobname(pid)
        backup_dir = os.path.join(self.get_workdir(pid), f"{jobname}_backup")
        self.log_update(f"Copying files to {backup_dir}")

        # Test if backup dir exists, overwrite if it does
        if helpers.is_remotedir(self.ssh_client, backup_dir):
            self.ssh_client.exec_command(f"rm -r {backup_dir}")
            self.ssh_client.exec_command(f"mkdir {backup_dir}")
            self.parent.debug("Backup dir existed => overwrite")
        else:
            self.ssh_client.exec_command(f"mkdir {backup_dir}")
            self.parent.debug("Backup dir did not exist.")

        if G:
            save_files = [".out", ".chk"]
            self.parent.debug("Copying back Gaussian files")
            for ext in save_files:
                self.parent.debug(f"-> {ext} file")
                src = os.path.join(scratch, jobname+ext)
                cmd = f"cp {src} {backup_dir}"
                stdin, stdout, stderr = self.ssh_client.exec_command(cmd)

                if stderr:
                    self.log_update(f"{ext}: stderr: {stderr.read().decode('ascii')}")
                    self.parent.debug(f"-> stderr: {stderr.read().decode('ascii')}")

        elif O:
            save_files = [".out", ".gbw", ".xyz"]
            self.parent.debug("Copying back ORCA files")
            for ext in save_files:
                self.parent.debug(f"-> {ext} file")
                src = os.path.join(scratch, jobname + ext)
                cmd = f"cp {src} {backup_dir}"
                stdin, stdout, stderr = self.ssh_client.exec_command(cmd)

                if stderr.read().decode("ascii").strip():
                    self.log_update(f"{ext}: stderr: {stderr.read().decode('ascii')}")
                    self.parent.debug(f"-> stderr: {stderr.read().decode('ascii')}")
        else:
            save_files = [".out"]
            self.parent.debug("Copying back MRChem files")
            for ext in save_files:
                self.parent.debug(f"-> {ext} file")
                src = os.path.join(scratch, jobname + ext)
                cmd = f"cp {src} {backup_dir}"
                stdin, stdout, stderr = self.ssh_client.exec_command(cmd)

                if stderr:
                    self.log_update(f"{ext}: stderr: {stderr.read().decode('ascii')}")
                    self.parent.debug(f"-> stderr: {stderr.read().decode('ascii')}")

    def update_current_file(self):
        if messagebox.askyesno("Update file contents",
                               f"Do you want to update the contents of the current file? This cannot be undone! Current file: {self.current_file.get()}"):
            contents = self.txt.get("1.0", tk.END).splitlines()
            cmds = [f"echo '{line}' >> {self.current_file.get()}" for line in contents]
            rm = f"rm {self.current_file.get()}"

            self.ssh_client.exec_command(rm)
            for cmd in cmds:
                self.ssh_client.exec_command(cmd)

            self.log_update(f"Updated {self.current_file.get()}")

    def store_mrchem_checkpoint(self):
        pid = self.selected_text.get()
        jobname = self.get_jobname(pid)
        scratch = os.path.dirname(self.locate_output_file(pid))
        workdir = self.get_workdir(pid)
        source = os.path.join(scratch, "checkpoint")
        destination = f"/cluster/work/users/ambr/MWcheckpoints_{pid}"
        pointer = os.path.join(workdir, jobname+".checkpoint")

        cmd_dush = f"du -sh {source}"
        cmd_touch = f"touch {pointer}; echo {destination} > {pointer}"
        cmd_mkdir = f"mkdir -p {destination}"
        cmd_copy = f"cp {source}/* {destination}/"

        stdin, stdout, stderr = self.ssh_client.exec_command(cmd_dush)
        dush = stdout.read().decode("ascii").strip()
        self.log_update(f"Orbital size: {dush}")

        self.log_update("Touching checkpoint pointer:")
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd_touch)
        self.log_update(f"stderr: {stderr.read().decode('ascii').strip()}")

        self.log_update("Creating CHK directory")
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd_mkdir)
        self.log_update(f"stderr: {stderr.read().decode('ascii').strip()}")

        self.log_update("Copying orbital checkpoints:")
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd_copy)
        self.log_update(f"stderr: {stderr.read().decode('ascii').strip()}")
        self.log_update("Checkpointing done!")

        # Make OSX notification
        if "darwin" in self.parent.platform:
            cmd_msg = f"osascript -e 'display notification \"Copied orbitals ({dush})\" with title \"QG CHECKPOINTING\"'"
            os.system(cmd_msg)

        return

class UpdateJob(tk.Toplevel):
    def __init__(self, parent, pid, user):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.pid = pid
        self.user = user
        self.job = Job(self.parent.ssh_client, self.pid)

        self.account = tk.StringVar()
        self.account.set(self.job.get_info("Account"))

        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0)

        tk.Label(self.frame, text=f"Update Job Parameters for Job {self.pid}", font=self.parent.parent.main_font).grid(row=0, column=0)

        tk.Button(self.frame, text="Close", font=self.parent.parent.main_font,
                  command=self.destroy).grid(row=99, column=0, sticky=tk.W)
        tk.Button(self.frame, text="Update Job", font=self.parent.parent.main_font,
                  command=self.update).grid(row=98, column=0, sticky=tk.W)

        tk.Label(self.frame, text="Account", font=self.parent.parent.main_font).grid(row=1, column=0, sticky=tk.W)
        tk.Label(self.frame, text="Memory per node (MB)", font=self.parent.parent.main_font).grid(row=2, column=0, sticky=tk.W)
        tk.Label(self.frame, text="Time limit (d-hh:mm:ss)", font=self.parent.parent.main_font).grid(row=3, column=0, sticky=tk.W)
        tk.Label(self.frame, text="Number of nodes", font=self.parent.parent.main_font).grid(row=4, column=0, sticky=tk.W)

        self.optmenu_account = tk.OptionMenu(self.frame, self.account, *self.get_all_accounts())
        self.optmenu_account.config(font=self.parent.parent.main_font)
        self.optmenu_account["menu"].config(font=self.parent.parent.main_font)
        self.e_mem = tk.Entry(self.frame, width=10, font=self.parent.parent.main_font)
        self.e_time = tk.Entry(self.frame, width=10, font=self.parent.parent.main_font)
        self.e_node = tk.Entry(self.frame, width=10, font=self.parent.parent.main_font)
        self.optmenu_account.grid(row=1, column=1, sticky=tk.W)
        self.e_mem.grid(row=2, column=1, sticky=tk.W)
        self.e_time.grid(row=3, column=1, sticky=tk.W)
        self.e_node.grid(row=4, column=1, sticky=tk.W)

        self.e_mem.insert(0, self.job.get_info("MinMemoryNode"))
        self.e_time.insert(0, self.job.get_info("TimeLimit"))
        self.e_node.insert(0, self.job.get_info("Nodes"))

    def update(self):
        self.parent.log_update(f"Updating job {self.pid}")
        self.parent.parent.debug("Updating job parameters", header=True)

        cmds = [f"scontrol update jobid {self.pid} account {self.account.get()}",
                f"scontrol update jobid {self.pid} timelimit {self.e_time.get()}",
                f"scontrol update jobid {self.pid} numnodes {self.e_node.get()}",
                f"scontrol update jobid {self.pid} minmemorynode {self.e_mem.get()}"]

        for cmd in cmds:
            stdin, stdout, stderr = self.parent.ssh_client.exec_command(cmd)
            err = stderr.read().decode('ascii').strip()
            self.parent.log_update(f"...command: {cmd}")
            self.parent.log_update(f"...stderr: {err}")

            self.parent.parent.debug(f"...running command: {cmd}")
            self.parent.parent.debug(f"...stderr: {err}")

    def get_all_accounts(self):
        self.parent.parent.debug(f"Getting active accounts for user={self.user}", header=True)
        host = self.parent.parent.host.get()
        pattern = re.compile(r"[a-zA-Z]{2}[0-9]{4}k")  # This will match all accounts at uninett

        if host == "stallo":
            cmd = "/global/apps/gold/2.1.5.0/bin/cost"
            self.parent.parent.debug(f"...command to send: {cmd}")

            stdin, stdout, stderr = self.parent.ssh_client.exec_command(cmd)
            self.parent.parent.debug("...command sent to cluster")
            output = stdout.read().decode("ascii")

            self.parent.parent.debug(f"...RE pattern: {pattern}")

            accounts = set(pattern.findall(output))
            self.parent.parent.debug(f"...matched user accounts: {', '.join(accounts)}")
            return list(accounts)

        else:
            cmd = "/cluster/bin/cost"
            self.parent.parent.debug(f"Command to send: {cmd}")

            stdin, stdout, stderr = self.parent.ssh_client.exec_command(cmd)
            self.parent.parent.debug("...command sent to cluster")
            output = stdout.read().decode("ascii")
            print("output", output)

            self.parent.parent.debug(f"...RE pattern: {pattern}")

            accounts = set(pattern.findall(output))
            self.parent.parent.debug(f"...matched user accounts: {', '.join(accounts)}")
            return list(accounts)
