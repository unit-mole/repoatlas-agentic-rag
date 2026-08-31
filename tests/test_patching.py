from repoatlas.patching.verifier import verify_diff


def test_reject_test_suppression():
    assert not verify_diff("+ @pytest.mark.skip").passed


def test_accept_nonempty_clean_diff():
    assert verify_diff("+ return timeout + 1").passed
