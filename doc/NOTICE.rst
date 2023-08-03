How to cite
***********

We ask that you take the following two actions whenever you:

- **use** the ``climate-assessment`` workflow, or any model(s) you have built using these tools
- **produce** any scientific publication, technical report, website, or other **publicly-available material**.

The aim of this request is to ensure good scientific practice and collaborative development of the platform.

1. Understand the code license
==============================

Use the most recent version of ``climate-assessment`` from the Github repository.
Specify clearly which version (e.g. release tag, such as ``v0.1.0``, or commit hash, such as ``26cc08f``) you have used, and whether you have made any modifications to the code.

Read and understand the file ``LICENSE``; in particular, clause 7 (“Disclaimer of Warranty”), which states:

    Unless required by applicable law or agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.

.. _notice-cite:

2. Cite the scientific publication
==================================

Cite, at minimum, the following manuscript:

  | Jarmo S. Kikstra, Zebedee R. J. Nicholls, Christopher J. Smith, Jared Lewis, Robin D. Lamboll, Edward Byers, Marit Sandstad, Malte Meinshausen, Matthew J. Gidden, Joeri Rogelj, Elmar Kriegler, Glen P. Peters, Jan S. Fuglestvedt, Ragnhild B. Skeie, Bjørn H. Samset, Laura Wienpahl, Detlef P. van Vuuren, Kaj-Ivar van der Wijst, Alaa Al Khourdajie, Piers M. Forster, Andy Reisinger, Roberto Schaeffer, and Keywan Riahi
  | "The IPCC Sixth Assessment Report WGIII climate assessment of mitigation pathways: from emissions to global temperatures".
  | *Geosci. Model Dev., 15, 9075–9109*
  | https://doi.org/10.5194/gmd-15-9075-2022
  | 2022

Additionally, you may cite the source code using the Zenodo reference (DOI: https://doi.org/10.5281/zenodo.6624519).

If you are using the AR6 scenario data (DOI: https://doi.org/10.5281/zenodo.5886911) and the AR6 infiller database (DOI: https://doi.org/10.5281/zenodo.6390767), you should in addition cite those respective sources.

In addition, to provide credit to the climate emulator modelers, please cite literature describing the climate emulator(s) that you use.

Lastly, you may cite the tools that enabled the development of this climate assessment workflow, including ``aneris``, ``silicone``, and ``openscm-runner``.

All these citations are also provided in full in the manuscript mentioned above, if further guidance is required on how to cite specific tools and data.

- **Cite the code via Zenodo**.
  The `DOI 10.5281/zenodo.6624519 <https://doi.org/10.5281/zenodo.6624519>`_ represents *all* versions of the :mod:`climate-assessment` code, and will always resolve to the latest version.
  Zenodo also provides citation export in BibTeX and other formats.
  If you would like to cite a specific release version, that is possible too and requires using the dedicate URLs, such as `DOI 10.5281/zenodo.6782457 <https://doi.org/10.5281/zenodo.6782457>` for version v0.1.1.
- Include a link, e.g. in a footnote, to the online documentation at https://climate-assessment.readthedocs.io.
