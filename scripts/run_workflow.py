from multiprocessing import freeze_support

import climate_assessment.cli

if __name__ == "__main__":
    freeze_support()
    climate_assessment.cli.workflow()
