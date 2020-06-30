import matplotlib.pyplot as plt
import os
import sys
sys.path.append(os.path.dirname(__file__))
from helpers import splitjoin


# Define the class MrchemOut, which will be MRChem output files.
class MrchemOut(object):
    def __init__(self, filename):
        self.filename = filename

        with open(self.filename) as f:
            self.source = f.read()
            self.content = self.source.splitlines()

    def content_generator(self):
        """Return a generator that yields the lines of the output file"""
        with open(self.filename, "r") as f:
            while True:
                yield next(f)

    def normaltermination(self):
        """This method evaluates whether the job
        terminated normally, and returns a Boolean:
        True if termination was normal, False if not."""
        for line in self.content:
            if "SCF did NOT converge!!!" in line:
                return False
            if "Exiting MRChem" in line:
                return True
        else:
            return False

    def dipole_norm_debye(self):
        """Return the norm of the calculated
        dipole moment vector in Debye (float)"""
        for i,line in enumerate(self.content):
            if line.strip().startswith("Length of vector"):
                return float(self.content[i+1])

    def dipole_norm_au(self):
        """Return the norm of the calculated
        dipole moment vector in atomic units (float)"""
        for i,line in enumerate(self.content):
            if line.strip().startswith("Length of vector"):
                return float(self.content[i].split()[-1])

    def dipole_vector(self):
        """Return a list of the three components of the dipole moment, in au"""
        vec = None
        for i, line in enumerate(self.content):
            if line.strip().startswith("Length of vector"):
                # different version of MRChem show different dipole moment data.
                # so first determine the correct way to extract the vector info
                if "--- Total ---" in self.content[i+3]:
                    vec = self.content[i+5]
                    # we need to get rid of brackets and commas
                    while "," in vec or "[" in vec or "]" in vec:
                        spec_char = ",[]"
                        for c in spec_char:
                            vec = ''.join(vec.split(c))
                    return vec.split()
                else:
                    return self.content[i+5].split()

    def polarizability_tensor(self):
        """Return a list of the polarizability tensor, in a.u."""
        tensor = None
        for i, line in enumerate(self.content):
            if "--- Tensor ---" in line:
                tensor = self.content[i+2:i+5]
                # Now get rid of brackets and commas in the tensor
                for j, el in enumerate(tensor):
                    while "," in tensor[j] or "[" in tensor[j] or "]" in tensor[j]:
                        chars = ",[]"
                        for c in chars:
                            tensor[j] = ''.join(tensor[j].split(c))
                break
        tensor = map(lambda x: x.strip(), tensor)
        tensor = [el.split() for el in tensor]
        return [[float(i) for i in el] for el in tensor]

    def polarizability_diagonal(self, unit="au"):
        """Return the diagonal elements of the polarizability tensor as a list of floats"""

        tensor = self.polarizability_tensor()
        diag = []
        for i, line in enumerate(tensor):
            for j, el in enumerate(line):
                if i==j:
                    diag.append(el)
        if unit == "au" or unit == "bohr":
            return diag
        elif unit == "angstrom":
            return [el / 1.8897162**3 for el in diag]

    def final_energy_pot(self):
        """This method returns the optimized potential energy (float)"""
        for line in reversed(self.content):
            if ' '.join(line.split()).startswith("Total energy : (au)"):
                return float(line.split()[-1].strip())
        else:
            raise Exception("Potential energy not found!")

    def precision(self):
        """This method returns the multiwavelet precision used in the calculation (float)"""
        for line in self.content:
            if line.strip().startswith("Precision"):
                return float(line.strip().split()[2])

    def no_scfcycles(self):
        """This method returns the number of SCF cycles performed before convergence (float)"""
        if not self.normaltermination():
            raise BadTerminationError("Calculation terminated badly. Check output file.")

        for line in reversed(self.content):
            if line.strip().startswith("SCF converged in"):
                return int(line.split()[3])

    def scf_energy(self):
        """Return a list of floats containing the SCF energies, indeces, Mo residuaks
           and updates"""
        # Get SCF iterations
        scf = []
        for i, line in enumerate(self.content):
            if all([line.strip().startswith("Iter"),
                    self.content[i-1].strip().startswith("=")]):
                for cycle in self.content[i+2:]:
                    if cycle.strip().startswith("-"):
                        break
                    scf.append((cycle.split()[1:]))

        mo, e, upd = zip(*scf)
        return [float(i) for i in mo], [float(i) for i in e], [float(i) for i in upd]

    def plot_scf_energy(self, title=None):
        """Return a graph plotting the potential energies"""

        prop_thrs = self.property_threshold()
        orb_thrs = self.orbital_threshold()

        mo_residual, energies, updates = self.scf_energy()
        xs = range(len(energies))

        property_thresholds = [prop_thrs for _x in xs]
        orbital_thresholds = [orb_thrs for _x in xs]

        fig = plt.Figure(figsize=(15, 5), dpi=100)
        plt.title("Job {}: {}".format(title, os.path.basename(self.filename)))
        ax = plt.gca()
        ax.plot(xs, list(map(abs, updates)), color="red", marker="o", markersize=2, mfc="black", mec="black", label="Energy Update")
        ax.plot(xs, mo_residual, color="blue", marker="o", markersize=2, mfc="black", mec="black", label="MO Residual")

        if orb_thrs:
            ax.plot(xs, orbital_thresholds, color="blue", linestyle="--", linewidth=1, label="Orbital Threshold")

        if prop_thrs:
            ax.plot(xs, property_thresholds, color="red", linestyle="--", linewidth=1, label="Energy Threshold")

        ax2 = ax.twinx()
        ax2.plot(xs, energies, color="gray", linewidth=3, label="Total Energy", marker="o", markersize=4, mfc="black")

        ax.set_ylabel("MO residual")
        ax2.set_ylabel("Energy [a.u]")
        ax.set_xlabel("SCF iteration")
        ax.set_yscale("log")
        ax2.set_yscale("linear")

        if prop_thrs:
            ax.set_ylim(prop_thrs/10)
        elif not prop_thrs and orb_thrs:
            ax.set_ylim(orb_thrs/10)
        else:
            ax.set_ylim(1e-8)  # Fallback value

        # Combine legends for ax and ax2
        ax_h, ax_l = ax.get_legend_handles_labels()
        ax2_h, ax2_l = ax2.get_legend_handles_labels()

        plt.legend(ax_h+ax2_h, ax_l+ax2_l, fancybox=True, framealpha=0.5)
        plt.grid(axis="both")
        plt.tight_layout()
        return plt.show()

    def walltime(self):
        """Return the total walltime for the job (float) in seconds"""
        for line in self.content:
            if ' '.join(line.strip().split()).startswith("*** Wall time"):
                s = float(line.split()[4][:-1]) * 3600
                m = float(line.split()[5][:-1]) * 60
                h = float(line.split()[6][:-1])
        return s + m + h

    def orbital_threshold(self):
        """Return the orbital convergence threshold as a float"""
        t = [line for line in self.content if line.strip().startswith("Orbital threshold")][0].split()[3]
        try:
            return float(t)
        except ValueError:
            return False

    def property_threshold(self):
        """Return the property convergence threshold as a float. This is the energy convergence threshold."""
        t = [line for line in self.content if line.strip().startswith("Energy threshold")][0].split()[3]
        try:
            return float(t)
        except ValueError:
            return False

    def version(self):
        """Return the line of output describing the MRChem version"""
        for line in self.content:
            try:
                if line.split()[1] == "VERSION":
                    return " ".join(line.split())
            except IndexError:
                continue

    def no_cores(self):
        """

        :return:
        """
        for line in self.content:
            if line.strip().startswith("Total cores"):
                return int(line.split()[3])


class BadTerminationError(Exception):
    pass
