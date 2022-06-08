import traceback


def _format_traceback_and_stdout_from_click_result(result):
    return "{}\n\n{}".format(traceback.print_exception(*result.exc_info), result.stdout)
