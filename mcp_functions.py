"""
MCP Function Implementations using PyGithub
These functions replace the MCP server calls with direct PyGithub implementations
"""

import os
import base64
from github import Github
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize GitHub client globally
_github_token = None
_github_client = None

def _get_github_client():
    """Get or create GitHub client"""
    global _github_client, _github_token
    
    if _github_client is None:
        if _github_token is None:
            _github_token = os.getenv("GITHUB_TOKEN")
        
        if not _github_token:
            raise ValueError("GITHUB_TOKEN environment variable not set")
        _github_client = Github(_github_token)
    return _github_client

async def mcp_github_search_repositories(query: str, per_page: int = 30, page: int = 1) -> Dict:
    """Search for GitHub repositories"""
    try:
        g = _get_github_client()
        
        # Parse the query to extract org
        if "org:" in query:
            org_name = query.split("org:")[1].split()[0]
            try:
                org = g.get_organization(org_name)
                repos = list(org.get_repos())
            except:
                user = g.get_user(org_name)
                repos = list(user.get_repos())
            
            # Convert to format expected by the collectors
            items = []
            for repo in repos:
                items.append({
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'owner': {'login': repo.owner.login},
                    'description': repo.description,
                    'language': repo.language,
                    'size': repo.size,
                    'stargazers_count': repo.stargazers_count,
                    'html_url': repo.html_url
                })
            
            return {'items': items, 'total_count': len(items)}
        
        return {'items': [], 'total_count': 0}
        
    except Exception as e:
        print(f"Error in mcp_github_search_repositories: {e}")
        return {'items': [], 'total_count': 0}

async def mcp_github_get_file_contents(owner: str, repo: str, path: str, branch: Optional[str] = None) -> Optional[Dict]:
    """Get file contents from a GitHub repository"""
    try:
        g = _get_github_client()
        repository = g.get_repo(f"{owner}/{repo}")
        
        try:
            file_content = repository.get_contents(path, ref=branch if branch else repository.default_branch)
            
            if file_content.type == "file":
                return {
                    'content': file_content.content,  # Already base64 encoded
                    'encoding': 'base64',
                    'size': file_content.size,
                    'name': file_content.name,
                    'path': file_content.path,
                    'sha': file_content.sha,
                    'html_url': file_content.html_url,
                    'download_url': file_content.download_url
                }
            return None
        except:
            return None
            
    except Exception as e:
        print(f"Error in mcp_github_get_file_contents: {e}")
        return None

async def mcp_github_search_code(q: str, per_page: int = 30, page: int = 1, sort: Optional[str] = None, order: Optional[str] = None) -> Dict:
    """Search for code in GitHub repositories"""
    try:
        g = _get_github_client()
        
        # Use GitHub's code search
        try:
            results = g.search_code(query=q, per_page=per_page)
            
            items = []
            for result in results[:per_page]:
                items.append({
                    'name': result.name,
                    'path': result.path,
                    'sha': result.sha,
                    'html_url': result.html_url,
                    'repository': {
                        'name': result.repository.name,
                        'full_name': result.repository.full_name,
                        'owner': {'login': result.repository.owner.login}
                    }
                })
            
            return {'items': items, 'total_count': len(items)}
        except:
            return {'items': [], 'total_count': 0}
            
    except Exception as e:
        print(f"Error in mcp_github_search_code: {e}")
        return {'items': [], 'total_count': 0}

