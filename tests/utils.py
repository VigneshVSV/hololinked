import unittest

class TestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.write(f' {test} ✔')
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.write(f' {test} ❌')
        self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.write(f' {test} ❌ Error')
        self.stream.flush()

class TestRunner(unittest.TextTestRunner):
    resultclass = TestResult