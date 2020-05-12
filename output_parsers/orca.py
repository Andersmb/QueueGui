import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "queuegui"))

import helpers


class OrcaOut(object):
    def __init__(self, filename):
        self.filename = filename

        with open(self.filename) as f:
            self.source = f.read()
            self.content = self.source.splitlines()

    def __repr__(self):
        return "<OrcaOut(filename={})>".format(self.filename)

    def geometry_trajectory(self):
        """Return list of all geometry steps from a geometry optimization. The last step is the optimized geometry"""
        traj = []
        for i, line in enumerate(self.content):
            if line.strip().startswith("CARTESIAN COORDINATES (ANGSTROEM)"):
                traj.append(self.content[i+2:i+self.no_atoms()+2])
        # Strip all white space and newilne characters in traj

        return [[helpers.splitjoin(atom) for atom in geom] for geom in traj]

    def source(self):
        """Return the file content as a string."""
        with open(self.filename, "r") as f:
            return f.read()

    def normaltermination(self):
        """Evaluate whether the job
        terminated normally, and return a Boolean:
        True if termination was normal, False if not."""
        if self.content[-1].strip().startswith("TOTAL RUN TIME:"):
            return True
        return False
    
    def scf_energy(self):
        """Return a list of floats containing the optimized SCF energies.
        Note that these values INCLUDE the dispersion correction if present."""
        e = filter(lambda x: x.strip().startswith("FINAL SINGLE POINT ENERGY"), self.content)
        return list(map(float, map(lambda x: x.split()[4], e)))

    def no_scfcycles(self):
        """Return a list of floats containing the number of SCF iterations needed for converging each geom step"""
        c = filter(lambda x: ' '.join(x.split()).startswith("* SCF CONVERGED AFTER"), self.content)
        return list(map(int, map(lambda x: x.split()[4], c)))

    def walltime(self):
        """Return the total walltime for the job (float) in seconds"""
        w = [line for line in self.content if line.strip().startswith("TOTAL RUN TIME:")][0].split()
        return float(w[3])*86400 + float(w[5])*3600 + float(w[7])*60 + float(w[9]) + float(w[11])/1000

    def no_atoms(self):
        """Return the number of atoms of the system (integer)"""
        for line in self.content:
            if line.strip().startswith("Number of atoms"):
                return int(line.strip().split()[-1])
             
    def no_geomcycles(self):
        """Return the number of geometry cycles needed for convergence. Return an integer."""
        return len(self.geometry_trajectory())
    
    def no_basisfunctions(self):
        """Return the number of basis functions (integer)."""
        for line in self.content:
            if line.strip().startswith("Basis Dimension"):
                return int(line.strip().split()[-1])

    def maxforce(self):
        """Return a list of floats containing all Max Forces for each geometry iteration"""
        l = filter(lambda x: x.strip().startswith("MAX gradient"), self.content)
        l = filter(lambda x: len(x.split()) > 4, l)
        return list(map(float, map(lambda x: x.strip().split()[2], l)))

    def rmsforce(self):
        """Return a list of floats containing all RMS Forces for each geometry iteration"""
        l = filter(lambda x: x.strip().startswith("RMS gradient"), self.content)
        l = filter(lambda x: len(x.split()) > 4, l)
        return list(map(float, map(lambda x: x.strip().split()[2], l)))
    
    def maxstep(self):
        """Return a list of floats containing all Max Steps for each geometry iteration"""
        l = filter(lambda x: x.strip().startswith("MAX step"), self.content)
        return list(map(float, map(lambda x: x.strip().split()[2], l)))
    
    def rmsstep(self):
        """Return a list of floats containing all RMS Steps for each geometry iteration"""
        l = filter(lambda x: x.strip().startswith("RMS step"), self.content)
        return list(map(float, map(lambda x: x.strip().split()[2], l)))

    def tol_maxforce(self):
        """Return the Max Force convergence tolerance as float"""
        for line in self.content:
            if line.strip().startswith("MAX gradient") and len(line.split()) > 4:
                return float(line.strip().split()[3])

    def tol_rmsforce(self):
        """Return the RMSD Force convergence tolerance as float"""
        for line in self.content:
            if line.strip().startswith("RMS gradient") and len(line.split()) > 4:
                return float(line.strip().split()[3])

    def tol_maxstep(self):
        """Return the Max Step convergence tolerance as float
        :return: float
        """
        for line in self.content:
            if line.strip().startswith("MAX step"):
                return float(line.strip().split()[3])

    def tol_rmsstep(self):
        """Return the RMSD Step convergence tolerance as float
        :return: float
        """
        for line in self.content:
            if line.strip().startswith("RMS step"):
                return float(line.strip().split()[3])

    def orcaversion(self):
        """
        Return the version of ORCA as printed at the top of the output file
        :return: str
        """
        for line in self.content:
            if line.strip().startswith("Program Version"):
                return line.strip()

    def scf_convergence_tol_e(self):
        """
        Return the Energy change SCF convergence tolerance
        :return: float
        """
        for line in self.content:
            if line.split()[:4] == ["Energy", "Change", "TolE", "...."]:
                return float(line.split()[4])

    def scf_convergence_1el(self):
        """
        Return the 1-Electron energy change SCF convergence tolerance
        :return: float
        """
        for line in self.content:
            if line.split()[:4] == ["1-El.", "energy", "change", "...."]:
                return float(line.split()[4])

    def scf_convergences(self):
        """
        Return each set of SCF optimization cycle summaries.
        :return: list
        """
        output = self.content
        indeces = []
        for i, line in enumerate(self.content):
            if line.strip().startswith("SCF ITERATIONS"):
                start = i + 3
                for j in range(200):
                    try:
                        if "***" in output[start+j] and ("Energy Check signals convergence" not in output[start+j] or "convergence achieved" not in output[start+j]):
                            continue
                    except IndexError:
                        pass
                    try:
                        int(output[start+j].split()[0])
                        continue
                    except (ValueError, IndexError):
                        stop = start + j - 1
                        indeces.append({"start": start, "stop": stop})
                        break

        data = []
        for index in indeces:
            data.append([line.strip() for line in output[index["start"]:index["stop"]+1]])

        return [[line.strip() for line in cycle if not "***" in line] for cycle in data]

    def polarizability_diagonal(self):
        output = self.content
        diag = []
        for i, line in enumerate(output):
            if line.strip().startswith("The raw cartesian tensor"):
                diag.append(output[i+1].split()[0])
                diag.append(output[i+2].split()[1])
                diag.append(output[i+3].split()[2])
                return list(map(float, diag))

    def dispersion_correction(self):
        """
        Return the last print statement of the Dispersion correction. If not found,
        raise NoDispersionCorrection exception.
        :return:
        """
        for line in reversed(self.content):
            if line.strip().startswith("Dispersion correction  ") and len(line.split()) == 3:
                return float(line.split()[-1])
        else:
            raise NoDispersionCorrection("No dispersion correction found")

    def zero_point_energy_correction(self):
        """
        Return the last print statement of the Zero-point energy correction. If not found,
        raise NoZPECorrection exception.
        :return:
        """
        for line in reversed(self.content):
            if line.strip().startswith("Non-thermal (ZPE) correction"):
                return float(line.split()[3])
        else:
            raise NoZPECorrection("No ZPE correction found")

    def final_total_energy(self):
        """
        Return the final total energy. Note that this value does NOT INCLUDE the D3 correction.
        :return:
        """
        for line in reversed(self.content):
            if line.strip().startswith("Total Energy"):
                return float(line.split()[3])
        else:
            raise BadTermination("Possibly bad termination. Check output file!")

    def cmp_var(self, var):
        """
        Return the value of the given compound job variable name as a float.
        :param var:
        :return:
        """
        for line in reversed(self.content):
            if line.strip().lower().startswith(var.lower()):
                return float(line.split()[2])
        else:
            raise BadTermination("Possibly bad termination. Check output file!")

    def scf_timings(self):
        """
        Return the SCF timings in the output file
        :return:
        """
        t = []
        content = self.content
        for i, line in enumerate(content):
            if line.strip().startswith("Timings for individual modules:"):
                t.append(float(content[i+4].split()[3]))
        return t

    def no_cores(self):
        """

        :return:
        """
        c = []
        for line in self.content:
            if "%Pal NProcs" in line:
                c.append(int(line.split()[4]))
        return c


