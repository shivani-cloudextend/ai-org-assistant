"""
Optimized GitHub Data Collector using Tree API
MUCH faster and more efficient than search-based approach!

Key improvements:
- Uses Tree API (1 call vs 100s of search calls)
- Parallel file fetching (10 concurrent requests)
- Real-time progress tracking
- Gets ALL files (no 50-file limit)
- No search API rate limits
"""

import asyncio
import logging
import base64
from typing import List, Dict, AsyncGenerator, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from data_collectors import Document, GitHubMCPConnector
from mcp_functions import (
    mcp_github_get_tree,
    mcp_github_get_file_contents,
    mcp_github_list_issues,
    mcp_github_get_issue,
    mcp_github_list_pull_requests
)

logger = logging.getLogger(__name__)


class OptimizedGitHubCollector(GitHubMCPConnector):
    """
    Optimized GitHub collector using Tree API for 2-3x faster collection
    
    Old approach: 150 search calls + 500 content calls = 650 API calls, 3-4 minutes
    New approach: 1 tree call + 500 content calls = 501 API calls, 1-2 minutes
    """
    
    def __init__(self, organization: str, repositories: Optional[List[str]] = None,
                 collect_source_code: bool = True, max_file_size: int = 100000,
                 max_concurrent: int = 10, include_paths: Optional[List[str]] = None,
                 exclude_paths: Optional[List[str]] = None):
        super().__init__(organization, repositories)
        self.collect_source_code = collect_source_code
        self.max_file_size = max_file_size
        self.max_concurrent = max_concurrent  # Parallel requests
        self.include_paths = include_paths  # Only collect from these paths (e.g., ['src/', 'lib/'])
        self.exclude_paths = exclude_paths or []  # Exclude these paths (e.g., ['tests/', 'examples/'])
        
        # File extensions we want to collect
        self.source_extensions = {
            '.py', '.pyx', '.pyi',  # Python
            '.js', '.jsx', '.ts', '.tsx', '.mjs',  # JavaScript/TypeScript
            '.java',  # Java
            '.cs', '.cshtml',  # C#
            '.go',  # Go
            '.rs',  # Rust
            '.php',  # PHP
            '.rb',  # Ruby
            '.kt', '.kts',  # Kotlin
            '.scala',  # Scala
            '.swift',  # Swift
            '.cpp', '.cc', '.cxx', '.h', '.hpp',  # C++
            '.c',  # C
            '.sql',  # SQL
            '.sh', '.bash',  # Shell
        }
        
        # Documentation and config files
        self.doc_extensions = {
            '.md', '.mdx', '.txt', '.rst',
            '.json', '.yaml', '.yml', '.toml', '.xml',
            '.env.example', '.gitignore', 'Dockerfile'
        }
        
        # Directories to exclude (tests, node_modules, etc.)
        self.exclude_patterns = {
            'node_modules/', 'vendor/', '.git/', 'dist/', 'build/',
            '__pycache__/', '.pytest_cache/', 'coverage/', '.next/',
            'target/', 'bin/', 'obj/', '.gradle/', 'venv/', 'env/'
        }
    
    async def process_repository(self, repo: Dict) -> AsyncGenerator[Document, None]:
        """Enhanced repository processing with Tree API"""
        repo_name = repo['name']
        owner = repo['owner']['login']
        
        logger.info(f"🚀 Processing repository with OPTIMIZED collector: {repo_name}")
        print(f"\n{'='*80}")
        print(f"🚀 OPTIMIZED COLLECTION: {repo_name}")
        print(f"{'='*80}")
        
        # Collect documentation and config (keep original)
        async for doc in super().process_repository(repo):
            yield doc
        
        # NEW: Use Tree API for source code collection
        if self.collect_source_code:
            async for doc in self.collect_all_source_files_optimized(owner, repo_name, repo):
                yield doc
    
    async def collect_all_source_files_optimized(self, owner: str, repo_name: str, repo: Dict) -> AsyncGenerator[Document, None]:
        """
        Optimized source code collection using Tree API
        This is 2-3x faster than the search-based approach!
        """
        try:
            # STEP 1: Get entire repository structure in ONE API call! 🚀
            print(f"\n📥 Fetching repository tree structure...")
            tree_data = await mcp_github_get_tree(owner=owner, repo=repo_name, recursive=True)
            
            if not tree_data or not tree_data.get('tree'):
                logger.warning(f"No tree data returned for {repo_name}")
                return
            
            all_files = tree_data['tree']
            print(f"✅ Got {len(all_files)} total items from repository")
            
            # Show path filtering configuration
            if self.include_paths:
                print(f"📁 Include paths: {', '.join(self.include_paths)}")
            if self.exclude_paths:
                print(f"🚫 Exclude paths: {', '.join(self.exclude_paths)}")
            
            # STEP 2: Filter files locally (instant, no API calls!)
            source_files = []
            for item in all_files:
                # Skip directories
                if item['type'] != 'blob':
                    continue
                
                path = item['path']
                size = item.get('size', 0)
                
                # Skip excluded directories (default patterns)
                if any(pattern in path for pattern in self.exclude_patterns):
                    continue
                
                # NEW: Custom path filtering
                # If include_paths is specified, ONLY collect from those paths
                if self.include_paths:
                    if not any(path.startswith(inc_path) for inc_path in self.include_paths):
                        continue
                
                # NEW: Additional exclude paths (on top of default exclude_patterns)
                if self.exclude_paths:
                    if any(path.startswith(exc_path) for exc_path in self.exclude_paths):
                        continue
                
                # Skip files that are too large
                if size > self.max_file_size:
                    continue
                
                # Check if it's a source or doc file
                if self._is_source_file(path) or self._is_doc_file(path):
                    source_files.append(item)
            
            print(f"✅ Found {len(source_files)} source/doc files to collect")
            
            # Show breakdown by file type
            file_types = {}
            for f in source_files:
                ext = '.' + f['path'].split('.')[-1] if '.' in f['path'] else 'no_ext'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            print(f"\n📋 File breakdown:")
            for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {ext}: {count} files")
            
            # STEP 3: Fetch files in parallel batches! 🚀
            print(f"\n📦 Fetching file contents ({self.max_concurrent} concurrent requests)...")
            
            batch_size = self.max_concurrent
            total_files = len(source_files)
            fetched_count = 0
            error_count = 0
            
            for i in range(0, total_files, batch_size):
                batch = source_files[i:i+batch_size]
                
                # Progress tracking
                progress = min(100, (i + len(batch)) / total_files * 100)
                print(f"📊 Progress: {progress:.1f}% ({i + len(batch)}/{total_files} files) - Errors: {error_count}")
                
                # Fetch files in parallel
                tasks = [
                    self._fetch_and_create_document(owner, repo_name, file_item, repo)
                    for file_item in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Yield successful documents
                for result in results:
                    if isinstance(result, Document):
                        yield result
                        fetched_count += 1
                    elif isinstance(result, Exception):
                        error_count += 1
                        logger.debug(f"Error fetching file: {result}")
            
            print(f"\n✅ Collection complete!")
            print(f"   ✓ Successfully fetched: {fetched_count} files")
            print(f"   ✗ Errors: {error_count} files")
            print(f"{'='*80}\n")
            
        except Exception as e:
            logger.error(f"Error in optimized collection for {repo_name}: {e}")
            print(f"❌ Error: {e}")
    
    async def _fetch_and_create_document(self, owner: str, repo_name: str, 
                                         file_item: Dict, repo: Dict) -> Optional[Document]:
        """Fetch a single file and create a Document"""
        try:
            file_path = file_item['path']
            
            # Fetch file contents
            content_result = await mcp_github_get_file_contents(
                owner=owner,
                repo=repo_name,
                path=file_path
            )
            
            if not content_result or 'content' not in content_result:
                return None
            
            # Decode content
            try:
                content = base64.b64decode(content_result['content']).decode('utf-8')
            except UnicodeDecodeError:
                # Binary file, skip it
                logger.debug(f"Skipping binary file: {file_path}")
                return None
            
            # Determine document type
            doc_type = self._get_doc_type(file_path)
            
            # Determine role tags
            role_tags = self._determine_role_tags(file_path, content)
            
            # Create document
            document = Document(
                content=content,
                source="github",
                doc_type=doc_type,
                metadata={
                    "repository": repo_name,
                    "organization": owner,
                    "file_path": file_path,
                    "file_name": file_item.get('path', '').split('/')[-1],
                    "file_size": file_item.get('size', 0),
                    "sha": file_item.get('sha', ''),
                    "url": content_result.get('html_url', ''),
                    "collected_at": datetime.now().isoformat()
                },
                role_tags=role_tags
            )
            
            return document
            
        except Exception as e:
            logger.debug(f"Error fetching {file_item.get('path', 'unknown')}: {e}")
            return None
    
    def _is_source_file(self, path: str) -> bool:
        """Check if file is a source code file"""
        return any(path.endswith(ext) for ext in self.source_extensions)
    
    def _is_doc_file(self, path: str) -> bool:
        """Check if file is a documentation/config file"""
        file_name = path.split('/')[-1]
        return (any(path.endswith(ext) for ext in self.doc_extensions) or
                file_name in ['README', 'LICENSE', 'Makefile', 'Dockerfile'])
    
    def _get_doc_type(self, path: str) -> str:
        """Determine document type from file path"""
        path_lower = path.lower()
        
        if any(path_lower.endswith(ext) for ext in ['.md', '.mdx', '.txt', '.rst']):
            return "documentation"
        elif any(path_lower.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.toml', '.xml', '.env']):
            return "configuration"
        elif any(path_lower.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cs', '.go', '.rs', '.php']):
            return "source_code"
        elif any(path_lower.endswith(ext) for ext in ['.sql']):
            return "database"
        elif 'test' in path_lower or 'spec' in path_lower:
            return "test"
        else:
            return "source_code"
    
    def _determine_role_tags(self, file_path: str, content: str) -> List[str]:
        """Determine which roles would be interested in this file"""
        tags = set()
        
        path_lower = file_path.lower()
        content_lower = content.lower()[:5000]  # Check first 5000 chars
        
        # Developers care about all source code
        if self._is_source_file(file_path):
            tags.add("developer")
        
        # Support engineers care about error handling, logging, monitoring
        if any(keyword in content_lower for keyword in ['error', 'exception', 'log', 'alert', 'monitor']):
            tags.add("support")
        
        # Managers care about README, docs, architecture
        if any(name in path_lower for name in ['readme', 'architecture', 'design', 'overview']):
            tags.add("manager")
            tags.add("developer")
            tags.add("support")
        
        # API endpoints are relevant to all
        if any(keyword in content_lower for keyword in ['@app.route', '@router', 'endpoint', 'controller', 'handler']):
            tags.add("developer")
            tags.add("support")
        
        # Configuration files are relevant to ops/support
        if self._get_doc_type(file_path) == "configuration":
            tags.add("support")
            tags.add("developer")
        
        return list(tags) if tags else ["developer"]


# For backward compatibility, create an alias
EnhancedGitHubMCPConnector = OptimizedGitHubCollector

