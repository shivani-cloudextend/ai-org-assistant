# AI Organization Assistant - Detailed Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES LAYER                                    │
├─────────────────┬─────────────────────┬─────────────────────┬─────────────────────┤
│   GitHub MCP    │   Confluence API    │     Jira API       │   File System      │
│                 │                     │                     │                     │
│ • Repositories  │ • Pages/Spaces      │ • Issues/Projects  │ • Local Docs       │
│ • Issues/PRs    │ • Comments          │ • Comments         │ • Config Files     │
│ • Code Files    │ • Attachments       │ • Worklog          │                     │
│ • README/Docs   │ • Labels            │ • Resolution Notes │                     │
└─────────────────┴─────────────────────┴─────────────────────┴─────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   GitHub    │  │ Confluence  │  │    Jira     │  │   Scheduler &       │   │
│  │  Connector  │  │  Connector  │  │  Connector  │  │  Rate Limiter       │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT PROCESSING LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Content   │  │  Document   │  │   Metadata  │  │    Role-based       │   │
│  │   Parser    │  │  Chunker    │  │  Extractor  │  │   Classification    │   │
│  │             │  │             │  │             │  │                     │   │
│  │ • Code      │  │ • Semantic  │  │ • Source    │  │ • Developer Tags    │   │
│  │ • Markdown  │  │ • Sliding   │  │ • Author    │  │ • Support Tags      │   │
│  │ • HTML      │  │ • Overlap   │  │ • Date      │  │ • Document Type     │   │
│  │ • Plain     │  │ • Context   │  │ • Type      │  │ • Complexity Level  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       EMBEDDING & STORAGE LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Embedding   │  │   Vector    │  │  Metadata   │  │      Search         │   │
│  │  Engine     │  │  Database   │  │   Store     │  │     Index           │   │
│  │             │  │             │  │             │  │                     │   │
│  │ BGE-Large   │  │  ChromaDB   │  │ PostgreSQL  │  │ • Semantic Search   │   │
│  │ 1024 dim    │  │ Collections │  │ Relations   │  │ • Keyword Search    │   │
│  │             │  │ Similarity  │  │ JSONB       │  │ • Hybrid Search     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AI PROCESSING LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Query     │  │  Context    │  │ Role-based  │  │    Response         │   │
│  │ Processing  │  │ Retrieval   │  │   Prompt    │  │   Generation        │   │
│  │             │  │             │  │ Engineering │  │                     │   │
│  │ • Intent    │  │ • Similarity│  │             │  │ • GPT-4 Turbo       │   │
│  │ • Entities  │  │ • Reranking │  │ • Developer │  │ • Context Injection │   │
│  │ • Role      │  │ • Filtering │  │ • Support   │  │ • Citation          │   │
│  │ • Context   │  │ • Relevance │  │ • Manager   │  │ • Confidence Score  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           API & UI LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   REST API  │  │  WebSocket  │  │ Web UI      │  │   Authentication    │   │
│  │   FastAPI   │  │ Real-time   │  │ React       │  │   & Authorization   │   │
│  │             │  │ Streaming   │  │             │  │                     │   │
│  │ • /query    │  │ • Progress  │  │ • Chat UI   │  │ • JWT Tokens        │   │
│  │ • /feedback │  │ • Results   │  │ • History   │  │ • Role Management   │   │
│  │ • /health   │  │ • Errors    │  │ • Settings  │  │ • SSO Integration   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Collection Strategy

### 1. GitHub Data Collection (Using MCP)

#### Repository Structure Analysis
```python
async def collect_github_data():
    # Step 1: Discover all repositories
    repos = await mcp_github_search_repositories(
        query="org:your-org",
        per_page=100
    )
    
    for repo in repos:
        # Step 2: Get repository metadata
        repo_info = {
            'name': repo['name'],
            'description': repo['description'],
            'language': repo['language'],
            'topics': repo['topics'],
            'size': repo['size'],
            'stars': repo['stargazers_count']
        }
        
        # Step 3: Collect different types of content
        await collect_documentation_files(repo)
        await collect_code_files(repo)
        await collect_issues_and_prs(repo)
```

