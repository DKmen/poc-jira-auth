import base64
from fastapi import FastAPI, Request
import requests
import os

from requests.auth import HTTPBasicAuth

# Create a new FastAPI instance
app = FastAPI()

# In-memory storage (replace with database for production)
tokens = {}

# Jira OAuth 2.0 Credentials
CLIENT_ID = ""
CLIENT_SECRET = ""
REDIRECT_URI = "http://localhost:8000/auth/jira/callback"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
RESOURCE_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

JIRA_BASE_URL = "JIRA_BASE_URL"
EMAIL = "EMAIL"
API_TOKEN = "API_TOKEN"

# Redirect user to Jira authorization URL
@app.get("/auth/jira")
def auth_jira():
    auth_url = (
        f"https://auth.atlassian.com/authorize"
        f"?audience=api.atlassian.com"
        f"&client_id={CLIENT_ID}"
        f"&scope=read:jira-user write:jira-work read:jira-work offline_access"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state=random_state_string"
        f"&response_type=code"
        f"&prompt=consent"
    )
    return {"redirect_url": auth_url}

# Handle Jira OAuth callback
@app.get("/auth/jira/callback")
def jira_oauth_callback(request: Request, code: str, state: str):
    # Exchange authorization code for access token
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(TOKEN_URL, json=data)
    token_data = response.json()

    print(token_data)

    if "access_token" in token_data:
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        
        # Store tokens (Replace with database storage)
        tokens["access_token"] = access_token
        tokens["refresh_token"] = refresh_token

        return {"message": "Authorization successful!", "access_token": access_token, "refresh_token": refresh_token, "token_data": token_data}
    else:
        return {"error": "Failed to get access token", "details": token_data}


# Refresh access token when expired
@app.get("/auth/jira/refresh")
def refresh_token():
    if "refresh_token" not in tokens:
        return {"error": "No refresh token available. Re-authenticate first."}

    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
    }

    response = requests.post(TOKEN_URL, json=data)
    token_data = response.json()

    if "access_token" in token_data:
        tokens["access_token"] = token_data["access_token"]
        tokens["refresh_token"] = token_data["refresh_token"]  # Update stored refresh token
        return {"message": "Access token refreshed", "new_access_token": token_data["access_token"], "token_data": token_data}
    else:
        return {"error": "Failed to refresh token", "details": token_data}

# Fetch Jira projects
@app.get("/projects")
def get_projects():
    project_fetch_url = f"{JIRA_BASE_URL}/2/project"

    bear_token = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode("utf-8")).decode('utf-8')
    print(bear_token)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {bear_token}"
    }

    response = requests.get(project_fetch_url, headers=headers)

    if response.status_code == 200:
        projects = response.json()
        return {"projects": projects}
    else:
        return {"error": "Failed to fetch projects", "status_code": response.status_code}

# Create a new Jira issue
@app.post("/issues")
def create_issue():
    issue_creation_url = f"{JIRA_BASE_URL}/2/issue"
    bear_token = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode("utf-8")).decode('utf-8')

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {bear_token}"
    }

    issue_data = {
        "fields": {
            "project": {"key": "MBA"},
            "summary": "New Issue Summary",
            "description": "Issue description",
            "issuetype": {"name": "Task"},
            "labels": ["BUG"],
        }
    }

    response = requests.post(issue_creation_url, headers=headers, json=issue_data)
    print(response.json())
    if response.status_code == 201:
        issue = response.json()
        return {"message": "Issue created successfully", "issue": issue}
    else:
        return {"error": "Failed to create issue", "status_code": response.status_code}

@app.get("/issue_types")
def get_issue_types():
    issue_type_fetch_url = f"{JIRA_BASE_URL}/2/issue/createmeta?projectKeys=MBA&expand=projects.issuetypes"
    bear_token = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode("utf-8")).decode('utf-8')
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {bear_token}"
    }

    response = requests.get(issue_type_fetch_url, headers=headers)
    if response.status_code == 200:
        issue_types = response.json()
        return issue_types
    else:
        return {"error": "Failed to fetch issue types", "status_code": response.status_code}

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
