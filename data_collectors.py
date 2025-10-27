"""
Data Collection Modules for AI Organization Assistant
Handles data ingestion from GitHub (MCP), Confluence, and Jira
"""

import asyncio
import logging
from typing import List, Dict, AsyncGenerator, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from bs4 import BeautifulSoup
from atlassian import Confluence, Jira

# Import MCP function implementations
from mcp_functions import (
    mcp_github_search_repositories,
    mcp_github_get_file_contents,
    mcp_github_search_code,
    mcp_github_list_issues,
    mcp_github_get_issue,
    mcp_github_list_pull_requests
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Represents a processed document from any source"""
    content: str
    source: str  # 'github', 'confluence', 'jira'
    doc_type: str  # 'documentation', 'code', 'issue', 'ticket'
    role_tags: List[str]  # ['developer', 'support', 'manager']
    metadata: Dict
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GitHubMCPConnector:
    """Handles GitHub data collection using MCP functions"""
    
    def __init__(self, organization: str, repositories: Optional[List[str]] = None):
        self.organization = organization
        self.repositories = repositories or []
    
    async def collect_all_data(self) -> AsyncGenerator[Document, None]:
        """Main entry point for GitHub data collection"""
        logger.info(f"Starting GitHub data collection for org: {self.organization}")
        
        # Get all repositories if none specified
        if not self.repositories:
            repos = await self.discover_repositories()
        else:
            repos = [{'name': repo, 'owner': {'login': self.organization}} for repo in self.repositories]
        
        logger.info(f"Found {len(repos)} repositories to process")
        
        # Process each repository
        for repo in repos:
            async for document in self.process_repository(repo):
                yield document
    
    async def discover_repositories(self) -> List[Dict]:
        """Discover all repositories in the organization"""
        try:
            # Using MCP GitHub search
            search_result = await mcp_github_search_repositories(
                query=f"org:{self.organization}",
                per_page=100
            )
            return search_result.get('items', [])
        except Exception as e:
            logger.error(f"Error discovering repositories: {e}")
            return []
    
    async def process_repository(self, repo: Dict) -> AsyncGenerator[Document, None]:
        """Process a single repository for all types of content"""
        repo_name = repo['name']
        owner = repo['owner']['login']
        
        logger.info(f"Processing repository: {repo_name}")
        
        # Collect documentation files
        async for doc in self.collect_documentation(owner, repo_name, repo):
            yield doc
        
        # Collect configuration and setup files
        async for doc in self.collect_config_files(owner, repo_name, repo):
            yield doc
        
        # Collect issues and PRs
        async for doc in self.collect_issues_and_prs(owner, repo_name, repo):
            yield doc
        
        # Search for specific patterns in code
        async for doc in self.collect_code_with_patterns(owner, repo_name, repo):
            yield doc
    
    async def collect_documentation(self, owner: str, repo_name: str, repo: Dict) -> AsyncGenerator[Document, None]:
        """Collect documentation files from repository"""
        doc_files = [
            'README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE',
            'ARCHITECTURE.md', 'API.md', 'DEPLOYMENT.md', 'TROUBLESHOOTING.md',
            'docs/README.md', 'documentation/index.md', '.github/README.md'
        ]
        
        for file_path in doc_files:
            try:
                content_result = await mcp_github_get_file_contents(
                    owner=owner,
                    repo=repo_name,
                    path=file_path
                )
                
                if content_result and 'content' in content_result:
                    # Decode base64 content
                    import base64
                    content = base64.b64decode(content_result['content']).decode('utf-8')
                    
                    document = Document(
                        content=content,
                        source='github',
                        doc_type='documentation',
                        role_tags=self.determine_doc_role_tags(file_path, content),
                        metadata={
                            'repository': repo_name,
                            'file_path': file_path,
                            'owner': owner,
                            'language': repo.get('language'),
                            'size': content_result.get('size', 0),
                            'sha': content_result.get('sha'),
                            'url': content_result.get('html_url')
                        },
                        updated_at=datetime.fromisoformat(content_result.get('updated_at', '').replace('Z', '+00:00')) if content_result.get('updated_at') else None
                    )
                    
                    logger.debug(f"Collected documentation: {repo_name}/{file_path}")
                    yield document
                    
            except Exception as e:
                logger.debug(f"Could not fetch {file_path} from {repo_name}: {e}")
                continue
    
    async def collect_config_files(self, owner: str, repo_name: str, repo: Dict) -> AsyncGenerator[Document, None]:
        """Collect configuration and setup files"""
        config_patterns = [
            'package.json', 'requirements.txt', 'Dockerfile', 'docker-compose.yml',
            '.env.example', 'config.yml', 'setup.py', 'pom.xml', 'build.gradle'
        ]
        
        for pattern in config_patterns:
            try:
                # Search for files matching the pattern
                search_result = await mcp_github_search_code(
                    q=f"filename:{pattern} repo:{owner}/{repo_name}"
                )
                
                for item in search_result.get('items', []):
                    content_result = await mcp_github_get_file_contents(
                        owner=owner,
                        repo=repo_name,
                        path=item['path']
                    )
                    
                    if content_result and 'content' in content_result:
                        import base64
                        content = base64.b64decode(content_result['content']).decode('utf-8')
                        
                        document = Document(
                            content=content,
                            source='github',
                            doc_type='configuration',
                            role_tags=['developer'],  # Config files are primarily for developers
                            metadata={
                                'repository': repo_name,
                                'file_path': item['path'],
                                'owner': owner,
                                'language': repo.get('language'),
                                'config_type': self.classify_config_file(item['path'])
                            }
                        )
                        
                        logger.debug(f"Collected config file: {repo_name}/{item['path']}")
                        yield document
                        
            except Exception as e:
                logger.debug(f"Could not search for {pattern} in {repo_name}: {e}")
                continue
    
    async def collect_issues_and_prs(self, owner: str, repo_name: str, repo: Dict) -> AsyncGenerator[Document, None]:
        """Collect issues and pull requests"""
        try:
            # Get issues (includes PRs in GitHub API)
            issues = await mcp_github_list_issues(
                owner=owner,
                repo=repo_name,
                state='all',
                per_page=100
            )
            
            for issue in issues:
                # Get detailed issue information
                issue_detail = await mcp_github_get_issue(
                    owner=owner,
                    repo=repo_name,
                    issue_number=issue['number']
                )
                
                # Combine title, body, and comments
                content_parts = [
                    f"Title: {issue_detail['title']}",
                    f"Body: {issue_detail.get('body', 'No description provided.')}"
                ]
                
                # Add comments if any
                if issue_detail.get('comments', 0) > 0:
                    # Note: In real implementation, you'd fetch comments separately
                    content_parts.append("Comments: [Comments would be fetched separately]")
                
                content = "\n\n".join(content_parts)
                
                document = Document(
                    content=content,
                    source='github',
                    doc_type='pull_request' if 'pull_request' in issue_detail else 'issue',
                    role_tags=self.determine_issue_role_tags(issue_detail.get('labels', [])),
                    metadata={
                        'repository': repo_name,
                        'issue_number': issue_detail['number'],
                        'owner': owner,
                        'state': issue_detail['state'],
                        'labels': [label['name'] for label in issue_detail.get('labels', [])],
                        'assignees': [assignee['login'] for assignee in issue_detail.get('assignees', [])],
                        'milestone': issue_detail.get('milestone', {}).get('title') if issue_detail.get('milestone') else None
                    },
                    created_at=datetime.fromisoformat(issue_detail['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(issue_detail['updated_at'].replace('Z', '+00:00'))
                )
                
                logger.debug(f"Collected issue/PR: {repo_name}#{issue_detail['number']}")
                yield document
                
        except Exception as e:
            logger.error(f"Error collecting issues from {repo_name}: {e}")
    
    async def collect_code_with_patterns(self, owner: str, repo_name: str, repo: Dict) -> AsyncGenerator[Document, None]:
        """Search for specific patterns in code that might be useful for documentation"""
        search_patterns = [
            'error handling',
            'configuration',
            'setup',
            'deployment',
            'authentication',
            'troubleshooting',
            'TODO',
            'FIXME'
        ]
        
        for pattern in search_patterns:
            try:
                search_result = await mcp_github_search_code(
                    q=f'"{pattern}" repo:{owner}/{repo_name}',
                    per_page=20  # Limit to avoid too much noise
                )
                
                for item in search_result.get('items', []):
                    # Skip if file is too large
                    if item.get('size', 0) > 50000:  # 50KB limit
                        continue
                    
                    content_result = await mcp_github_get_file_contents(
                        owner=owner,
                        repo=repo_name,
                        path=item['path']
                    )
                    
                    if content_result and 'content' in content_result:
                        import base64
                        content = base64.b64decode(content_result['content']).decode('utf-8')
                        
                        # Extract relevant sections around the pattern
                        relevant_content = self.extract_relevant_sections(content, pattern)
                        
                        document = Document(
                            content=relevant_content,
                            source='github',
                            doc_type='code',
                            role_tags=self.determine_code_role_tags(item['path'], content, pattern),
                            metadata={
                                'repository': repo_name,
                                'file_path': item['path'],
                                'owner': owner,
                                'language': repo.get('language'),
                                'search_pattern': pattern,
                                'file_type': item['path'].split('.')[-1] if '.' in item['path'] else 'unknown'
                            }
                        )
                        
                        logger.debug(f"Collected code pattern '{pattern}': {repo_name}/{item['path']}")
                        yield document
                        
            except Exception as e:
                logger.debug(f"Could not search for pattern '{pattern}' in {repo_name}: {e}")
                continue
    
    def determine_doc_role_tags(self, file_path: str, content: str) -> List[str]:
        """Determine role tags based on documentation content"""
        file_path_lower = file_path.lower()
        content_lower = content.lower()
        
        role_tags = []
        
        # Developer-focused documentation
        dev_keywords = ['api', 'sdk', 'architecture', 'deployment', 'configuration', 
                       'setup', 'installation', 'build', 'compile', 'development']
        if any(keyword in file_path_lower or keyword in content_lower for keyword in dev_keywords):
            role_tags.append('developer')
        
        # Support-focused documentation  
        support_keywords = ['troubleshooting', 'faq', 'help', 'support', 'error', 
                           'problem', 'solution', 'guide', 'how-to']
        if any(keyword in file_path_lower or keyword in content_lower for keyword in support_keywords):
            role_tags.append('support')
        
        # Default to both if it's general documentation
        if not role_tags:
            role_tags = ['developer', 'support']
        
        return role_tags
    
    def determine_issue_role_tags(self, labels: List[Dict]) -> List[str]:
        """Determine role tags based on GitHub issue labels"""
        label_names = [label['name'].lower() for label in labels]
        
        role_tags = []
        
        # Developer-focused labels
        dev_labels = ['bug', 'enhancement', 'feature', 'technical-debt', 'architecture', 'performance']
        if any(label in label_names for label in dev_labels):
            role_tags.append('developer')
        
        # Support-focused labels
        support_labels = ['support', 'question', 'help-wanted', 'documentation', 'user-experience']
        if any(label in label_names for label in support_labels):
            role_tags.append('support')
        
        # Default to both if no specific labels
        if not role_tags:
            role_tags = ['developer', 'support']
        
        return role_tags
    
    def determine_code_role_tags(self, file_path: str, content: str, pattern: str) -> List[str]:
        """Determine role tags for code files based on content and patterns"""
        role_tags = []
        
        # Generally code is for developers, but some patterns might be useful for support
        role_tags.append('developer')
        
        if pattern.lower() in ['error handling', 'troubleshooting', 'todo', 'fixme']:
            role_tags.append('support')
        
        return role_tags
    
    def classify_config_file(self, file_path: str) -> str:
        """Classify the type of configuration file"""
        if 'package.json' in file_path:
            return 'npm_package'
        elif 'requirements.txt' in file_path:
            return 'python_dependencies'
        elif 'Dockerfile' in file_path:
            return 'docker_config'
        elif '.env' in file_path:
            return 'environment_config'
        else:
            return 'general_config'
    
    def extract_relevant_sections(self, content: str, pattern: str) -> str:
        """Extract relevant sections around a search pattern"""
        lines = content.split('\n')
        relevant_lines = []
        
        for i, line in enumerate(lines):
            if pattern.lower() in line.lower():
                # Include context: 5 lines before and after
                start = max(0, i - 5)
                end = min(len(lines), i + 6)
                context = lines[start:end]
                relevant_lines.extend(context)
                relevant_lines.append("---")  # Separator
        
        return '\n'.join(relevant_lines)


class ConfluenceConnector:
    """Handles Confluence data collection"""
    
    def __init__(self, url: str, username: str, api_token: str, space_keys: List[str]):
        self.confluence = Confluence(
            url=url,
            username=username,
            password=api_token
        )
        self.space_keys = space_keys
    
    async def collect_all_data(self) -> AsyncGenerator[Document, None]:
        """Main entry point for Confluence data collection"""
        logger.info(f"Starting Confluence data collection for spaces: {self.space_keys}")
        
        for space_key in self.space_keys:
            async for document in self.process_space(space_key):
                yield document
    
    async def process_space(self, space_key: str) -> AsyncGenerator[Document, None]:
        """Process all pages in a Confluence space"""
        try:
            pages = self.confluence.get_all_pages_from_space(
                space=space_key,
                start=0,
                limit=1000,
                expand='body.storage,metadata.labels,version,ancestors'
            )
            
            logger.info(f"Found {len(pages)} pages in space {space_key}")
            
            for page in pages:
                try:
                    # Get detailed page content
                    page_detail = self.confluence.get_page_by_id(
                        page_id=page['id'],
                        expand='body.storage,metadata.labels,version,ancestors'
                    )
                    
                    # Extract clean text from HTML
                    clean_content = self.extract_clean_content(page_detail['body']['storage']['value'])
                    
                    document = Document(
                        content=clean_content,
                        source='confluence',
                        doc_type='documentation',
                        role_tags=self.determine_confluence_role_tags(page_detail),
                        metadata={
                            'page_id': page['id'],
                            'title': page['title'],
                            'space_key': space_key,
                            'labels': [label['name'] for label in page_detail.get('metadata', {}).get('labels', {}).get('results', [])],
                            'creator': page_detail['version']['by']['displayName'],
                            'url': f"{self.confluence.url}/pages/viewpage.action?pageId={page['id']}"
                        },
                        created_at=datetime.fromisoformat(page_detail['version']['when'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(page_detail['version']['when'].replace('Z', '+00:00'))
                    )
                    
                    logger.debug(f"Collected Confluence page: {page['title']}")
                    yield document
                    
                except Exception as e:
                    logger.error(f"Error processing page {page.get('title', page.get('id'))}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing Confluence space {space_key}: {e}")
    
    def extract_clean_content(self, html_content: str) -> str:
        """Extract clean text from Confluence HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def determine_confluence_role_tags(self, page_detail: Dict) -> List[str]:
        """Determine role tags based on page content and labels"""
        labels = [label['name'].lower() for label in page_detail.get('metadata', {}).get('labels', {}).get('results', [])]
        title = page_detail['title'].lower()
        
        role_tags = []
        
        # Developer-focused content
        dev_keywords = ['api', 'sdk', 'technical', 'architecture', 'deployment', 
                       'development', 'integration', 'hld', 'lld', 'design']
        if any(keyword in title or keyword in labels for keyword in dev_keywords):
            role_tags.append('developer')
        
        # Support-focused content  
        support_keywords = ['troubleshooting', 'support', 'faq', 'help', 'issue', 
                           'problem', 'solution', 'guide', 'howto', 'user']
        if any(keyword in title or keyword in labels for keyword in support_keywords):
            role_tags.append('support')
        
        # Manager-focused content
        manager_keywords = ['process', 'policy', 'meeting', 'decision', 'roadmap', 'planning']
        if any(keyword in title or keyword in labels for keyword in manager_keywords):
            role_tags.append('manager')
        
        # Default to both developer and support if unclear
        if not role_tags:
            role_tags = ['developer', 'support']
            
        return role_tags


# Example usage and testing
async def main():
    """Example usage of the data collectors"""
    
    # GitHub data collection
    github_collector = GitHubMCPConnector(
        organization="your-org",
        repositories=["repo1", "repo2"]  # Optional: specify repos
    )
    
    github_docs = []
    async for document in github_collector.collect_all_data():
        github_docs.append(document)
        if len(github_docs) >= 5:  # Limit for testing
            break
    
    print(f"Collected {len(github_docs)} documents from GitHub")
    
    # Confluence data collection (commented out as it requires real credentials)
    # confluence_collector = ConfluenceConnector(
    #     url="https://yourorg.atlassian.net",
    #     username="your-email@company.com", 
    #     api_token="your-api-token",
    #     space_keys=["DEV", "SUPPORT"]
    # )
    # 
    # confluence_docs = []
    # async for document in confluence_collector.collect_all_data():
    #     confluence_docs.append(document)
    # 
    # print(f"Collected {len(confluence_docs)} documents from Confluence")

if __name__ == "__main__":
    asyncio.run(main())
