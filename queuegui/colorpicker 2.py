import tkinter as tk
from tkinter import font
import math


class ColorPicker(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.master = self.parent.master
        self.title("ColorPicker")

        self.frame = tk.Frame(self)
        self.frame.pack()

        self.buttonfont = font.Font(family="Arial", size=5)

        ROW, COL = 0, 0
        COLORS = range(1, int("FFFFFF", base=16), 50000)
        for color in COLORS:
            hexcolor = "#" + str(hex(color))[2:]
            hexcolor += "0"*(7 - len(hexcolor))

            l = tk.Label(self.frame, bg=hexcolor, fg=hexcolor, font=self.buttonfont, text="......")
            l.bind("<Button-1>", lambda event, x=hexcolor: self.set_color(x))
            l.grid(row=ROW, column=COL)

            ROW += 1
            if ROW > math.sqrt(len(COLORS)):
                ROW = 0
                COL += 1

    def set_color(self, color):
        self.parent.entry_background_color.delete(0, tk.END)
        self.parent.entry_background_color.insert(0, color)

        self.parent.preview.set(True)
        self.parent.get_new_settings()
        self.parent.preview.set(False)
