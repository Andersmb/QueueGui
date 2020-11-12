import tkinter as tk
from tkinter import font
import math


class FontPicker(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.master = self.parent.master
        self.title("FontPicker")
        self.resizable(False, False)

        ROW, COL = 0, 0
        for f in font.families():
            label = tk.Label(self, text=f, font=(f, 12))
            label.grid(row=ROW, column=COL)
            label.bind("<Button-1>", lambda event, f=f: self.select_font(f))

            ROW += 1
            if ROW > 2*math.sqrt(len(font.families())):
                ROW = 0
                COL += 1

    def select_font(self, font):
        popup = tk.Toplevel()
        container = tk.Frame(popup)
        container.pack()

        popup.resizable(False, False)

        tk.Label(container, text="Select font for").grid(row=0, column=0, columnspan=3, sticky=tk.NSEW)

        tk.Button(container, text="Main", command=lambda: self.set_font(font, 0, popup)).grid(row=1, column=0,
                                                                                            sticky=tk.NSEW)
        tk.Button(container, text="Queue", command=lambda: self.set_font(font, 1, popup)).grid(row=1, column=1,
                                                                                           sticky=tk.NSEW)
        tk.Button(container, text="Log", command=lambda: self.set_font(font, 2, popup)).grid(row=1, column=2,
                                                                                       sticky=tk.NSEW)

    def set_font(self, font, mode, popup):
        """
        Update variables storing information about the fonts, and re-initialize MainWindow
        """
        if mode == 0:
            self.master.fontfam_main.set(font)
        elif mode == 1:
            self.master.fontfam_q.set(font)
        else:
            self.master.fontfam_low.set(font)

        self.parent.preview.set(True)
        self.parent.get_new_settings()
        self.parent.preview.set(False)

        popup.destroy()