"""Compatibility entry point for strict, isolated completion verification.

The former hard-coded restart and permissive What-if checks are retired.
Use integration.run_backend_completion for builds/migrations/full acceptance.
"""
import os
from integration.verify_backend_completion import verify


def verify_live_candidate(base_url: str, db_url: str, output_log: str):
    if db_url != os.environ.get('TEST_DATABASE_URL'):
        raise ValueError('Explicit isolated TEST_DATABASE_URL must match; URLs are not logged')
    return verify(base_url, output_log)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    verify(args.base_url, args.output)