#### Documentation Files Collection
```python
async def collect_documentation_files(repo):
    doc_files = [
        'README.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
        'docs/', 'documentation/', '.github/',
        'API.md', 'ARCHITECTURE.md'
    ]
    
    for file_path in doc_files:
        try:
            content = await mcp_github_get_file_contents(
                owner=repo['owner']['login'],
                repo=repo['name'],
                path=file_path
            )
            
            document = {
                'content': content,
                'source': 'github',
                'type': 'documentation',
                'repository': repo['name'],
                'file_path': file_path,
                'role_tags': ['developer', 'support'],  # Both can benefit
                'metadata': {
                    'language': repo.get('language'),
                    'last_updated': content.get('updated_at'),
                    'size': len(content.get('content', ''))
                }
            }
            yield document
        except:
            continue  # File doesn't exist
```

#### Code Files Analysis
```python
async def collect_code_files(repo):
    # Search for specific patterns in code
    search_queries = [
        f"config repo:{repo['full_name']} language:{repo['language']}",
        f"deploy repo:{repo['full_name']}",
        f"setup repo:{repo['full_name']}",
        f"install repo:{repo['full_name']}",
        f"error repo:{repo['full_name']}",
        f"exception repo:{repo['full_name']}"
    ]
    
    for query in search_queries:
        code_results = await mcp_github_search_code(q=query)
        
        for result in code_results.get('items', []):
            # Get full file content
            full_content = await mcp_github_get_file_contents(
                owner=repo['owner']['login'],
                repo=repo['name'],
                path=result['path']
            )
            
            document = {
                'content': full_content,
                'source': 'github',
                'type': 'code',
                'repository': repo['name'],
                'file_path': result['path'],
                'role_tags': determine_role_tags(result['path'], full_content),
                'metadata': {
                    'language': result.get('language'),
                    'file_type': get_file_extension(result['path']),
                    'complexity': analyze_code_complexity(full_content)
                }
            }
            yield document
```

#### Issues & Pull Requests
```python
async def collect_issues_and_prs(repo):
    # Get issues with specific labels
    issues = await mcp_github_list_issues(
        owner=repo['owner']['login'],
        repo=repo['name'],
        state='all',
        labels=['bug', 'documentation', 'enhancement', 'support']
    )
    
    for issue in issues:
        # Get issue details including comments
        issue_detail = await mcp_github_get_issue(
            owner=repo['owner']['login'],
            repo=repo['name'],
            issue_number=issue['number']
        )
        
        document = {
            'content': f"Title: {issue['title']}\n\nBody: {issue['body']}\n\nComments: {get_issue_comments(issue_detail)}",
            'source': 'github',
            'type': 'issue',
            'repository': repo['name'],
            'role_tags': determine_issue_role_tags(issue['labels']),
            'metadata': {
                'issue_number': issue['number'],
                'state': issue['state'],
                'labels': [label['name'] for label in issue['labels']],
                'created_at': issue['created_at'],
                'updated_at': issue['updated_at']
            }
        }
        yield document
```

### 2. Confluence Data Collection

