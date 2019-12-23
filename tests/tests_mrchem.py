import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from output_parsers.mrchem import MrchemOut


class TestMRChem(unittest.TestCase):

    def setUp(self):
        self.output = MrchemOut("mrchem_energy_test.out")

    def tearDown(self):
        pass

    def test_normaltermination(self):
        self.assertEqual(self.output.normaltermination(), True)

    def test_final_energy_pot(self):
        self.assertEqual(self.output.final_energy_pot(), -2.754654312726e+03)

    def test_precision(self):
        self.assertEqual(self.output.precision(), 1.00000e-04)

    def test_no_scfcycles(self):
        self.assertEqual(self.output.no_scfcycles(), 51)

    def test_scf_energy(self):
        self.assertEqual(len(self.output.scf_energy()) - 1, self.output.no_scfcycles())
        self.assertEqual(self.output.scf_energy()[11][1], -2747.810561686282)


if __name__ == "__main__":
    unittest.main()
