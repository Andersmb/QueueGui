import tkinter as tk
from tkinter import font
from tkinter import messagebox
import os
from copy import deepcopy
import tempfile
import shutil
import json
import requests

from mainwindow import MainWindow
from login import Login


class QueueGui(tk.Tk):
    """
    Main application file. Used for storing application-wide variables and settings.
    """
    def __init__(self):
        tk.Tk.__init__(self)
        self.name = "QueueGui3"

        # Define constants for conversions
        self.AU2ANG = 0.529177249
        self.ANG2AU = 1 / self.AU2ANG
        self.AU2KCAL = 627.509
        self.KCAL2AU = 1 / self.AU2KCAL

        # Define system variables and set defaults where relevant
        self.user = tk.StringVar()
        self.pwd = tk.StringVar()
        self.host = tk.StringVar()  # Coupled to OptionMenu in Login
        self.visualizer_mode = tk.IntVar()
        self.visualizer_mode.set(0)
        self.filter_mode = tk.IntVar()
        self.filter_mode.set(0)
        self.check_for_updates = tk.BooleanVar()
        self.check_for_updates.set(1)
        self.remote_version_file = "https://raw.githubusercontent.com/Andersmb/QueueGui/master/__VERSION__"
        self.cluster_data = {
            "stallo": {
                "hostname": "stallo.uit.no",
                "number_of_cpus": float(13796)
            },
            "fram": {
                "hostname": "fram.sigma2.no",
                "number_of_cpus": float(32256)
            },
            "saga": {
                "hostname": "saga.sigma2.no",
                "number_of_cpus": float(9824)
            }
        }

        # Define system variables that can be set by the user
        self.background_color = tk.StringVar()
        self.job_history_length = tk.IntVar()
        self.queue_monitor_update_frequency = tk.IntVar()
        self.cpu_usage_highlight_users = tk.StringVar()
        self.fontsize_main = tk.IntVar()
        self.fontsize_q = tk.IntVar()
        self.fontsize_log = tk.IntVar()
        self.fontfam_main = tk.StringVar()
        self.fontfam_q = tk.StringVar()
        self.fontfam_log = tk.StringVar()
        self.path_scratch_stallo = tk.StringVar()
        self.path_scratch_fram = tk.StringVar()
        self.path_scratch_saga = tk.StringVar()
        self.path_to_visualizer = tk.StringVar()
        self.path_to_settings_file = tk.StringVar()
        self.path_to_notes = tk.StringVar()
        self.extensions_inputfiles = tk.StringVar()
        self.extensions_outputfiles = tk.StringVar()

        # Define default settings
        self.default_settings = {
            "background_color": "#e8b251",
            "job_history_length": 14,
            "check_for_updates": "Yes" if self.check_for_updates.get() else "No",
            "queue_monitor_update_frequency": 4000,
            "cpu_usage_highlight_users": "",
            "visualizer_mode": self.visualizer_mode.get(),

            "fonts": {
                "main": {"size": 13, "family": "Chalkboard SE"},
                "q": {"size": 12, "family": "Courier"},
                "log": {"size": 10, "family": "Arial"}
            },
            "paths": {
                "scratch_stallo": "/global/work",
                "scratch_fram": "/cluster/work/jobs",
                "scratch_saga": "/cluster/work/jobs",
                "visualizer": "",
                "notes": os.path.join(os.path.expanduser("~"), ".QueueGui", "notes.txt"),
                "settings": os.path.join(os.path.expanduser("~"), ".QueueGui", "settings.json")
            },
            "extensions": {
                "input": ".inp .com",
                "output": ".out .log"
            }
        }

        # Set up a temporary directory for storing files
        self.tmp = tempfile.mkdtemp()
        print(f"Temporary files will be stored in:\n{self.tmp}")

        # Check for updates
        if self.check_for_updates.get():
            self.update_checker()

        # Initialize the login window
        self.startup = True  # Necessary since no window needs to be forgotten the first time
        self.login_window = Login(self)
        self.show_login()
        self.startup = False

        # Load settings and set system variables
        self.current_settings = self.load_settings()
        self.set_system_variables()
        self.set_fonts()

        # Check for settings file
        self.is_settings_file()

    def show_login(self):
        self.login_window.grid(row=0, column=0)
        if not self.startup:
            self.main_window.grid_forget()

    def show_main(self):
        self.main_window = MainWindow(self)
        self.login_window.grid_forget()
        self.main_window.grid(row=0, column=0)

    def load_settings(self):
        """
        Attempt to load the settings file from default path, and assign settings to variable.
        If no file is found, assign defaults to variable and create empty file.
        :return:
        """
        try:
            with open(self.default_settings["paths"]["settings"]) as f:
                return json.load(f)
        except IOError:
            print("Warning: No settings file found. Using defaults.")
            return deepcopy(self.default_settings)
        except json.decoder.JSONDecodeError:
            print("Empty settings file found. Using defaults.")
            return deepcopy((self.default_settings))

    def dump_settings(self):
        with open(self.path_to_settings_file.get(), "w") as f:
            json.dump(self.current_settings, f, indent=4)

    def is_settings_file(self):
        if not os.path.isfile(self.path_to_settings_file.get()):
            msg = f"""
                  No settings file found. You must create the following empty file in order to
                  be able to set your own settings:

            {     self.path_to_settings_file.get()}
            """
            messagebox.showinfo(self.name, msg)

    def set_system_variables(self):
        """
        Set all system variables stored in current_settings
        :return:
        """
        self.background_color.set(self.current_settings["background_color"])
        self.job_history_length.set(self.current_settings["job_history_length"])
        self.queue_monitor_update_frequency.set(self.current_settings["queue_monitor_update_frequency"])
        self.cpu_usage_highlight_users.set(self.current_settings["cpu_usage_highlight_users"])
        self.visualizer_mode.set(self.current_settings["visualizer_mode"])

        if self.current_settings["check_for_updates"] == "Yes":
            self.check_for_updates.set(True)
        else:
            self.check_for_updates.set(False)

        self.fontsize_main.set(self.current_settings["fonts"]["main"]["size"])
        self.fontsize_q.set(self.current_settings["fonts"]["q"]["size"])
        self.fontsize_log.set(self.current_settings["fonts"]["log"]["size"])
        self.fontfam_main.set(self.current_settings["fonts"]["main"]["family"])
        self.fontfam_q.set(self.current_settings["fonts"]["q"]["family"])
        self.fontfam_log.set(self.current_settings["fonts"]["log"]["family"])

        self.path_scratch_stallo.set(self.current_settings["paths"]["scratch_stallo"])
        self.path_scratch_fram.set(self.current_settings["paths"]["scratch_fram"])
        self.path_scratch_saga.set(self.current_settings["paths"]["scratch_saga"])
        self.path_to_visualizer.set(self.current_settings["paths"]["visualizer"])
        self.path_to_settings_file.set(self.current_settings["paths"]["settings"])
        self.path_to_notes.set(self.current_settings["paths"]["notes"])

        self.extensions_inputfiles.set(self.current_settings["extensions"]["input"])
        self.extensions_outputfiles.set(self.current_settings["extensions"]["output"])

    def update_checker(self):
        """
        Compare the __VERSION__ file in local dir with the __VERSION__ file github.

        Return if no update or IOError on local file
        Return if any exception on reading remote file

        If new update, show message box

        :return: None
        """
        try:
            with open("__VERSION__") as f:
                local_version = f.read()
        except IOError:
            return

        r = requests.get(self.remote_version_file)
        if r.status_code == requests.codes.ok:
            remote_version = r.content.decode("ascii").strip()

            if local_version != remote_version:
                msg = f"""
                Version of {self.name} available! 

                Your version: {local_version}
                New version:  {remote_version}

                Download the files on Github:

                https://github.com/Andersmb/QueueGui

                (Psst! You can turn off update notifications in the preferences)
                """
                messagebox.showinfo(self.title, msg)

    def set_fonts(self):
        """
        Define the fonts. This cannot be in __init__, since then MainWindow cannot communicate with
        this instance of QueueGui.
        :return:
        """
        self.main_font = font.Font(family=self.fontfam_main.get(), size=self.fontsize_main.get())
        self.queue_font = font.Font(family=self.fontfam_q.get(), size=self.fontsize_q.get())
        self.log_font = font.Font(family=self.fontfam_log.get(), size=self.fontsize_log.get())
        self.about_font = font.Font(family="Arial", size=16)



# Run application
if __name__ == "__main__":
    app = QueueGui()
    app.title(app.name)
    app.resizable(False, False)

    app.lift()
    app.attributes('-topmost', True)
    app.after_idle(app.attributes, '-topmost', False)

    app.mainloop()

    print(f"Removing temporary directory:\n{app.tmp}")
    shutil.rmtree(app.tmp)