```python
from atlassian import Confluence

class ConfluenceConnector:
    def __init__(self, url, username, api_token):
        self.confluence = Confluence(
            url=url,
            username=username,
            password=api_token
        )
    
    async def collect_confluence_data(self, space_keys):
        for space_key in space_keys:
            # Get all pages in space
            pages = self.confluence.get_all_pages_from_space(
                space=space_key,
                start=0,
                limit=1000,
                expand='body.storage,metadata,version'
            )
            
            for page in pages:
                # Get page content
                page_content = self.confluence.get_page_by_id(
                    page_id=page['id'],
                    expand='body.storage,metadata.labels,version,ancestors'
                )
                
                document = {
                    'content': self.extract_content_from_html(page_content['body']['storage']['value']),
                    'source': 'confluence',
                    'type': 'documentation',
                    'space': space_key,
                    'role_tags': self.determine_confluence_role_tags(page_content),
                    'metadata': {
                        'page_id': page['id'],
                        'title': page['title'],
                        'space_key': space_key,
                        'labels': [label['name'] for label in page_content.get('metadata', {}).get('labels', {}).get('results', [])],
                        'created_at': page_content['version']['when'],
                        'updated_at': page_content['version']['when'],
                        'creator': page_content['version']['by']['displayName']
                    }
                }
                yield document
    
    def determine_confluence_role_tags(self, page_content):
        """Determine role tags based on page content and labels"""
        labels = [label['name'].lower() for label in page_content.get('metadata', {}).get('labels', {}).get('results', [])]
        title = page_content['title'].lower()
        content = page_content['body']['storage']['value'].lower()
        
        role_tags = []
        
        # Developer-focused content
        if any(keyword in title or keyword in content or keyword in labels 
               for keyword in ['api', 'sdk', 'code', 'technical', 'architecture', 
                              'deployment', 'development', 'integration', 'hld', 'lld']):
            role_tags.append('developer')
        
        # Support-focused content  
        if any(keyword in title or keyword in content or keyword in labels 
               for keyword in ['troubleshooting', 'support', 'faq', 'help', 
                              'issue', 'problem', 'solution', 'guide', 'howto']):
            role_tags.append('support')
        
        # Default to both if unclear
        if not role_tags:
            role_tags = ['developer', 'support']
            
        return role_tags
```

### 3. Jira Data Collection

```python
from atlassian import Jira

class JiraConnector:
    def __init__(self, url, username, api_token):
        self.jira = Jira(
            url=url,
            username=username,
            password=api_token
        )
    
    async def collect_jira_data(self, project_keys):
        for project_key in project_keys:
            # Get issues from project
            jql = f'project = {project_key} AND (issuetype = Bug OR issuetype = Story OR issuetype = Task OR issuetype = "Technical Debt")'
            
            issues = self.jira.jql(jql, expand='changelog,comments,worklog')
            
            for issue in issues['issues']:
                # Process issue content
                description = issue['fields'].get('description', '')
                comments = self.extract_comments(issue.get('fields', {}).get('comment', {}).get('comments', []))
                resolution = issue['fields'].get('resolution', {})
                
                content = f"""
                Summary: {issue['fields']['summary']}
                
                Description: {description}
                
                Comments: {comments}
                
                Resolution: {resolution.get('description', '') if resolution else 'Unresolved'}
                
                Worklogs: {self.extract_worklogs(issue)}
                """
                
                document = {
                    'content': content,
                    'source': 'jira',
                    'type': 'ticket',
                    'project': project_key,
                    'role_tags': self.determine_jira_role_tags(issue),
                    'metadata': {
                        'issue_key': issue['key'],
                        'issue_type': issue['fields']['issuetype']['name'],
                        'status': issue['fields']['status']['name'],
                        'priority': issue['fields']['priority']['name'] if issue['fields']['priority'] else 'None',
                        'assignee': issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else 'Unassigned',
                        'created_at': issue['fields']['created'],
                        'updated_at': issue['fields']['updated'],
                        'labels': issue['fields'].get('labels', [])
                    }
                }
                yield document
```

## Next Steps After Data Collection

### Step 1: Document Processing Pipeline

```python
class DocumentProcessor:
    def __init__(self):
        self.embedder = SentenceTransformer('BAAI/bge-large-en-v1.5')
        self.chunker = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
    
    async def process_document(self, document):
        # 1. Clean and preprocess content
        cleaned_content = self.clean_content(document['content'])
        
        # 2. Chunk the document
        chunks = self.chunker.split_text(cleaned_content)
        
        # 3. Generate embeddings
        embeddings = self.embedder.encode(chunks)
        
        # 4. Prepare chunks with metadata
        processed_chunks = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_doc = {
                'id': f"{document['source']}_{document.get('repository', document.get('space', document.get('project')))}_{i}",
                'content': chunk,
                'embedding': embedding,
                'metadata': {
                    **document['metadata'],
                    'source': document['source'],
                    'type': document['type'],
                    'role_tags': document['role_tags'],
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            }
            processed_chunks.append(chunk_doc)
        
        return processed_chunks
```

