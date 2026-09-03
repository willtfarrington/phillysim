"""The routing toolchain and harness (EP-13; ADR-0008).

Everything the M3 spike's numbers come from, and nothing CI runs:

* :mod:`~phillysim.routing.toolchain` installs and checks the pinned Temurin
  JDK 21 build and the pinned R5 jar, project-local (``phillysim/.jdk/``,
  ``phillysim/.r5/``), through the guarded download path, never on ``PATH``;
* :mod:`~phillysim.routing.sampler` samples the process-tree RSS of a routing
  child at >= 1 Hz and kills the tree at the architecture.md line;
* :mod:`~phillysim.routing.records` is the run record's fixed, scrubbed shape
  under ``<data root>/runs/routing/<run-id>/``;
* :mod:`~phillysim.routing.harness` runs every JVM in a child process with an
  environment built per invocation (``JAVA_HOME``, the processor cap, r5py's
  heap, classpath, cache, and temporary directory under the data root);
* :mod:`~phillysim.routing.smoke` is the first route: one tract center to one
  supermarket-format retailer on EP-12's clipped network, three times.

No module here imports r5py or JPype at import time; only the harness child
does, inside the function that runs in the child (``tests/test_no_jvm_in_ci.py``
asserts it). The routing dependency group is optional and CI never installs it.
"""
