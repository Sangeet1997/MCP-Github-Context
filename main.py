import os
import requests
import base64
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Github Extractor")

def fetch_github_content(github_url):
    """
    Fetches content from a GitHub URL.
    If the URL points to a single file, returns the content of that file.
    If the URL points to a repository, returns the combined content of all files.
    """
    # Parse the GitHub URL
    parsed_url = urlparse(github_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    # Check if it's a valid GitHub URL
    if parsed_url.netloc != 'github.com' or len(path_parts) < 2:
        return "Invalid GitHub URL"
    
    # Extract owner and repo
    owner = path_parts[0]
    repo = path_parts[1]
    
    # Determine if it's a file URL or a repository URL
    is_file_url = len(path_parts) > 4 and path_parts[2] == 'blob'
    
    if is_file_url:
        # For a single file
        file_path = '/'.join(path_parts[4:])
        return fetch_file_content(owner, repo, file_path)
    else:
        # For a repository
        return fetch_repository_content(owner, repo)

def is_text_file(file_path):
    """Check if the file extension is likely to be a text file"""
    text_extensions = [
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv',
        '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf', '.sh', '.bat',
        '.sql', '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.ts',
        '.jsx', '.tsx', '.vue', '.rb', '.php', '.pl', '.kt', '.swift',
        '.gitignore', '.env', '.lock', '.config', '.r', '.scala'
    ]
    
    # Check if file has any of the text extensions
    _, ext = os.path.splitext(file_path.lower())
    return ext in text_extensions or ext == ''

def fetch_file_content(owner, repo, file_path):
    """Fetches content of a specific file from GitHub"""
    # Skip non-text files
    if not is_text_file(file_path):
        return f"Skipped binary file: {file_path}"
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    response = requests.get(api_url)
    
    if response.status_code != 200:
        return f"Error fetching file: {response.status_code}"
    
    file_data = response.json()
    if 'content' not in file_data:
        return "No content found in file"
    
    # GitHub API returns content in base64, we need to decode it
    try:
        content = base64.b64decode(file_data['content']).decode('utf-8')
        return content
    except UnicodeDecodeError:
        return f"Skipped binary or non-UTF-8 file: {file_path}"

def fetch_repository_content(owner, repo):
    """Fetches and combines content of all files in a repository"""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    response = requests.get(api_url)
    
    if response.status_code != 200:
        # Try with 'master' branch if 'main' fails
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            return f"Error fetching repository structure: {response.status_code}"
    
    repo_data = response.json()
    if 'tree' not in repo_data:
        return "No files found in repository"
    
    all_content = []
    
    for item in repo_data['tree']:
        if item['type'] == 'blob':  # Only process files, not directories
            file_path = item['path']
            # Only process text files based on extension
            if is_text_file(file_path):
                try:
                    file_content = fetch_file_content(owner, repo, file_path)
                    all_content.append(f"--- File: {file_path} ---\n{file_content}\n")
                except Exception as e:
                    all_content.append(f"--- File: {file_path} ---\nError: {str(e)}\n")
    
    return "\n".join(all_content)

@mcp.tool()
def github_context(url: str):
    return fetch_github_content(url)
