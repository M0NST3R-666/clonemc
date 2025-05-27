import os # Imported os for path operations consistency
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError # Useful for specific error handling

from Clonify import LOGGER # Added LOGGER
_log = LOGGER(__name__) # Added logger instance

# Default ytdl options, can be overridden if needed
YTDL_OPTS_BASE = {
    "outtmpl": "downloads/%(id)s.%(ext)s", # Save to downloads folder
    "format": "bestaudio[ext=m4a]",       # Download best audio in m4a format
    "geo_bypass": True,                   # Bypass geographic restrictions
    "nocheckcertificate": True,           # Skip certificate verification (use with caution)
    "quiet": True,                        # No console output from yt-dlp itself
    "no_warnings": True,                  # Suppress yt-dlp warnings
}

# Instance for extracting info without downloading, if needed separately
# ytdl_info_extractor = YoutubeDL(YTDL_OPTS_BASE) # Not strictly needed by download function as written

def download(url: str, my_hook, custom_opts: dict = None) -> str: # Allow custom options
    """
    Downloads audio from a given URL using yt-dlp.

    Args:
        url: The URL of the video/audio to download.
        my_hook: A progress hook function to be called by yt-dlp.
        custom_opts: Optional dictionary to override default yt-dlp options.

    Returns:
        The file path of the downloaded audio, or an empty string on failure.
    """
    log_url = url[:100] + "..." if len(url) > 100 else url # For cleaner logs
    _log.info(f"Starting download process for URL: {log_url}")

    current_opts = YTDL_OPTS_BASE.copy()
    if custom_opts:
        current_opts.update(custom_opts)
    
    _log.debug(f"yt-dlp options for URL {log_url}: {current_opts}")

    downloaded_file_path = "" # Initialize to empty string

    try:
        # Extract info first to get 'id' and 'ext' for predictable filepath
        # This avoids downloading to get this info if the download call itself doesn't return it easily.
        # However, the original code directly calls download and constructs path later.
        # Let's stick to a pattern that ensures we know the path.
        
        # Initial info extraction (without download) to determine filename primarily
        # This is a separate call, not strictly necessary if download call provides enough info or if outtmpl is reliable.
        with YoutubeDL(current_opts) as ydl_info_check:
            info = ydl_info_check.extract_info(url, download=False)
            # Construct expected filepath based on 'outtmpl' and extracted info
            # This requires parsing outtmpl or having a fixed naming scheme.
            # Original code: xyz = path.join("downloads", f"{info['id']}.{info['ext']}")
            # This assumes 'id' and 'ext' are always available and match 'outtmpl'.
            # Let's ensure the 'downloads' directory exists.
            if not os.path.exists("downloads"):
                try:
                    os.makedirs("downloads")
                    _log.info("Created 'downloads' directory.")
                except OSError as e_dir:
                    _log.error(f"Could not create 'downloads' directory: {e_dir}. Download may fail.")
                    # Depending on policy, might return "" here.

            # The actual download process
            # Add progress hook to the options for THIS download instance
            opts_with_hook = current_opts.copy()
            if my_hook:
                opts_with_hook['progress_hooks'] = [my_hook]
            
            _log.debug(f"Starting actual download for {log_url} with progress hook.")
            with YoutubeDL(opts_with_hook) as ydl:
                error_code = ydl.download([url]) # download() returns 0 on success, 1 on error (by default)
                
                if error_code == 0: # Check if download was successful
                    # Construct the filename as yt-dlp would have created it.
                    # This relies on 'id' and 'ext' from the earlier info extraction.
                    # If 'outtmpl' is complex, this might not be robust.
                    # A safer way is to let yt-dlp return the filename or use a fixed output name if possible.
                    # For now, using the original logic for path construction.
                    if 'id' in info and 'ext' in info:
                         downloaded_file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                         _log.info(f"Download successful for URL: {log_url}. File saved to: {downloaded_file_path}")
                    else:
                         _log.error(f"Download reported success for {log_url}, but 'id' or 'ext' missing from info. Cannot determine filepath. Info: {info}")
                         downloaded_file_path = "" # Mark as failed if path unknown
                else:
                    _log.error(f"yt-dlp download method indicated an error (code: {error_code}) for URL: {log_url}.")
                    downloaded_file_path = "" # Mark as failed

    except DownloadError as de: # Specific yt-dlp download error
        _log.error(f"yt-dlp DownloadError for URL {log_url}: {de}", exc_info=True)
        downloaded_file_path = ""
    except Exception as e: # Catch any other exceptions
        _log.error(f"Generic exception during download process for URL {log_url}: {type(e).__name__} - {e}", exc_info=True)
        downloaded_file_path = "" # Ensure path is empty on any failure
    
    if downloaded_file_path and not os.path.exists(downloaded_file_path):
        _log.warning(f"Download logic completed for {log_url}, path determined as '{downloaded_file_path}', but file does not exist. Download likely failed silently or path is incorrect.")
        return "" # Return empty if file doesn't exist despite no explicit error

    return downloaded_file_path
