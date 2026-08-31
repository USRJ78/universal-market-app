"""
==============================================================================
  ORACLE CLOUD CONNECTIVITY & PORT SCANNER
==============================================================================
"""

import socket, sys

IP = "140.245.195.162"
PORTS = [22, 80, 8050, 443]

print(f"Testing connectivity to Oracle Cloud IP: {IP}...\n")

for port in PORTS:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    result = s.connect_ex((IP, port))
    if result == 0:
        print(f"  [OPEN]   Port {port:<5} -> Connection Successful!")
    else:
        print(f"  [CLOSED] Port {port:<5} -> Connection Timed Out / Blocked (Error code: {result})")
    s.close()
