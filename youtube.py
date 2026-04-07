from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    """
    Extract video ID from a YouTube URL.
    """
    try:
        parsed_url = urlparse(url)
        if "youtube.com" in url:
            return parse_qs(parsed_url.query).get("v", [None])[0]
        if "youtu.be" in url:
            return parsed_url.path.split("/")[1]
    except:
        return None
    return None

def fetch_comments_from_youtube(api_key, video_id):
    """
    Fetch comments for a given video ID using the YouTube Data API.
    """
    youtube = build("youtube", "v3", developerKey=api_key)
    comments = []
    next_page = None

    while True:
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
            print(f"YouTube API Error: {e}")
            break

        for item in response.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text)

        next_page = response.get("nextPageToken")
        if not next_page:
            break

    return comments
