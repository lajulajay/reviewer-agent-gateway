#!/usr/bin/env python3
"""Store an API key in the macOS login Keychain without exposing it.

  keychain-store.py SERVICE

Prompts for the key with echo off (no length limit, unlike the `security`
prompt, which truncates at 128 characters) and writes it through the Security
framework, so the key never appears in argv, the environment, shell history
or a file. An existing item for SERVICE and $USER is replaced. Run it
yourself in a terminal; it prints only the stored length.
"""

import ctypes
import ctypes.util
import getpass
import os
import subprocess
import sys
import warnings

ERR_DUPLICATE = -25299


def main(argv):
    if len(argv) != 2 or not argv[1].replace("-", "").isalnum():
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 64
    service, account = argv[1].encode(), os.environ.get("USER", "").encode()
    if not sys.stdin.isatty():
        print("run this in an interactive terminal so the key is read with echo off", file=sys.stderr)
        return 65
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)  # never fall back to echoed input
        try:
            secret = getpass.getpass(f"Key for {argv[1]} (input hidden): ").strip().encode()
        except getpass.GetPassWarning:
            print("cannot turn off terminal echo; refusing to read the key", file=sys.stderr)
            return 65
    if not secret or not all(33 <= b < 127 for b in secret):
        print("refusing an empty key or one with spaces or non-ASCII characters", file=sys.stderr)
        return 65
    sec = ctypes.CDLL(ctypes.util.find_library("Security"))
    add = sec.SecKeychainAddGenericPassword
    add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p,
                    ctypes.c_uint32, ctypes.c_char_p, ctypes.c_void_p]
    add.restype = ctypes.c_int32
    status = add(None, len(service), service, len(account), account, len(secret), secret, None)
    if status == ERR_DUPLICATE:
        # Deleting needs only the service and account names, never the key.
        subprocess.run(["security", "delete-generic-password", "-a", account.decode(), "-s", service.decode()],
                       capture_output=True, check=False)
        status = add(None, len(service), service, len(account), account, len(secret), secret, None)
    if status != 0:
        print(f"Keychain write failed (OSStatus {status})", file=sys.stderr)
        return 70
    print(f"stored {len(secret)} characters in Keychain item {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
