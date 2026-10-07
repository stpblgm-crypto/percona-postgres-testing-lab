import unittest
from run import REQUIRED, gate_pass

class GatePolicy(unittest.TestCase):
    def check(self, ids=None, **changes):
        state = dict(success_ids=list(REQUIRED) if ids is None else ids,
                     failures=[], errors=[], skips=[], expected_failures=[], unexpected_successes=[])
        state.update(changes)
        return gate_pass(**state)
    def test_complete_success(self): self.assertTrue(self.check())
    def test_no_tests(self): self.assertFalse(self.check(ids=[]))
    def test_missing_integration(self): self.assertFalse(self.check(ids=[sorted(REQUIRED)[0]]))
    def test_skipped(self): self.assertFalse(self.check(skips=['db']))
    def test_failure(self): self.assertFalse(self.check(failures=['db']))
    def test_error(self): self.assertFalse(self.check(errors=['db']))
    def test_expected_failure(self): self.assertFalse(self.check(expected_failures=['db']))
    def test_unexpected_success(self): self.assertFalse(self.check(unexpected_successes=['db']))
    def test_extra_test(self): self.assertFalse(self.check(ids=list(REQUIRED)+['extra']))
    def test_duplicate(self): self.assertFalse(self.check(ids=list(REQUIRED)+[sorted(REQUIRED)[0]]))

if __name__ == '__main__': unittest.main(verbosity=2)
