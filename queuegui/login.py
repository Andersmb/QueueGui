import tkinter as tk
import paramiko as pmk

import helpers


class Login(tk.Frame):
    def __init__(self, parent, **kwargs):
        """
        Window for logging in to a computing cluster.
        :param parent: parent widget, here a reference to queuegui.py
        :param kwargs:
        """
        tk.Frame.__init__(self, parent, **kwargs)
        self.parent = parent

        # Set the ssh client
        self.ssh_client = pmk.SSHClient()
        self.ssh_client.set_missing_host_key_policy(pmk.AutoAddPolicy())

        # Store hostname options and set default
        self.host_options = ["stallo", "fram", "saga"]
        self.parent.host.set(self.host_options[0])

        # Define and place widgets
        # Buttons
        tk.Button(self, text="Log in", command=self.authorize).grid(row=3, column=0, sticky=tk.W)
        tk.Button(self, text="Quit", command=self.quit).grid(row=4, column=0, sticky=tk.W)

        # Labels
        tk.Label(self, text="Username: ").grid(row=0, column=0, sticky=tk.E)
        tk.Label(self, text="Password: ").grid(row=1, column=0, sticky=tk.E)
        tk.Label(self, text="Host: ").grid(row=2, column=0, sticky=tk.E)
        tk.Label(self, text="Tip: Press <Control-c> to circle hostnames", font=("", 10)).grid(row=3, column=1)

        # Option Menus
        tk.OptionMenu(self, self.parent.host, *self.host_options).grid(row=2, column=1, sticky=tk.W)

        # Text entries
        self.entry_user = tk.Entry(self)
        self.entry_pwd = tk.Entry(self, show="*")

        self.entry_user.grid(row=0, column=1, sticky=tk.W)
        self.entry_pwd.grid(row=1, column=1, sticky=tk.W)

        self.entry_user.insert(0, "ambr")
        self.entry_pwd.insert(0, "Brosmetinden1!")

        # Bind the return key for easier login
        self.entry_pwd.bind("<Return>", self.authorize)

        # Get a modulo loop generator for looping over possible host names for easier login
        host_el_gen = helpers.modulo_generator(length=1500, mod=len(self.host_options))
        next(host_el_gen)  # Get rid of first element, since that is the same as default hostname

        # Bind keyboard combination to change the host name for logging in
        self.parent.bind("<Control-c>", lambda event: self.parent.host.set(self.host_options[next(host_el_gen)]))
        self.parent.bind("<Return>", self.authorize)

    def authorize(self, *args):
        """
        Attempt to log in by submitting the credentials
        :param args: the event will be passed when <Return> is pressed
        :return:
        """
        self.parent.pwd.set(self.entry_pwd.get())
        self.parent.user.set(self.entry_user.get())
        hostname = self.parent.cluster_data[self.parent.host.get()]["hostname"]

        try:
            self.ssh_client.connect(hostname=hostname, username=self.parent.user.get(), password=self.entry_pwd.get())
            self.entry_pwd.delete(0, tk.END)
            self.parent.show_main()

        except pmk.AuthenticationException:
            l_error = tk.Label(self, text="Login failed...", fg="red")
            l_error.grid(row=4, column=1, sticky=tk.W)
            l_error.after(5000, l_error.destroy)