import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime

from helpers import splitjoin


class ConvertMe(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.master = self.parent.master
        self.name = "ConvertMe"
        self.title(self.name)
        self.resizable(False, False)

        # Set background color
        self["bg"] = self.parent.master.background_color.get()

        # Place widgets
        self.place_widgets()

        # Greet user
        self.log_update("Welcome to ConvertMe!")

    def place_widgets(self):
        """
        Set up grid and place widgets
        """
        self.top = tk.Frame(self, bg=self.master.background_color.get())
        self.bot = tk.Frame(self, bg=self.master.background_color.get())

        self.top.grid(row=0, column=0, sticky="nsew")
        self.bot.grid(row=1, column=0, sticky="nsew")

        self.top.grid_columnconfigure(0, weight=1)

        # Buttons
        tk.Button(self.bot,
                  text=".xyz -> .com",
                  font=self.master.main_font,
                  command=self.xyz_to_com).grid(row=0, column=0, pady=5, padx=5)

        tk.Button(self.bot,
                  text=".com -> .xyz",
                  font=self.master.main_font,
                  command=self.com_to_xyz).grid(row=0, column=1, pady=5, padx=5)

        tk.Button(self.bot,
                  text=".ang -> .bohr",
                  font=self.master.main_font,
                  command=self.ang_to_bohr).grid(row=0, column=2, pady=5, padx=5)

        tk.Button(self.bot,
                  text=".bohr -> .ang",
                  font=self.master.main_font,
                  command=self.bohr_to_ang).grid(row=0, column=3, pady=5, padx=5)

        tk.Button(self.top,
                  text="Browse File",
                  font=self.master.main_font,
                  command=self.browse_file).grid(row=0, column=1, sticky="e", pady=5, padx=5)

        tk.Button(self.bot,
                  text="Quit",
                  font=self.master.main_font,
                  fg="red",
                  command=self.destroy).grid(row=1, column=0, pady=5, padx=5)

        # create the entry and place it in the mainframe
        self.entry_file = tk.Entry(self.top)
        self.entry_file.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

        # crate a vertical scrollbar and log window
        yscrollbar = tk.Scrollbar(self.top)
        yscrollbar.grid(row=1, column=4, pady=2, padx=2, sticky="ns")

        self.log = tk.Text(self.top, height=10, yscrollcommand=yscrollbar.set, bg="black", fg="white")
        self.log.grid(row=1, columnspan=2, pady=5, padx=5, sticky="ew")

        yscrollbar.config(command=self.log.yview)

    def log_update(self, msg):
        logmsg = "[{}] {}\n".format(str(datetime.now().time()).split(".")[0], msg)
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, logmsg)
        # self.log.config(state=tk.DISABLED)
        self.log.see(tk.END)

    def xyz_to_com(self):
        """Convert an XYZ file format to a Gaussian input format (.com). The input file
           contains only the bare minimum to be opened with GaussView, essentially only the coordinates.
           The new filename is the same as the given XYZ file, but with '.com' extension, so beware
           that you don't overwrite any files."""

        xyzfile = self.entry_file.get().split()
        for f in xyzfile:
            if not os.path.isfile(f):
                return self.log_update("Error: File Not Found!")

            job = f.split(".")[0]
            ext = f.split(".")[-1]
            if ext != "xyz":
                return self.log_update("Error: You must specify an XYZ file!")

            with open(f, "r") as infile:
                inlines = infile.readlines()[2:]

            # get rid of special characters such as tabs and newlines
            coords = [splitjoin(atom) for atom in inlines]

            with open(job + ".com", "w") as o:
                o.write("#\n")
                o.write("\n")
                o.write(f"Number of atoms: {len(coords)}\n")
                o.write("\n")
                o.write("0 1\n")

                for atom in coords:
                    o.write(atom + "\n")
                o.write('\n')
            self.log_update(f"New file written: {job+'.com'}")
        return None

    def com_to_xyz(self):
        """Extract the coordinates from a Gaussian input file, and save them as an XYZ file.
           The new filename is the same as the given XYZ file, but with '.com' extension, so beware
           that you don't overwrite any files."""
        comfile = self.entry_file.get().split()
        for f in comfile:
            if not os.path.isfile(f):
                self.log_update("Error: File Not Found!")
                return

            job = f.split(".")[0]
            ext = f.split(".")[-1]
            if ext != "com":
                self.log_update("Error: You must specify a COM file!")
                return

            with open(f) as infile:
                coords = infile.read().split("\n\n")[2].split("\n")[1:]

            # get rid of special characters such as tabs and newlines
            coords = [splitjoin(atom) for atom in coords]

            with open(job + ".xyz", "w") as o:
                o.write(f"{len(coords)}\n")
                o.write("\n")
                for atom in coords:
                    o.write(atom + "\n")
            self.log_update(f"New file written: {job+'.xyz'}")
        return None

    def ang_to_bohr(self):
        """Convert the XYZ coordinates in an XYZ file from Angstrom to Bohr.
           Only works with XYZ files."""
        xyzfile = self.entry_file.get()
        if not os.path.isfile(xyzfile):
            return self.log_update("Error: File Not Found!")

        job = xyzfile.split(".")[0]
        ext = xyzfile.split(".")[-1]
        if ext != "xyz":
            return self.log_update("Error: You must specify an XYZ file!")

        with open(xyzfile, "r") as infile:
            coords = infile.readlines()[2:]
        elements = [atom.split()[0] for atom in coords]
        coords = [atom.split()[1:] for atom in coords]

        for i, atom in enumerate(coords):
            for j, c in enumerate(atom):
                coords[i][j] = str(float(coords[i][j]) * 1.889726)

        with open(job + "_bohr.xyz", "w") as o:
            o.write(f"{len(coords)}\n")
            o.write(f"Coordinates in Bohr, created by {self.name}\n")
            for i, atom in enumerate(elements):
                o.write(f"{atom} {' '.join(coords[i])}\n")
        return self.log_update(f"New coordinates written to: {job+'_bohr.xyz'}")

    def bohr_to_ang(self):
        """Convert the XYZ coordinates in an XYZ file from Bohr to Angstrom.
           Only works with XYZ files."""
        xyzfile = self.entry_file.get()
        if not os.path.isfile(xyzfile):
            return self.log_update("Error: File Not Found!")

        job = xyzfile.split(".")[0]
        ext = xyzfile.split(".")[-1]
        if ext != "xyz":
            return self.log_update("Error: You must specify an XYZ file!")

        with open(xyzfile, "r") as infile:
            coords = infile.readlines()[2:]
        elements = [atom.split()[0] for atom in coords]
        coords = [atom.split()[1:] for atom in coords]

        for i, atom in enumerate(coords):
            for j, c in enumerate(atom):
                coords[i][j] = str(float(coords[i][j]) / 1.889726)

        with open(job + "_ang.xyz", "w") as o:
            o.write(f"{len(coords)}\n")
            o.write(f"Coordinates in Angstrom, created by {self.name}\n")
            for i, atom in enumerate(elements):
                o.write(f"{atom} {' '.join(coords[i])}\n")
        return self.log_update("New coordinates written to: {}".format(job + "_ang.xyz"))

    def browse_file(self):
        ftypes = [("All files", "*.*"),
                  ("XYZ files", "*.xyz"),
                  ("Gaussian input files", "*.com")]

        self.entry_file.delete(0, tk.END)
        self.entry_file.insert(0, filedialog.askopenfilenames(initialdir=os.getcwd(),
                                                              parent=self, title="Select File", filetypes=ftypes,
                                                              defaultextension="*.*"))