class OrcaHess(object):
    def __init__(self, filename):
        self.filename = filename

        with open(self.filename) as f:
            self.source = f.read()
            self.content = self.source.splitlines()

    def no_freq(self):
        for i, line in enumerate(self.content):
            if line.strip().startswith("$vibrational_frequencies"):
                return int(self.content[i+1].strip())

    def normal_modes(self):
        no_freq = self.no_freq()

        freqs, rawmodes = [], []
        modes = [[] for _ in range(no_freq)]

        for i, line in enumerate(self.content):
            # Get the frequencies
            if line.startswith("$vibrational_frequencies"):
                for j in range(no_freq):
                    freqs.append(float(self.content[i+j+2].split()[1]))

            # Now get all the normal modes
            if line.startswith("$normal_modes"):
                # Define some indexes for easier book-keeping on where to get stuff
                start = i + 3

                # The number of columns containing normal modes
                cols = len(self.content[start].split()) - 1

                # The number of times the columns are repeated (rows)
                rows = int(no_freq / cols) + 1

                # The number of columns in the last "line" of normal mode data
                rest = no_freq - (cols * (rows - 1))

                for r in range(rows - 1):  # Subtract one to exclude the "rest" set of data. Pick those up later
                    # define each line where the data starts
                    # i: start of normal mode section, 3: to get to where the data
                    # starts, r*(nfreq+1): move down in r multiples of nfreq (must add
                    # one due to the extra label line inbetween each normal mode)
                    start = i + 3 + r * (no_freq + 1)
                    for c in range(cols):
                        for freq in range(no_freq):
                            rawmodes.append(float(self.content[start+freq].split()[c+1]))

                # Now pick up the  "rest" normal modes
                start = i + 3 + (rows - 1) * (no_freq + 1)
                for r in range(rest):
                    for freq in range(no_freq):
                        rawmodes.append(float(self.content[start + freq].split()[r + 1]))

                # Now split the normal mode data into their x, y, and z components, as
                # this will make it easier to write to file
                mode_x = rawmodes[::3]
                mode_y = rawmodes[1::3]
                mode_z = rawmodes[2::3]

        # Rearrange the raw modes into a prettier format in modes
        for m in range(len(rawmodes)):
            if m % 3 == 0:
                main_index = int(m / (3 * self.no_atoms()))
                sub_index = int(m / 3)
                modes[main_index].append(str(mode_x[sub_index]) + " " + str(mode_y[sub_index]) + " " + str(mode_z[sub_index]))

        # Return a list of lists of floats
        return [[[float(el)for el in atom.split()] for atom in mode] for mode in modes]

    def geometry(self):
        geom = []
        for i, line in enumerate(self.content):
            if line.strip().startswith("$atoms"):
                for atom in range(self.no_atoms()):
                    geom.append(self.content[i+2+atom])

        geom = [[el.strip() for el in atom.split()] for atom in geom]
        return [atom[0] + " " + " ".join(atom[2:]) for atom in geom]

    def no_atoms(self):
        for i, line in enumerate(self.content):
            if line.strip().startswith("$atoms"):
                return int(self.content[i+1])

    def frequencies(self):
        content = self.content
        freq = []
        for i, line in enumerate(content):
            if line.strip().startswith("$vibrational_frequencies"):
                freq = content[i+2:i+2+self.no_freq()]
                return [float(f.split()[-1].strip()) for f in freq]


class NoDispersionCorrection(Exception):
    pass


class NoZPECorrection(Exception):
    pass


class BadTermination(Exception):
    pass

