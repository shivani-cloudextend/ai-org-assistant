"""
AI Engine for Organization Assistant
Handles role-based response generation using retrieved context
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

# Third-party imports
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from document_processor import VectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRole(Enum):
    DEVELOPER = "developer"
    SUPPORT = "support"
    MANAGER = "manager"
    GENERAL = "general"

@dataclass
class QueryContext:
    """Context information for a user query"""
    user_role: UserRole
    query: str
    additional_context: str = ""
    filters: Optional[Dict] = None
    max_context_length: int = 4000

@dataclass
class AIResponse:
    """Response from the AI assistant"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float
    processing_time: float
    role_specific_notes: List[str]
    suggested_actions: List[str]

class RoleBasedPromptBuilder:
    """Builds role-specific prompts for different user types"""
    
    def __init__(self):
        self.role_prompts = {
            UserRole.DEVELOPER: {
                "system_prompt": """You are an AI assistant helping software developers. Your responses should be:

TECHNICAL FOCUS:
- Provide detailed technical implementation details
- Include code examples, configuration snippets, and API usage
- Explain architecture decisions and design patterns
- Focus on HOW to implement, deploy, and configure systems
- Include best practices, standards, and conventions
- Mention performance implications and optimization opportunities

RESPONSE STYLE:
- Use technical terminology appropriately
- Provide step-by-step implementation guides
- Include relevant file paths, configuration keys, and command examples
- Reference specific functions, classes, and modules when applicable
- Suggest debugging techniques and troubleshooting approaches

AVOID:
- High-level business explanations
- User-facing feature descriptions
- Marketing or sales content""",

                "context_instruction": """Based on the technical documentation and code examples provided below, give a comprehensive technical answer that a developer can immediately act upon.""",
                
                "response_format": """Structure your response as:
1. **Technical Overview** - Brief technical summary
2. **Implementation Details** - Step-by-step technical instructions
3. **Code Examples** - Relevant code snippets or configurations
4. **Best Practices** - Technical recommendations and gotchas
5. **Related Resources** - Links to relevant documentation or code files"""
            },

            UserRole.SUPPORT: {
                "system_prompt": """You are an AI assistant helping support engineers resolve customer issues. Your responses should be:

SUPPORT FOCUS:
- Provide clear troubleshooting steps and diagnostic procedures
- Explain common issues and their root causes
- Focus on WHAT to check, HOW to diagnose, and HOW to resolve problems
- Include monitoring, logging, and diagnostic information
- Provide customer-friendly explanations for complex technical issues
- Suggest escalation paths when needed

RESPONSE STYLE:
- Use clear, actionable language
- Provide step-by-step troubleshooting procedures
- Include specific error messages and their meanings
- Suggest multiple approaches (quick fixes vs. permanent solutions)
- Explain impact on users and business operations

AVOID:
- Deep technical implementation details
- Code development instructions
- Architecture discussions unless relevant to troubleshooting""",

                "context_instruction": """Based on the support documentation, troubleshooting guides, and issue reports provided below, give a practical support response that helps resolve customer issues.""",
                
                "response_format": """Structure your response as:
1. **Issue Summary** - Brief description of the problem
2. **Immediate Steps** - Quick diagnostic or temporary fixes
3. **Detailed Troubleshooting** - Systematic investigation steps
4. **Resolution** - Permanent solution if available
5. **Prevention** - How to prevent this issue in the future
6. **Escalation** - When and how to escalate if needed"""
            },

            UserRole.MANAGER: {
                "system_prompt": """You are an AI assistant helping engineering managers and team leads. Your responses should be:

MANAGEMENT FOCUS:
- Provide strategic and operational insights
- Explain business impact and technical risks
- Focus on team processes, planning, and decision-making
- Include timeline estimates and resource requirements
- Balance technical details with business implications
- Suggest organizational and process improvements

RESPONSE STYLE:
- Use business and management terminology
- Provide executive summaries and key takeaways
- Include risk assessments and mitigation strategies
- Suggest team coordination and communication approaches
- Balance technical accuracy with business clarity

AVOID:
- Detailed implementation code
- Step-by-step technical procedures
- Low-level troubleshooting steps""",

                "context_instruction": """Based on the project documentation, process guides, and team information provided below, give a strategic response that helps with management decisions.""",
                
                "response_format": """Structure your response as:
1. **Executive Summary** - Key points for quick understanding
2. **Impact Assessment** - Business and technical implications
3. **Recommendations** - Strategic actions and decisions
4. **Resource Requirements** - Team, time, and technical needs
5. **Risk Mitigation** - Potential issues and prevention strategies
6. **Next Steps** - Immediate and long-term actions"""
            },

            UserRole.GENERAL: {
                "system_prompt": """You are a helpful AI assistant providing comprehensive information about organizational systems and processes. Adapt your response style based on the context and question complexity.""",
                
                "context_instruction": """Based on the documentation provided below, give a comprehensive and balanced answer appropriate for a general audience.""",
                
                "response_format": """Structure your response clearly with appropriate sections based on the question type."""
            }
        }

    def build_prompt(self, query_context: QueryContext, retrieved_docs: List[Dict]) -> str:
        """Build role-specific prompt with context"""
        
        role = query_context.user_role
        role_config = self.role_prompts[role]
        
        # Build context from retrieved documents
        context_text = self._build_context_text(retrieved_docs, query_context.max_context_length)
        
        # Construct the full prompt
        prompt = f"""{role_config['system_prompt']}

{role_config['context_instruction']}

CONTEXT INFORMATION:
{context_text}

ADDITIONAL CONTEXT: {query_context.additional_context}

USER QUESTION: {query_context.query}

{role_config['response_format']}

Please provide a comprehensive answer based on the context information above. If the information is insufficient or unclear, state what additional information would be needed."""

        return prompt

    def _build_context_text(self, retrieved_docs: List[Dict], max_length: int) -> str:
        """Build context text from retrieved documents with length limits"""
        
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(retrieved_docs):
            # Format document information
            source_info = f"Source: {doc['metadata'].get('source', 'unknown')}"
            if doc['metadata'].get('repository'):
                source_info += f" | Repository: {doc['metadata']['repository']}"
            if doc['metadata'].get('file_path'):
                source_info += f" | File: {doc['metadata']['file_path']}"
            if doc['metadata'].get('title'):
                source_info += f" | Title: {doc['metadata']['title']}"
            
            doc_text = f"--- Document {i+1} ---\n{source_info}\nContent: {doc['content']}\n"
            
            # Check if adding this document would exceed limit
            if current_length + len(doc_text) > max_length:
                if context_parts:  # If we have at least one document, break
                    break
                else:  # If this is the first document and it's too long, truncate it
                    available_length = max_length - len(f"--- Document 1 ---\n{source_info}\nContent: ")
                    truncated_content = doc['content'][:available_length] + "...[truncated]"
                    doc_text = f"--- Document 1 ---\n{source_info}\nContent: {truncated_content}\n"
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
        
        return "\n".join(context_parts)

