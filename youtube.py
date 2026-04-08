from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    """
    Extract video ID from a YouTube URL.
    Supports standard and short URLs.
    """
    try:
        if not url:
            return None
        parsed_url = urlparse(url.strip())
        if "youtube.com" in url:
            vid = parse_qs(parsed_url.query).get("v", [None])[0]
            return vid
        if "youtu.be" in url:
            return parsed_url.path.lstrip("/").split("/")[0]
    except Exception:
        return None
    return None


def fetch_comments_from_youtube(api_key, video_id, max_pages=5):
    """
    Fetch comments for a given video ID using the YouTube Data API v3.
    Returns (comments_list, error_message).
    - comments_list: list of comment strings (may be empty on error)
    - error_message: string describing the error, or None on success
    """
    if not api_key or not api_key.strip():
        return [], "❌ No API Key provided. Please enter your YouTube Data API key in the sidebar."

    if not video_id:
        return [], "❌ Could not extract a valid Video ID from the URL."

    try:
        youtube = build("youtube", "v3", developerKey=api_key.strip())
    except Exception as e:
        return [], f"❌ Failed to initialise YouTube API client: {e}"

    comments = []
    next_page = None
    page_count = 0

    while page_count < max_pages:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                textFormat="plainText",
                pageToken=next_page
            )
            response = request.execute()
        except HttpError as e:
            error_reason = str(e)
            # Surface friendly messages for common error codes
            if "commentsDisabled" in error_reason:
                msg = "⚠️ Comments are disabled for this video."
            elif "403" in error_reason:
                msg = "🔑 API Key error (403 Forbidden). Check that your key has the YouTube Data API v3 enabled and is not restricted."
            elif "400" in error_reason:
                msg = f"🚫 Bad request (400). Double-check the Video URL. Details: {e}"
            elif "quotaExceeded" in error_reason:
                msg = "📛 YouTube API quota exceeded. Try again tomorrow or use a different API key."
            else:
                msg = f"❌ YouTube API Error: {e}"
            if comments:
                # Partial results — return what we have with a warning
                return comments, f"⚠️ Partial fetch stopped: {msg}"
            return [], msg
        except Exception as e:
            return [], f"❌ Unexpected error while calling YouTube API: {e}"

        for item in response.get("items", []):
            try:
                text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(text)
            except (KeyError, TypeError):
                continue

        next_page = response.get("nextPageToken")
        page_count += 1
        if not next_page:
            break

    if not comments:
        return [], "⚠️ No comments found for this video (it may have 0 comments or comments may be hidden)."

    return comments, None