async def mcp_github_list_issues(owner: str, repo: str, state: str = 'all', labels: Optional[List[str]] = None,
                                 per_page: int = 30, page: int = 1, since: Optional[str] = None,
                                 sort: Optional[str] = None, direction: Optional[str] = None) -> List[Dict]:
    """List issues from a GitHub repository"""
    try:
        g = _get_github_client()
        repository = g.get_repo(f"{owner}/{repo}")
        
        # Get issues
        issues = repository.get_issues(state=state, labels=labels if labels else [])
        
        result = []
        for issue in list(issues)[:per_page]:
            result.append({
                'number': issue.number,
                'title': issue.title,
                'body': issue.body,
                'state': issue.state,
                'labels': [{'name': label.name} for label in issue.labels],
                'created_at': issue.created_at.isoformat() if issue.created_at else None,
                'updated_at': issue.updated_at.isoformat() if issue.updated_at else None,
                'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
                'user': {'login': issue.user.login} if issue.user else None,
                'html_url': issue.html_url,
                'comments': issue.comments
            })
        
        return result
        
    except Exception as e:
        print(f"Error in mcp_github_list_issues: {e}")
        return []

async def mcp_github_get_issue(owner: str, repo: str, issue_number: int) -> Optional[Dict]:
    """Get a specific issue from a GitHub repository"""
    try:
        g = _get_github_client()
        repository = g.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(issue_number)
        
        return {
            'number': issue.number,
            'title': issue.title,
            'body': issue.body,
            'state': issue.state,
            'labels': [{'name': label.name} for label in issue.labels],
            'created_at': issue.created_at.isoformat() if issue.created_at else None,
            'updated_at': issue.updated_at.isoformat() if issue.updated_at else None,
            'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
            'user': {'login': issue.user.login} if issue.user else None,
            'html_url': issue.html_url,
            'comments': issue.comments
        }
        
    except Exception as e:
        print(f"Error in mcp_github_get_issue: {e}")
        return None

async def mcp_github_list_pull_requests(owner: str, repo: str, state: str = 'all', per_page: int = 30) -> List[Dict]:
    """List pull requests from a GitHub repository"""
    try:
        g = _get_github_client()
        repository = g.get_repo(f"{owner}/{repo}")
        
        pulls = repository.get_pulls(state=state)
        
        result = []
        for pr in list(pulls)[:per_page]:
            result.append({
                'number': pr.number,
                'title': pr.title,
                'body': pr.body,
                'state': pr.state,
                'created_at': pr.created_at.isoformat() if pr.created_at else None,
                'updated_at': pr.updated_at.isoformat() if pr.updated_at else None,
                'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
                'user': {'login': pr.user.login} if pr.user else None,
                'html_url': pr.html_url,
                'head': {'ref': pr.head.ref},
                'base': {'ref': pr.base.ref}
            })
        
        return result
        
    except Exception as e:
        print(f"Error in mcp_github_list_pull_requests: {e}")
        return []

async def mcp_github_get_tree(owner: str, repo: str, branch: Optional[str] = None, recursive: bool = True) -> Dict:
    """
    Get repository tree structure using GitHub Tree API
    This is MUCH more efficient than searching - gets all files in ONE API call!
    
    Returns:
        Dict with 'tree' key containing list of all files:
        {
            'sha': 'abc123',
            'tree': [
                {'path': 'src/main.ts', 'type': 'blob', 'size': 1234, 'sha': '...'},
                {'path': 'lib/utils.js', 'type': 'blob', 'size': 567, 'sha': '...'},
                ...
            ]
        }
    """
    try:
        g = _get_github_client()
        repository = g.get_repo(f"{owner}/{repo}")
        
        # Get the branch SHA
        if branch is None:
            branch = repository.default_branch
        
        branch_obj = repository.get_branch(branch)
        sha = branch_obj.commit.sha
        
        # Get the tree (recursive=True gets ALL files in one call!)
        tree = repository.get_git_tree(sha=sha, recursive=recursive)
        
        # Convert to dict format
        result = {
            'sha': tree.sha,
            'tree': []
        }
        
        for item in tree.tree:
            result['tree'].append({
                'path': item.path,
                'type': item.type,  # 'blob' for files, 'tree' for directories
                'size': item.size if hasattr(item, 'size') else 0,
                'sha': item.sha,
                'url': item.url
            })
        
        return result
        
    except Exception as e:
        print(f"Error in mcp_github_get_tree: {e}")
        return {'sha': '', 'tree': []}

