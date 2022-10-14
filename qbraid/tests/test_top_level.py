"""
Unit tests for qbraid top-level functionality

"""
import sys
from unittest.mock import Mock

import pytest

from qbraid import __version__
from qbraid._about import about
from qbraid._warnings import _warn_new_version
from qbraid.display_utils import running_in_jupyter, update_progress_bar
from qbraid.exceptions import PackageValueError
from qbraid.get_devices import get_devices
from qbraid.get_jobs import _display_jobs_jupyter, get_jobs

# pylint: disable=missing-function-docstring,redefined-outer-name

check_version_data = [
    # local, API, warn
    ("0.1.0", "0.1.1", True),
    ("1.0.7", "1.0.8", True),
    ("1.3.2", "2.0.6", True),
    ("0.1.0", "0.1.0", False),
    ("0.2.4.dev1", "0.2.4", False),
    ("0.1.0", "0.1.0.dev0", False),
    ("0.1.6.dev2", "0.1.6.dev5", False),
    ("0.1.6.dev5", "0.1.6.dev2", False),
]


job_status_list = [
    "INITIALIZING",
    "QUEUED",
    "VALIDATING",
    "RUNNING",
    "CANCELLING",
    "CANCELLED",
    "COMPLETED",
    "FAILED",
    "UNKNOWN",
]


def test_about(capfd):
    about()
    out, err = capfd.readouterr()
    assert __version__ in out
    assert len(err) == 0


@pytest.mark.parametrize("test_data", check_version_data)
def test_check_version(test_data):
    """Test function that compares local/api package versions to determine if
    update is needed."""
    local, api, warn_bool = test_data
    assert warn_bool == _warn_new_version(local, api)


def test_package_value_error():
    with pytest.raises(PackageValueError):
        raise PackageValueError("custom msg")


def test_update_progress_bar_done(capfd):
    """Test ``update_progress_bar`` for status 'Done'."""
    progress_val = 1
    expected_out = "\rProgress: [....................] 100% Done\r\n"
    update_progress_bar(progress_val)
    out, err = capfd.readouterr()
    assert out == expected_out
    assert len(err) == 0


def test_update_progress_bar_halted(capfd):
    """Test ``update_progress_bar`` for status 'Halted'."""
    progress_val = -1
    expected_out = "\rProgress: [                    ] 0% Halted\r\n"
    update_progress_bar(progress_val)
    out, err = capfd.readouterr()
    assert out == expected_out
    assert len(err) == 0


def test_running_in_jupyter():
    assert not running_in_jupyter()


def test_ipython_imported_but_ipython_none():
    _mock_ipython(None)
    assert not running_in_jupyter()


def test_ipython_imported_but_not_in_jupyter():
    _mock_ipython(MockIPython(None))
    assert not running_in_jupyter()


def test_ipython_imported_and_in_jupyter():
    _mock_ipython(MockIPython("non-empty kernel"))
    assert running_in_jupyter()


def test_get_jobs_no_results(capfd):
    """Test ``get_jobs`` stdout for results == 0.
    When no results are found, a single line is printed.
    """
    _mock_ipython(MockIPython(None))
    get_jobs(filters={"circuitNumQubits": -1})
    out, err = capfd.readouterr()
    assert out == "No jobs found matching given criteria\n"
    assert len(err) == 0


def test_get_jobs_results(capfd):
    """Test ``get_jobs`` stdout for results > 0.
    When results returned, output format is as follows:
    (1) Progress bar
    (2) Message
    (3) Empty line
    (4) Section titles
    (5) Underline titles
    (5+x) ``x`` lines of results
    (6+x) Empty line

    So, for ``numResults == x`` we expected ``6+x`` total lines from stdout.
    """
    _mock_ipython(MockIPython(None))
    num_results = 3  # test value
    lines_expected = 6 + num_results
    get_jobs(filters={"numResults": num_results})
    out, err = capfd.readouterr()
    lines_out = len(out.split("\n"))
    assert lines_out == lines_expected
    assert len(err) == 0


def test_display_jobs_in_jupyter(capfd):
    _mock_ipython(MockIPython("non-empty kernel"))
    data = []
    for index, value in enumerate(job_status_list):
        job_id = f"job_{index}"
        timestamp = f"timestamp_{index}"
        status_str = value
        job_tuple = (job_id, timestamp, status_str)
        data.append(job_tuple)
    msg = "test123"
    _display_jobs_jupyter(data, msg)
    out, err = capfd.readouterr()
    assert "IPython.core.display.HTML object" in out
    assert len(err) == 0


def test_get_jobs_in_jupyter(capfd):
    _mock_ipython(MockIPython("non-empty kernel"))
    get_jobs()
    out, err = capfd.readouterr()
    assert "IPython.core.display.HTML object" in out
    assert len(err) == 0


def test_get_devices_no_results(capfd):
    """Test ``get_devices`` stdout for results == 0, no refresh.
    When no results are found, a single line is printed.
    """
    _mock_ipython(MockIPython(None))
    get_devices(filters={"numberQubits": -1})
    out, err = capfd.readouterr()
    assert out == "No results matching given criteria\n"
    assert len(err) == 0


def test_get_devices_results(capfd):
    """Test ``get_devices`` stdout for results > 0, no refresh.
    When results returned, output format is as follows:
    (1) Message
    (2) Section titles
    (3) Underline titles
    (4+x) ``x`` lines of results
    (5+x) Empty line

    So, for a query returning ``x`` results, we expect ``5+x`` total lines from stdout.
    """
    _mock_ipython(MockIPython(None))
    get_devices(filters={"qbraid_id": "ibm_q_belem"})
    num_results = 1  # searching by device id will return one result
    lines_expected = 5 + num_results
    out, err = capfd.readouterr()
    lines_out = len(out.split("\n"))
    assert lines_out == lines_expected
    assert len(err) == 0


def test_get_devices_refresh_results(capfd):
    """Test ``get_devices`` stdout for results > 0, with refresh.
    When results returned, output format is as follows:
    (1) Progress bar
    (2) Empty line
    (3) Message
    (4) Empty line
    (5) Section titles
    (6) Underline titles
    (7+x) ``x`` lines of results

    So for a query returning ``x`` results, we expect ``6+x`` total lines from stdout.
    """
    _mock_ipython(MockIPython(None))
    get_devices(filters={"qbraid_id": "ibm_q_belem"}, refresh=True)
    num_results = 1  # searching by device id will return one result
    lines_expected = 7 + num_results
    out, err = capfd.readouterr()
    lines_out = len(out.split("\n"))
    assert lines_out == lines_expected
    assert len(err) == 0


def test_get_devices_in_jupyter(capfd):
    _mock_ipython(MockIPython("non-empty kernel"))
    get_devices()
    out, err = capfd.readouterr()
    assert "IPython.core.display.HTML object" in out
    assert len(err) == 0


def get_ipython():
    pass


def _mock_ipython(get_ipython_result):
    module = sys.modules["test_top_level"]
    sys.modules["IPython"] = module

    get_ipython = Mock(return_value=get_ipython_result)
    sys.modules["IPython"].__dict__["get_ipython"] = get_ipython


class MockIPython:
    """Mock IPython class for testing"""

    def __init__(self, kernel):
        self.kernel = kernel