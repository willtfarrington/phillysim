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
  supermarket-format retailer on EP-12's clipped network, three times;
* :mod:`~phillysim.routing.plan` and :mod:`~phillysim.routing.matrix` (EP-14)
  are the spike's runs as data and the resumable night driver;
* :mod:`~phillysim.routing.verdict`, :mod:`~phillysim.routing.handcheck`, and
  :mod:`~phillysim.routing.concordance` (EP-15) read a night against the M3
  criteria, route the hand check's pairs, and compare the walk times with the
  fallback engine (OSMnx + scipy, in the same optional group);
* :mod:`~phillysim.routing.stage` (EP-15) is the real pipeline's
  ``travel_times`` stage: the two core runs as a night, the matrix in the
  dictionary's shape.

No module here imports r5py or JPype at import time; only the harness child
does, inside the function that runs in the child (``tests/test_no_jvm_in_ci.py``
asserts it). The routing dependency group is optional and CI never installs it.
"""
