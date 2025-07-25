Index of documentation
**********************

Integrated assessment models (IAMs) produce emissions pathways as part of larger
pathway output coming from the modelling of scenarios. These emissions pathways
imply a certain temperature development.
Some integrated assessment modelling teams can provide their own climate assessment
based on these emissions outcomes, others just work on the level of emissions.
Not all IAMs model all societal processes that cause emissions, meaning that they
also generally do not report all emissions species required to run a climate model.

For the Working Group III (WGIII) contribution to the IPCC Sixth Assessment (AR6)
report, a large set of scenarios with emissions pathways had to be assessed and
classified based on their temperature implications.
To do so, emission pathways need to be harmonized to the same historical
emissions, need to report the same set of greenhouse gases, and need to be run
with the same (simple) climate model(s).

This repository package allows for reproducing the AR6 results, as well as assessing
your own full-century emissions pathways, given certain minimum requirements as
described in the :doc:`general`.

More information on how this package was used in AR6 can be found in the report
itself, as well as the manuscript accompanying the release of this package.

.. _getting-started:

Getting started
===============

.. NB this ReST pattern is repeated throughout this file:

   1. List of :doc:`...` links, followed by
   2. .. toctree:: directive with :hidden:, containing the same links.

   This overcomes limitations of toctree, allowing introductory paragraphs, and different titles in this page than in the sidebar.

While this package aims to make it easier to run a climate model for a specific
long-term scenario with emissions pathways, it is not quite "click and run".
Using this package requires some domain knowledge, understanding of certain
research methods, and scientific computing skills.

- :doc:`prereqs` gives an (incomplete, but hopefully helpful) list of these items for formal and self-guided learning.

After you have read the section above, you can get started with reading a more
detailed description of the workflow (:doc:`general`), read about what ways there
are to install this software (:doc:`install`), and go through a few examples
for new users that demonstrate the basic features of the workflow (:doc:`user_guide`).

.. toctree::
   :hidden:
   :caption: Getting started

   prereqs
   general
   install
   user_guide

.. _core:

Code description
================

To better understand what is going on, or to use more advanced options of this
workflow, we provide more detailed documentation on specific parts of the workflow,
as well as describe the functionality of the functions in the code base.

The page :doc:`code` provides detailed description of the command line interface
(CLI), that can be used from e.g. an Anaconda prompt, and descriptions of specific
functions for infilling, harmonization, climate emulator runs, and post-processing.

The page :doc:`emulator` provdies more detail and instructions on how the climate
emulators FaIR, CICERO-SCM, and MAGICC are coupled to this workflow, where to
download additional files, and how to set up emulators for running.

The page :doc:`utility` lists a couple of utility functions that serve some
specific functions including calculating a GHG basket to estimate CO2eq Kyoto
Gases.

Lastly, if you would like to contribute to the code of this package, please check
out the :doc:`dev`.

.. toctree::
   :hidden:
   :caption: Code description

   code
   emulator
   utility
   dev


License
=======
This package is licensed under an MIT License.
You may obtain a copy of the License at https://github.com/iiasa/climate-assessment/blob/main/LICENSE.


.. _acknowledgements:

Acknowledgements
================

Per good scientific practice, you **must** cite the following publication when you use this package in scientific work.

  | Jarmo S. Kikstra, Zebedee R. J. Nicholls, Christopher J. Smith, Jared Lewis, Robin D. Lamboll, Edward Byers, Marit Sandstad, Malte Meinshausen, Matthew J. Gidden, Joeri Rogelj, Elmar Kriegler, Glen P. Peters, Jan S. Fuglestvedt, Ragnhild B. Skeie, Bjørn H. Samset, Laura Wienpahl, Detlef P. van Vuuren, Kaj-Ivar van der Wijst, Alaa Al Khourdajie, Piers M. Forster, Andy Reisinger, Roberto Schaeffer, and Keywan Riahi
  | "The IPCC Sixth Assessment Report WGIII climate assessment of mitigation pathways: from emissions to global temperatures".
  | *Geosci. Model Dev., 15, 9075–9109*
  | https://doi.org/10.5194/gmd-15-9075-2022
  | 2022

You may additionally also cite the package itself:

  | Kikstra, J. S., Nicholls, Z. R. J., Lewis, J., Smith, C. J., Lamboll, R. D., Byers, E., Sandstad, M., Wienpahl, L., and Hackstock, P.:
  | Climate assessment of long-term emissions pathways: IPCC AR6 WGIII version,
  | Zenodo, 10.5281/zenodo.6624519, 2022.


For more detail, see :doc:`NOTICE`.

.. toctree::
   :hidden:
   :caption: Acknowledgments

   NOTICE
