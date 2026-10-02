"""Launch exactly one v066 import/open/solve callback chain."""

import os


def launch_head_only_solve_v066():
    os.environ["GAHYEON_IDENTITY_SOLVE_VERSION"] = "v066"
    os.environ["GAHYEON_IDENTITY_SOLVE_WAIT_TICKS"] = "2"
    from gahyeon_solve_head_only_identity_v059 import start_head_only_identity_v059

    start_head_only_identity_v059()


launch_head_only_solve_v066()
