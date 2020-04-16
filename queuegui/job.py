class Job:
    def __init__(self, ssh_client=None, pid=None):
        """
        Class that describes a job instance in the queue, fully defined by its process ID.

        :param root: an instance of MainWindow in order to access some methods
        :param pid: the process ID of the job
        """
        self.pid = pid
        self.ssh_client = ssh_client  # the MainWindow instance
        self.cmd = f"scontrol show jobid {self.pid}"

    def jobinfo(self):
        stdin, stdout, stderr = self.ssh_client.exec_command(self.cmd)
        return stdout.read().decode("ascii")

    def get_info(self, target, delim=" "):
        field = [line for line in self.jobinfo().splitlines() if target+"=" in line][0]
        return [el for el in field.split(delim) if target+"=" in el][0].split("=")[1]
