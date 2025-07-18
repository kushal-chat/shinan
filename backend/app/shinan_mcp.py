#!/usr/bin/env python3
"""
Sample MCP Server for Deep Research API Integration

This server implements the Model Context Protocol (MCP) with search and fetch
capabilities designed to work with ChatGPT's deep research feature.
"""

import logging
from typing import Dict, List, Any
from fastmcp import FastMCP
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
VECTOR_STORE_ID = os.environ.get("VECTOR_STORE_ID")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) 

def create_server():
    """Create and configure the MCP server with search and fetch tools."""

    # Initialize the FastMCP server
    mcp = FastMCP(name="Sample Deep Research MCP Server",
                  instructions="""
        This MCP server provides search and document retrieval capabilities for Softbank strategy and financial documents.
        Use the MCP server file search to find relevant Softbank documents based on keywords, then use the fetch 
        tool to retrieve complete document content with citations.
        """)

    @mcp.tool()
    async def file_search(query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve Softbank strategy information by ID for detailed analysis and citation.
        
        Use this after finding relevant documents with the search tool to get complete 
        information for Softbank analysis.
        
        Args:
            id: File ID from vector store (file-xxx) or local document ID
            
        Returns:
            Complete document with id, title, full text content, optional URL, and metadata

        ソフトバンクの戦略情報をIDで取得し、詳細な分析や引用に利用します。
        検索ツールで関連するドキュメントを見つけた後に使用し、
        ソフトバンク分析のための完全な情報を取得してください。
        引数:
         id: ベクトルストアのファイルID（file-xxx）またはローカルドキュメントID
        戻り値:
         id、タイトル、全文コンテンツ、オプションのURL、およびメタデータを含む完全なドキュメント

        """
        if not query or not query.strip():
            return {"results": []}

        if not openai_client:
            logger.error("OpenAI client not initialized - API key missing")
            raise ValueError(
                "OpenAI API key is required for vector store search")

        # Search the vector store using OpenAI API
        logger.info(
            f"Searching vector store {VECTOR_STORE_ID} for query: '{query}'")

        response = openai_client.vector_stores.search(
            vector_store_id=VECTOR_STORE_ID, query=query)

        results = []

        # Process the vector store search results
        if hasattr(response, 'data') and response.data:
            for i, item in enumerate(response.data):
                # Extract file_id, filename, and content from the VectorStoreSearchResponse
                item_id = getattr(item, 'file_id', f"vs_{i}")
                item_filename = getattr(item, 'filename', f"Document {i+1}")

                # Extract text content from the content array
                content_list = getattr(item, 'content', [])
                text_content = ""
                if content_list and len(content_list) > 0:
                    # Get text from the first content item
                    first_content = content_list[0]
                    if hasattr(first_content, 'text'):
                        text_content = first_content.text
                    elif isinstance(first_content, dict):
                        text_content = first_content.get('text', '')

                if not text_content:
                    text_content = "No content available"

                # Create a snippet from content
                text_snippet = text_content[:200] + "..." if len(
                    text_content) > 200 else text_content

                result = {
                    "id": item_id,
                    "title": item_filename,
                    "text": text_snippet,
                    "url": f"https://platform.openai.com/storage/files/{item_id}"
                }

                results.append(result)

        logger.info(f"Vector store search returned {len(results)} results")
        return {"results": results}

    @mcp.tool()
    async def file_fetch(id: str) -> Dict[str, Any]:
        """
        Retrieve Softbank strategy information by ID for detailed analysis and citation.
        
        Use this after finding relevant documents with the search tool to get complete 
        information for Softbank analysis.
        
        Args:
            id: File ID from vector store (file-xxx) or local document ID
            
        Returns:
            Complete document with id, title, full text content, optional URL, and metadata

        ソフトバンクの戦略情報をIDで取得し、詳細な分析や引用に利用します。
        検索ツールで関連するドキュメントを見つけた後に使用し、
        ソフトバンク分析のための完全な情報を取得してください。
        引数:
         id: ベクトルストアのファイルID（file-xxx）またはローカルドキュメントID
        戻り値:
         id、タイトル、全文コンテンツ、オプションのURL、およびメタデータを含む完全なドキュメント 
        """
        if not id:
            raise ValueError("Document ID is required")

        if not openai_client:
            logger.error("OpenAI client not initialized - API key missing")
            raise ValueError(
                "OpenAI API key is required for vector store file retrieval")

        logger.info(f"Fetching content from vector store for file ID: {id}")

        # Fetch file content from vector store
        content_response = openai_client.vector_stores.files.content(
            vector_store_id=VECTOR_STORE_ID, file_id=id)

        # Get file metadata
        file_info = openai_client.vector_stores.files.retrieve(
            vector_store_id=VECTOR_STORE_ID, file_id=id)

        # Extract content from paginated response
        file_content = ""
        if hasattr(content_response, 'data') and content_response.data:
            # Combine all content chunks from FileContentResponse objects
            content_parts = []
            for content_item in content_response.data:
                if hasattr(content_item, 'text'):
                    content_parts.append(content_item.text)
            file_content = "\n".join(content_parts)
        else:
            file_content = "No content available"

        # Use filename as title and create proper URL for citations
        filename = getattr(file_info, 'filename', f"Document {id}")
        
        result = {
            "id": id,
            "title": filename,
            "text": file_content,
            "url": f"https://platform.openai.com/storage/files/{id}",
            "metadata": None
        }

        # Add metadata if available from file info
        if hasattr(file_info, 'attributes') and file_info.attributes:
            result["metadata"] = file_info.attributes

        logger.info(f"Successfully fetched vector store file: {id}")
        return result

    return mcp

def main():
    """Main function to start the MCP server."""
    # Verify OpenAI client is initialized
    if not openai_client:
        logger.error(
            "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
        )
        raise ValueError("OpenAI API key is required")

    logger.info(f"Using vector store: {VECTOR_STORE_ID}")

    # Create the MCP server
    server = create_server()

    # Configure and start the server
    logger.info("Starting MCP server on localhost:8080")
    logger.info("Server will be accessible via SSE transport")
    logger.info("Connect this server to ChatGPT Deep Research for testing")

    try:
        # Use FastMCP's built-in run method with SSE transport
        server.run(transport="sse", host="localhost", port=8080)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()