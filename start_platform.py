# -*- coding: utf-8 -*-
"""
StratumRO Geospatial Platform Launcher.
Starts the FastAPI backend engine, verifies the live QGIS Desktop bridge,
and provides access to the Web Cockpit.

Usage:
    venv\\Scripts\\python start_platform.py [--port 8000] [--host 127.0.0.1]
"""

import argparse
import socket
import sys
import time
import webbrowser
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_qgis_socket(host: str = "127.0.0.1", port: int = 9876) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Start StratumRO Geospatial Platform")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn hot reload")
    args = parser.parse_args()

    print("=" * 75)
    print("      STRATUMRO GEOSPATIAL PLATFORM & PRE-CADASTRE STUDIO")
    print("=" * 75)
    print(f"[*] Platform Engine:  FastAPI + Uvicorn")
    print(f"[*] Host Address:     http://{args.host}:{args.port}")
    print(f"[*] Swagger Docs:     http://{args.host}:{args.port}/docs")
    print(f"[*] Geodetic CRS:     Stereo 70 (EPSG:3844 ANCPI)")

    # QGIS Socket Check
    qgis_online = check_qgis_socket()
    if qgis_online:
        print(f"[+] QGIS Desktop 3.40: CONNECTED via TCP 127.0.0.1:9876")
    else:
        print(f"[!] QGIS Desktop 3.40: NOT DETECTED on port 9876 (Web map will run with cached/mock layers)")

    url = f"http://{args.host}:{args.port}"
    print(f"\n[+] StratumRO Studio is ready! Access Web Cockpit at: {url}\n")

    if not args.no_browser:
        # Give uvicorn a moment to bind, then open browser
        import threading
        def _open():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        "stratum_ro.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
