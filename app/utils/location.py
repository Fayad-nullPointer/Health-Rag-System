import requests

def get_user_country() -> str:
    try:
        response = requests.get(
            "https://ipapi.co/json/",
            timeout=3
        )

        if response.ok:
            return response.json().get("country_name", "")
    except Exception:
        pass

    return ""