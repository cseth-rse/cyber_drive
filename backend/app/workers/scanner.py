# app/workers/scanner.py
"""
ClamAV integration via pyclamd.

If ClamAV is not installed or clamd is not running, the scanner falls back to
a CLEAN result and logs a warning — so the app still works in dev without ClamAV.

Install ClamAV:
  Ubuntu/Debian: sudo apt install clamav clamav-daemon && sudo freshclam && sudo systemctl start clamav-daemon
  macOS:         brew install clamav && freshclam
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CLAMD_AVAILABLE: bool | None = None  # None = not yet checked


def _get_clamd():
    global _CLAMD_AVAILABLE
    try:
        import pyclamd
        # Try Unix socket first (default on Linux), then TCP
        try:
            cd = pyclamd.ClamdUnixSocket()
            cd.ping()
            _CLAMD_AVAILABLE = True
            return cd
        except Exception:
            cd = pyclamd.ClamdNetworkSocket()
            cd.ping()
            _CLAMD_AVAILABLE = True
            return cd
    except Exception as exc:
        if _CLAMD_AVAILABLE is not False:
            logger.warning(
                "ClamAV daemon not reachable (%s). Running without virus scanning — "
                "all files will be marked CLEAN. Install ClamAV for production use.",
                exc,
            )
        _CLAMD_AVAILABLE = False
        return None


def scan_file(file_path: Path) -> tuple[bool, str]:
    """
    Scan a file with ClamAV.

    Returns:
        (is_clean: bool, detail: str)
        detail is 'CLEAN', a virus name, or an error message.
    """
    cd = _get_clamd()
    if cd is None:
        return True, "CLEAN (scanner unavailable)"

    try:
        result = cd.scan_file(str(file_path))
        if result is None:
            return True, "CLEAN"
        # result = {path: ('FOUND', 'Virus.Name')} or {path: ('ERROR', msg)}
        status, detail = next(iter(result.values()))
        if status == "FOUND":
            logger.warning("Virus detected in %s: %s", file_path, detail)
            return False, detail
        if status == "ERROR":
            logger.error("ClamAV scan error for %s: %s", file_path, detail)
            return False, f"Scan error: {detail}"
        return True, "CLEAN"
    except Exception as exc:
        logger.error("ClamAV scan exception for %s: %s", file_path, exc)
        # Conservative: treat scan failure as potentially unsafe
        return False, f"Scan failed: {exc}"
