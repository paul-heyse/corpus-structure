import time


def test_before():
    assert True


def test_hangs():
    time.sleep(30)


def test_after():
    assert True
