# Copyright (C) 2023 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Unit tests for BraketProvider class

"""
import os
import random
import string

import pytest
from braket.circuits import Circuit

from qbraid.runtime.aws import BraketProvider
from qbraid.runtime.aws.job import BraketQuantumTask

# Skip tests if AWS account auth/creds not configured
skip_remote_tests: bool = os.getenv("QBRAID_RUN_REMOTE_TESTS", "False").lower() != "true"
REASON = "QBRAID_RUN_REMOTE_TESTS not set (requires configuration of AWS storage)"

SV1_ARN = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"


def gen_rand_str(length: int) -> str:
    """Returns a random alphanumeric string of specified length."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def get_braket_most_busy():
    """Return the most busy device for testing purposes."""
    provider = BraketProvider()
    devices = provider.get_devices(
        types=["QPU"], statuses=["ONLINE"], provider_names=["Rigetti", "IonQ", "Oxford"]
    )
    test_device = None
    max_queued = 0
    for device in devices:
        jobs_queued = device.queue_depth()
        if jobs_queued is not None and jobs_queued > max_queued:
            max_queued = jobs_queued
            test_device = device
    return test_device


@pytest.mark.skipif(skip_remote_tests, reason=REASON)
def test_braket_queue_visibility():
    """Test methods that check Braket device/job queue."""
    circuit = Circuit().h(0).cnot(0, 1)
    device = get_braket_most_busy()
    if device is None:
        pytest.skip("No devices available for testing")
    else:
        job = device.run(circuit, shots=10)
        queue_position = job.queue_position()
        job.cancel()
        assert isinstance(queue_position, int)


@pytest.mark.skipif(skip_remote_tests, reason=REASON)
def test_job_wrapper_type():
    """Test that job wrapper creates object of original job type"""
    provider = BraketProvider()
    device = provider.get_device(SV1_ARN)
    circuit = Circuit().h(0).cnot(0, 1)
    job_0 = device.run(circuit, shots=10)
    job_1 = BraketQuantumTask(job_0.id, task=None)
    assert isinstance(job_0, type(job_1))
    assert job_0.id == job_1.metadata()["job_id"]


@pytest.mark.skipif(skip_remote_tests, reason=REASON)
def test_is_available():
    """Test device availability function."""
    provider = BraketProvider()
    devices = provider.get_devices()
    for device in devices:
        is_available_bool, _, _ = device.availability_window()
        assert device._device.is_available == is_available_bool


@pytest.mark.skipif(skip_remote_tests, reason=REASON)
def test_get_quantum_tasks_by_tag():
    """Test getting tagged quantum tasks."""
    provider = BraketProvider()
    all_regions = list(provider.REGIONS)
    default_region = provider._get_default_region()
    alt_regions = [e for e in all_regions if e != default_region]
    circuit = Circuit().h(0).cnot(0, 1)
    device = provider.get_device(SV1_ARN)
    key, value1, value2 = tuple(gen_rand_str(7) for _ in range(3))
    task1 = device.run(circuit, shots=2, tags={key: value1})
    task2 = device.run(circuit, shots=2, tags={key: value2})
    assert set([task1.id, task2.id]) == set(provider.get_tasks_by_tag(key))
    assert len(provider.get_tasks_by_tag(key, values=[value1], region_names=[default_region])) == 1
    assert len(provider.get_tasks_by_tag(key, region_names=alt_regions)) == 0
