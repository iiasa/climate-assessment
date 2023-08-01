Releasing
=========

1. Before releasing, check https://github.com/iiasa/climate-assessment/actions/workflows/ci-cd-workflow.yml to ensure that the push and scheduled builds are passing.
   Address any failures before releasing.

2. Tag the release candidate version, i.e. with a ``rcN`` suffix, and push::

    $ git tag v0.1.5rc1
    $ git push upstream v0.1.5rc1

3. Check:

   - at https://github.com/iiasa/climate-assessment/actions/workflows/publish.yaml that the workflow completes: the package builds successfully and is published to TestPyPI.
   - at https://test.pypi.org/project/climate-assessment/ that:

     - The package can be downloaded, installed and run.
     - The README is rendered correctly.

   Address any warnings or errors that appear.
   If needed, make a new commit and go back to step (2), incrementing the rc number.

4. On GitHub:

   - Create a new release with a new tag, e.g. v0.1.5.
   - Publish the release.

5. Check at https://github.com/iiasa/climate-assessment/actions/workflows/publish.yaml and https://pypi.org/project/climate-assessment/ that the distributions are published.
