import tkinter as tk
from tkinter import messagebox
from tkinter import font
from copy import deepcopy

from colorpicker import ColorPicker
from fontpicker import FontPicker


class Preferences(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.master = self.parent.master
        self.title("Preferences")
        self.preview = tk.IntVar()  # Used for applying settings without writing to file
        self.preview.set(0)

        # Place self in grid and place widgets
        self.grid_columnconfigure(0, weight=1)
        self.place_widgets()

    def place_widgets(self):
        """
        Defines frame and places widgets in the a grid
        """

        self.frame = tk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")

        # ROW 0
        tk.Label(self.frame, text="Background Color (HTML-name or hex): ").grid(row=0, column=0, sticky=tk.E)

        self.entry_background_color = tk.Entry(self.frame)
        self.entry_background_color.grid(row=0, column=1, sticky=tk.W)
        self.entry_background_color.insert(0, self.master.current_settings["background_color"])

        # ROW 1
        tk.Label(self.frame, text="Job history length: ").grid(row=1, column=0, sticky=tk.E)

        tk.OptionMenu(self.frame,
                      self.master.job_history_length,
                      *[i + 1 for i in range(31)]).grid(row=1, column=1, sticky=tk.W)

        # ROW 2
        tk.Label(self.frame, text="Select font size and family for buttons: ").grid(row=2, column=0, sticky=tk.E)

        tk.OptionMenu(self.frame,
                      self.master.fontsize_main,
                      *[i for i in range(3, 21)]).grid(row=2, column=1, sticky=tk.W)

        tk.OptionMenu(self.frame,
                      self.master.fontfam_main,
                      *font.families()).grid(row=2, column=2, sticky=tk.W)

        # ROW 3
        tk.Label(self.frame, text="Select font size and family for queue: ").grid(row=3, column=0, sticky=tk.E)

        tk.OptionMenu(self.frame,
                      self.master.fontsize_q,
                      *[i for i in range(3, 21)]).grid(row=3, column=1, sticky=tk.W)

        tk.OptionMenu(self.frame,
                      self.master.fontfam_q,
                      *font.families()).grid(row=3, column=2, sticky=tk.W)

        # ROW 4
        tk.Label(self.frame, text="Select font size and family for log: ").grid(row=4, column=0, sticky=tk.E)

        tk.OptionMenu(self.frame,
                      self.master.fontsize_log,
                      *[i for i in range(3, 21)]).grid(row=4, column=1, sticky=tk.W)

        tk.OptionMenu(self.frame,
                      self.master.fontfam_log,
                      *font.families()).grid(row=4, column=2, sticky=tk.W)

        # ROW 5
        tk.Label(self.frame, text="Path to scratch area on Stallo: ").grid(row=5, column=0, sticky=tk.E)

        self.entry_path_scratch_stallo = tk.Entry(self.frame)
        self.entry_path_scratch_stallo.grid(row=5, column=1, sticky=tk.W)
        self.entry_path_scratch_stallo.insert(0, self.master.path_scratch_stallo.get())

        # ROW 6
        tk.Label(self.frame, text="Path to scratch area on Fram: ").grid(row=6, column=0, sticky=tk.E)

        self.entry_path_scratch_fram = tk.Entry(self.frame)
        self.entry_path_scratch_fram.grid(row=6, column=1, sticky=tk.W)
        self.entry_path_scratch_fram.insert(0, self.master.path_scratch_fram.get())

        # ROW 7
        tk.Label(self.frame, text="Path to scratch area on Saga: ").grid(row=7, column=0, sticky=tk.E)

        self.entry_path_scratch_saga = tk.Entry(self.frame)
        self.entry_path_scratch_saga.grid(row=7, column=1, sticky=tk.W)
        self.entry_path_scratch_saga.insert(0, self.master.path_scratch_fram.get())

        # ROW 8
        tk.Label(self.frame, text="Extensions used for inputfiles (space-separated list): ").grid(row=8,
                                                                                                  column=0, sticky=tk.E)

        self.entry_inputfile_ext = tk.Entry(self.frame)
        self.entry_inputfile_ext.grid(row=8, column=1, sticky=tk.W)
        self.entry_inputfile_ext.insert(0, self.master.extensions_inputfiles.get())

        # ROW 9
        tk.Label(self.frame, text="Extensions used for outputfiles (space-separated list): ").grid(row=9, column=0,
                                                                                                   sticky=tk.E)

        self.entry_outputfile_ext = tk.Entry(self.frame)
        self.entry_outputfile_ext.grid(row=9, column=1, sticky=tk.W)
        self.entry_outputfile_ext.insert(0, self.master.extensions_outputfiles.get())

        # ROW 10
        tk.Label(self.frame, text="Local path to favourite visualizing software: ").grid(row=10, column=0, sticky=tk.E)

        self.entry_path_visualizer = tk.Entry(self.frame)
        self.entry_path_visualizer.grid(row=10, column=1, sticky=tk.W)
        self.entry_path_visualizer.insert(0, self.master.path_to_visualizer.get())

        vis_modes = {"Path": 0,
                     "Shell command": 1,
                     "Python command": 2}

        col = 0
        for mode, val in vis_modes.items():
            col += 1
            tk.Radiobutton(self.frame,
                           text=mode,
                           variable=self.master.visualizer_mode,
                           value=val).grid(row=10, column=1 + col)

        # ROW 11
        tk.Label(self.frame, text="Check for updates on startup?").grid(row=11, column=0, sticky=tk.E)

        tk.OptionMenu(self.frame,
                      self.master.check_for_updates,
                      *["Yes", "No"]).grid(row=11, column=1, sticky=tk.W)

        # ROW 12
        tk.Label(self.frame, text="Monitor queue update frequency (ms): ").grid(row=12, column=0, sticky=tk.E)

        self.entry_monitor_q_update_freq = tk.Entry(self.frame)
        self.entry_monitor_q_update_freq.grid(row=12, column=1, sticky=tk.W)
        self.entry_monitor_q_update_freq.insert(0, self.master.queue_monitor_update_frequency.get())

        # ROW 13
        tk.Label(self.frame, text="Highlight these users in CPU usage: (space sep)").grid(row=13, column=0, sticky=tk.E)

        self.entry_highlight_users = tk.Entry(self.frame)
        self.entry_highlight_users.grid(row=13, column=1, sticky=tk.W)
        self.entry_highlight_users.insert(0, self.master.cpu_usage_highlight_users.get())

        # ROW 14
        tk.Button(self.frame, text="Apply", command=self.get_new_settings, fg="green").grid(row=14, column=0, sticky=tk.W)
        tk.Checkbutton(self.frame, text="Preview", variable=self.preview).grid(row=14, column=1, sticky=tk.W)

        # Buttons
        tk.Button(self.frame, text="ColorPicker", command=self.colorpicker).grid(row=15, column=0, sticky=tk.W)
        tk.Button(self.frame, text="FontPicker", command=self.fontpicker).grid(row=16, column=0, sticky=tk.W)
        tk.Button(self.frame, text="Restore defaults", command=self.restore_defaults).grid(row=17, column=0, sticky=tk.W)
        tk.Button(self.frame, text="Exit", command=self.destroy, fg="red", bg="black").grid(row=18, column=0, sticky=tk.W)

    def get_new_settings(self):
        """
        Get settings from widgets and update self.master.current_settings.
        """
        self.master.current_settings["background_color"] = self.entry_background_color.get().strip()
        self.master.current_settings["job_history_length"] = self.master.job_history_length.get()
        self.master.current_settings["queue_monitor_update_frequency"] = self.entry_monitor_q_update_freq.get()
        self.master.current_settings["cpu_usage_highlight_users"] = self.entry_highlight_users.get()
        self.master.current_settings["visualizer_mode"] = self.master.visualizer_mode.get()
        self.master.current_settings["check_for_updates"] = "Yes" if self.master.check_for_updates.get() else "No"

        self.master.current_settings["fonts"]["main"]["size"] = self.master.fontsize_main.get()
        self.master.current_settings["fonts"]["main"]["family"] = self.master.fontfam_main.get()
        self.master.current_settings["fonts"]["log"]["size"] = self.master.fontsize_log.get()
        self.master.current_settings["fonts"]["log"]["family"] = self.master.fontfam_log.get()
        self.master.current_settings["fonts"]["q"]["size"] = self.master.fontsize_q.get()
        self.master.current_settings["fonts"]["q"]["family"] = self.master.fontfam_q.get()

        self.master.current_settings["paths"]["scratch_stallo"] = self.entry_path_scratch_stallo.get().strip()
        self.master.current_settings["paths"]["scratch_fram"] = self.entry_path_scratch_fram.get().strip()
        self.master.current_settings["paths"]["scratch_saga"] = self.entry_path_scratch_saga.get().strip()
        self.master.current_settings["paths"]["visualizer"] = self.entry_path_visualizer.get().strip()

        self.master.current_settings["extensions"]["input"] = self.entry_inputfile_ext.get().strip()
        self.master.current_settings["extensions"]["output"] = self.entry_outputfile_ext.get().strip()

        # Update widgets
        self.master.set_system_variables()
        self.master.set_fonts()
        self.update_all_widgets()

        # Write current settings to file if not in preview mode
        if not self.preview.get():
            self.master.dump_settings()
            self.parent.log_update("New settings written to file!")

    def restore_defaults(self):
        """
        If user agrees, then restore all settings to the defaults. The settings file is also updated,
        and the widgets in the window are updated.
        If user does not agree, then nothing happens.
        """
        msg = """
        Are you sure you want to restore to default settings? This cannot be undone.
        """
        if messagebox.askyesno(self.master.name, msg):
            self.master.current_settings = deepcopy(self.master.default_settings)
            self.master.set_system_variables()
            self.master.set_fonts()
            self.update_all_widgets()

            # Write default settings to file
            self.master.dump_settings()
            self.parent.log_update("Default settings written to file!")

    def update_all_widgets(self):
        """
        Destroy all widgets and place new widgets
        :return:
        """
        # We must destroy the current grids in order to remove all widgets
        for grid in [self.parent.topleft, self.parent.topright, self.parent.mid, self.parent.bot]:
            grid.destroy()

        # And finally we place the new widgets, and print the queue
        self.parent.place_widgets()
        self.parent.print_q()

    def colorpicker(self):
        ColorPicker(self)

    def fontpicker(self):
        FontPicker(self)
