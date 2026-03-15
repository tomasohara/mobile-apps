#! /usr/bin/env python

from mezcla import system, debug
import sys
import traceback

def test_crash_repro():
    print(f"sys.stderr: {sys.stderr}")
    print(f"sys.stderr type: {type(sys.stderr)}")
    
    # First registration
    system.getenv_value("POE_API", None, desc="API key for POE")
    
    # Second registration with different description - this triggers the warning and trace_stack
    print("Triggering second registration...")
    # Manually call what register_env_option does to isolate
    try:
        print("Calling traceback.print_stack(file=sys.stderr)...")
        traceback.print_stack(file=sys.stderr)
        print("traceback.print_stack(file=sys.stderr) done.")
    except Exception as e:
        print(f"traceback.print_stack failed: {e}")

if __name__ == "__main__":
    # Set DEBUG_LEVEL high
    import os
    os.environ["DEBUG_LEVEL"] = "6"
    debug.debug_init(force=True)
    
    test_crash_repro()
