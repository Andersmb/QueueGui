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

    def test_parsing(self):
        self.assertEqual(self.output.normaltermination(), True)
        self.assertEqual(self.output.final_energy_pot(), -2.754654312726e+03)
        self.assertEqual(self.output.precision(), 1.00000e-04)
        self.assertEqual(self.output.no_scfcycles(), 51)
        self.assertEqual(len(self.output.scf_energy()) - 1, self.output.no_scfcycles())
        self.assertEqual(self.output.scf_energy()[11][1], -2747.810561686282)
        self.assertEqual(self.output.orbital_threshold(), 3.16228e-03)
        self.assertEqual(self.output.property_threshold(), 1.00000e-05)
        self.assertEqual(self.output.precision(), 1.00000e-04)
        self.assertEqual(self.output.version(), "*** VERSION 0.2.0 (rev. 3869e6d) ***")
        self.assertEqual(self.output.no_cores(), 80)


if __name__ == "__main__":
    unittest.main()