### Step 2: Vector Database Storage

```python
import chromadb

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collections = {
            'developer': self.client.get_or_create_collection(name="developer_docs"),
            'support': self.client.get_or_create_collection(name="support_docs"),
            'general': self.client.get_or_create_collection(name="general_docs")
        }
    
    async def store_chunks(self, processed_chunks):
        for chunk in processed_chunks:
            # Determine which collections to store in based on role tags
            target_collections = []
            
            if 'developer' in chunk['metadata']['role_tags']:
                target_collections.append('developer')
            if 'support' in chunk['metadata']['role_tags']:
                target_collections.append('support')
            if not target_collections:
                target_collections.append('general')
            
            # Store in appropriate collections
            for collection_name in target_collections:
                self.collections[collection_name].add(
                    ids=[chunk['id']],
                    embeddings=[chunk['embedding'].tolist()],
                    documents=[chunk['content']],
                    metadatas=[chunk['metadata']]
                )
```

### Step 3: Query Processing & Response Generation

```python
class AIAssistant:
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
        self.embedder = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    async def query(self, question: str, user_role: str, context: str = ""):
        # 1. Embed the question
        query_embedding = self.embedder.encode([question])
        
        # 2. Search relevant collections based on role
        collections_to_search = ['general']
        if user_role in ['developer', 'support']:
            collections_to_search.append(user_role)
        
        relevant_docs = []
        for collection_name in collections_to_search:
            results = self.vector_store.collections[collection_name].query(
                query_embeddings=query_embedding.tolist(),
                n_results=5,
                include=['documents', 'metadatas', 'distances']
            )
            relevant_docs.extend(zip(results['documents'][0], results['metadatas'][0], results['distances'][0]))
        
        # 3. Rerank and filter results
        relevant_docs = sorted(relevant_docs, key=lambda x: x[2])[:10]  # Top 10 by similarity
        
        # 4. Build role-specific prompt
        prompt = self.build_role_specific_prompt(question, user_role, relevant_docs, context)
        
        # 5. Generate response
        response = await self.llm.agenerate([prompt])
        
        return {
            'answer': response.generations[0][0].text,
            'sources': [doc[1] for doc in relevant_docs],
            'confidence': self.calculate_confidence(relevant_docs)
        }
    
    def build_role_specific_prompt(self, question, user_role, docs, context):
        role_instructions = {
            'developer': """
            You are assisting a software developer. Focus on:
            - Technical implementation details
            - Code examples and snippets
            - Architecture and design patterns
            - API documentation and usage
            - Deployment and configuration steps
            - Best practices and standards
            """,
            'support': """
            You are assisting a support engineer. Focus on:
            - Troubleshooting steps and procedures
            - Common issues and their solutions
            - User-facing error messages and fixes
            - Monitoring and diagnostic information
            - Escalation procedures
            - Customer-friendly explanations
            """
        }
        
        context_text = "\n".join([doc[0] for doc in docs])
        
        return f"""
        {role_instructions.get(user_role, 'You are a helpful AI assistant.')}
        
        Context Information:
        {context_text}
        
        Additional Context: {context}
        
        Question: {question}
        
        Please provide a comprehensive answer based on the context information above.
        Include relevant code examples, links, or specific steps where appropriate.
        If the information is not available in the context, clearly state that.
        
        Answer:
        """
```

This architecture provides a robust foundation for your AI assistant with role-based responses. The key is the systematic data collection, proper chunking and embedding, and role-aware prompt engineering.

Would you like me to implement any specific part of this architecture first?