class AIEngine:
    """Main AI engine for processing queries and generating responses"""
    
    def __init__(self, 
                 openai_api_key: str,
                 vector_store: VectorStore,
                 model: str = "gpt-4-turbo-preview"):
        
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.vector_store = vector_store
        self.model = model
        self.prompt_builder = RoleBasedPromptBuilder()
        self.embedder = SentenceTransformer('BAAI/bge-large-en-v1.5')
        
        logger.info(f"AI Engine initialized with model: {model}")

    async def process_query(self, query_context: QueryContext) -> AIResponse:
        """Process a user query and generate role-based response"""
        
        start_time = datetime.now()
        
        try:
            # Step 1: Retrieve relevant documents
            retrieved_docs = await self._retrieve_relevant_docs(query_context)
            
            if not retrieved_docs:
                return AIResponse(
                    answer="I don't have enough information to answer your question. Please provide more specific details or check if the relevant documentation is available in the system.",
                    sources=[],
                    confidence_score=0.0,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    role_specific_notes=["No relevant documents found"],
                    suggested_actions=["Try rephrasing your question", "Check if documentation exists for this topic"]
                )
            
            # Step 2: Build role-specific prompt
            prompt = self.prompt_builder.build_prompt(query_context, retrieved_docs)
            
            # Step 3: Generate AI response
            ai_response_text = await self._generate_response(prompt)
            
            # Step 4: Calculate confidence and extract additional info
            confidence_score = self._calculate_confidence(retrieved_docs, query_context.query)
            role_notes, suggested_actions = self._extract_role_specific_info(
                query_context.user_role, 
                retrieved_docs, 
                ai_response_text
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AIResponse(
                answer=ai_response_text,
                sources=self._format_sources(retrieved_docs),
                confidence_score=confidence_score,
                processing_time=processing_time,
                role_specific_notes=role_notes,
                suggested_actions=suggested_actions
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return AIResponse(
                answer=f"I encountered an error while processing your question: {str(e)}. Please try again or rephrase your question.",
                sources=[],
                confidence_score=0.0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                role_specific_notes=["Error occurred during processing"],
                suggested_actions=["Try rephrasing your question", "Contact system administrator if error persists"]
            )

    async def _retrieve_relevant_docs(self, query_context: QueryContext) -> List[Dict]:
        """Retrieve relevant documents based on query and role"""
        
        # Search in role-specific collection first, then general
        results = await self.vector_store.search_similar(
            query=query_context.query,
            user_role=query_context.user_role.value,
            n_results=15,  # Get more results for better selection
            filters=query_context.filters
        )
        
        # Filter and re-rank results based on role relevance
        filtered_results = self._filter_by_role_relevance(results, query_context.user_role)
        
        # Return top 8 results
        return filtered_results[:8]

    def _filter_by_role_relevance(self, results: List[Dict], user_role: UserRole) -> List[Dict]:
        """Filter and re-rank results based on role relevance"""
        
        role_keywords = {
            UserRole.DEVELOPER: ['code', 'api', 'implementation', 'technical', 'architecture', 'deployment', 'configuration'],
            UserRole.SUPPORT: ['troubleshooting', 'error', 'issue', 'problem', 'solution', 'support', 'diagnostic'],
            UserRole.MANAGER: ['process', 'team', 'planning', 'strategy', 'decision', 'management', 'roadmap']
        }
        
        relevant_keywords = role_keywords.get(user_role, [])
        
        # Score results based on role relevance
        for result in results:
            content = result['content'].lower()
            metadata = result['metadata']
            
            role_score = 0
            
            # Check for role-specific keywords
            for keyword in relevant_keywords:
                if keyword in content:
                    role_score += 1
            
            # Check metadata role tags
            if 'role_tags' in metadata and user_role.value in metadata['role_tags']:
                role_score += 3
            
            # Check content type relevance
            content_type = metadata.get('content_type', '')
            if user_role == UserRole.DEVELOPER and content_type in ['code_snippet', 'api_documentation', 'configuration']:
                role_score += 2
            elif user_role == UserRole.SUPPORT and content_type in ['troubleshooting', 'setup_instructions']:
                role_score += 2
            
            # Add role score to result (normalize by content length to avoid bias)
            result['role_relevance_score'] = role_score / max(len(content.split()), 1)
        
        # Sort by combined score (similarity + role relevance)
        results.sort(key=lambda x: (1 - x['distance']) + x.get('role_relevance_score', 0), reverse=True)
        
        return results

    async def _generate_response(self, prompt: str) -> str:
        """Generate response using OpenAI API"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Lower temperature for more consistent responses
                max_tokens=2000,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            raise

    def _calculate_confidence(self, retrieved_docs: List[Dict], query: str) -> float:
        """Calculate confidence score based on retrieval quality"""
        
        if not retrieved_docs:
            return 0.0
        
        # Factors affecting confidence:
        # 1. Similarity scores of retrieved documents
        # 2. Number of relevant documents
        # 3. Content quality indicators
        
        similarity_scores = [1 - doc['distance'] for doc in retrieved_docs]
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        
        # Penalty for few documents
        document_factor = min(len(retrieved_docs) / 5, 1.0)
        
        # Bonus for recent documents
        recent_docs = sum(1 for doc in retrieved_docs 
                         if doc.get('metadata', {}).get('updated_at') 
                         and (datetime.now() - datetime.fromisoformat(doc['metadata']['updated_at'].replace('Z', '+00:00'))).days < 30)
        recency_factor = 1.0 + (recent_docs / len(retrieved_docs)) * 0.1
        
        confidence = avg_similarity * document_factor * recency_factor
        return min(confidence, 1.0)

    def _extract_role_specific_info(self, user_role: UserRole, retrieved_docs: List[Dict], response: str) -> Tuple[List[str], List[str]]:
        """Extract role-specific notes and suggested actions"""
        
        notes = []
        actions = []
        
        # Analyze the sources for role-specific insights
        doc_types = set()
        sources = set()
        
        for doc in retrieved_docs:
            doc_types.add(doc.get('metadata', {}).get('content_type', 'unknown'))
            sources.add(doc.get('metadata', {}).get('source', 'unknown'))
        
        # Role-specific notes
        if user_role == UserRole.DEVELOPER:
            if 'code_snippet' in doc_types:
                notes.append("Code examples available in sources")
            if 'api_documentation' in doc_types:
                notes.append("API documentation referenced")
            
            actions.extend([
                "Review code examples in referenced files",
                "Check for related test files or documentation",
                "Consider implementation best practices"
            ])
            
        elif user_role == UserRole.SUPPORT:
            if 'troubleshooting' in doc_types:
                notes.append("Troubleshooting guides available")
            if any('error' in doc.get('content', '').lower() for doc in retrieved_docs):
                notes.append("Error cases and solutions documented")
            
            actions.extend([
                "Follow diagnostic steps systematically", 
                "Document issue details for tracking",
                "Escalate if resolution steps don't work"
            ])
            
        elif user_role == UserRole.MANAGER:
            notes.append(f"Information gathered from {len(sources)} different sources")
            actions.extend([
                "Review team processes and documentation",
                "Consider resource allocation for improvements",
                "Plan knowledge sharing sessions"
            ])
        
        return notes, actions

    def _format_sources(self, retrieved_docs: List[Dict]) -> List[Dict[str, Any]]:
        """Format source information for response"""
        
        sources = []
        for doc in retrieved_docs:
            metadata = doc.get('metadata', {})
            
            source = {
                'type': metadata.get('source', 'unknown'),
                'content_type': metadata.get('content_type', 'general'),
                'similarity_score': 1 - doc.get('distance', 1),
                'title': metadata.get('title', metadata.get('file_path', 'Unknown'))
            }
            
            # Add source-specific information
            if metadata.get('repository'):
                source['repository'] = metadata['repository']
            if metadata.get('file_path'):
                source['file_path'] = metadata['file_path']
            if metadata.get('url'):
                source['url'] = metadata['url']
            if metadata.get('updated_at'):
                source['last_updated'] = metadata['updated_at']
            
            sources.append(source)
        
        return sources

# Example usage and testing
async def main():
    """Example usage of the AI Engine"""
    
    # This would require actual OpenAI API key and vector store with data
    # vector_store = VectorStore()
    # ai_engine = AIEngine("your-openai-key", vector_store)
    
    # Example query context
    query_context = QueryContext(
        user_role=UserRole.DEVELOPER,
        query="How do I deploy the authentication service?",
        additional_context="Production environment deployment"
    )
    
    # This would generate a response
    # response = await ai_engine.process_query(query_context)
    # print(f"Answer: {response.answer}")
    # print(f"Confidence: {response.confidence_score}")
    # print(f"Sources: {len(response.sources)}")
    
    print("AI Engine example - requires OpenAI API key and populated vector store to run")

if __name__ == "__main__":
    asyncio.run(main())

