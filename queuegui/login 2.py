import tkinter as tk
from tkinter import simpledialog, messagebox
import paramiko as pmk
import os
import sys

import helpers
from toolbox import ToolBox
from convertme import ConvertMe

dir_img = os.path.join(os.path.dirname(os.path.dirname(__file__)), "img")


class Login(tk.Frame):
    def __init__(self, parent, **kwargs):
        """
        Window for logging in to a computing cluster.
        :param parent: parent widget, here a reference to queuegui.py
        :param kwargs:
        """
        tk.Frame.__init__(self, parent, **kwargs)
        self.parent = parent
        self.pady = 5
        self.padx = 5

        # Set the ssh client
        self.ssh_client = pmk.SSHClient()
        self.ssh_client.set_missing_host_key_policy(pmk.AutoAddPolicy())

        # Define and place widgets
        for i, cluster in enumerate(self.parent.photos.keys()):
            login_cmd = lambda cluster=cluster: self.authorize(cluster)
            tk.Button(self,
                      image=self.parent.photos[cluster],
                      width=100,
                      height=100,
                      command=login_cmd).grid(row=0, column=i, pady=self.pady, padx=self.padx)
            tk.Label(self,
                     text=cluster.upper()).grid(row=1, column=i)

    def authorize(self, cluster):
        self.parent.host.set(cluster)
        hostname = self.parent.cluster_data[cluster]["hostname"]
        if self.parent.firstlogin.get():
            user = tk.simpledialog.askstring("", "Username: ")
            pwd = tk.simpledialog.askstring("", "Password: ", show="*")
            self.send_credentials(hostname, user, pwd)

            self.parent.user.set(user)
            self.parent.pwd.set(pwd)

            self.parent.show_main()
        else:
            self.send_credentials(hostname, self.parent.user.get(), self.parent.pwd.get())
            self.parent.show_main()

    def send_credentials(self, hostname, user, pwd):
        try:
            self.ssh_client.connect(hostname=hostname, username=user, password=pwd)
            self.parent.firstlogin.set(False)
        except pmk.ssh_exception.AuthenticationException:
            tk.messagebox.showerror("Error", f"Login to {hostname.split('.')[0]} failed:\nIncorrect username or password.")