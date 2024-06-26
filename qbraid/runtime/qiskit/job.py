# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Module defining QiskitJob Class

"""
import logging
from typing import TYPE_CHECKING, Optional

from qiskit_ibm_runtime.exceptions import RuntimeInvalidStateError

from qbraid.runtime.enums import JobStatus
from qbraid.runtime.exceptions import JobStateError, QbraidRuntimeError
from qbraid.runtime.job import QuantumJob

from .result import QiskitResult

if TYPE_CHECKING:
    import qiskit_ibm_runtime

logger = logging.getLogger(__name__)

IBM_JOB_STATUS_MAP = {
    "INITIALIZING": JobStatus.INITIALIZING,
    "QUEUED": JobStatus.QUEUED,
    "VALIDATING": JobStatus.VALIDATING,
    "RUNNING": JobStatus.RUNNING,
    "CANCELLED": JobStatus.CANCELLED,
    "DONE": JobStatus.COMPLETED,
    "ERROR": JobStatus.FAILED,
}


class QiskitJob(QuantumJob):
    """Wrapper class for IBM Qiskit ``Job`` objects."""

    def __init__(
        self, job_id: str, job: "Optional[qiskit_ibm_runtime.RuntimeJob]" = None, **kwargs
    ):
        """Create a ``QiskitJob`` object."""
        super().__init__(job_id, **kwargs)
        self._job = job or self._get_job()

    def _get_job(self):
        """Return the job like object that is being wrapped."""
        try:
            service = self.device._service
            return service.job(self.id)
        except Exception as err:  # pylint: disable=broad-exception-caught
            raise QbraidRuntimeError(f"Error retrieving job {self.id}") from err

    def status(self):
        """Returns status from Qiskit Job object."""
        job_status = self._job.status().name
        status = IBM_JOB_STATUS_MAP.get(job_status, JobStatus.UNKNOWN)
        self._cache_metadata["status"] = status
        return status

    def result(self):
        """Return the results of the job."""
        if self.is_terminal_state():
            logger.info("Result will be available when job has reached final state.")
        return QiskitResult(self._job.result())

    def cancel(self):
        """Attempt to cancel the job."""
        if self.is_terminal_state():
            raise JobStateError("Cannot cancel quantum job in non-terminal state.")
        try:
            return self._job.cancel()
        except RuntimeInvalidStateError as err:
            raise JobStateError from err
