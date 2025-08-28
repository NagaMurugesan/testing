import streamlit as st
import asyncio
import nest_asyncio
nest_asyncio.apply()

from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.agent.workflow import (
    FunctionAgent, 
    ToolCallResult, 
    ToolCall
)
from llama_index.core.workflow import Context

# Configure Streamlit page
st.set_page_config(
    page_title="MCP Tool Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 MCP Tool Assistant")
st.markdown("An AI assistant that can interact with your database using MCP tools")

SYSTEM_PROMPT = """\
You are an AI assistant for Tool Calling.

Before you help a user, you need to work with tools to interact with Our Database
"""

@st.cache_resource
def initialize_llm():
    """Initialize and cache the LLM"""
    llm = Ollama(model="llama3.2", request_timeout=120.0)
    Settings.llm = llm
    return llm

@st.cache_resource
def initialize_mcp_client():
    """Initialize and cache the MCP client"""
    try:
        mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
        mcp_tools = McpToolSpec(client=mcp_client)
        return mcp_tools
    except Exception as e:
        st.error(f"Failed to connect to MCP server: {e}")
        return None

async def create_agent(tools: McpToolSpec):
    """Create the agent with MCP tools"""
    try:
        tool_list = await tools.to_tool_list_async()
        
        agent = ReActAgent(
            name="FlightAgent", 
            llm=Ollama(model="llama3.2"),
            tools=tool_list,
            description="Agent using MCP flight search tools with natural language understanding",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            verbose=False
        )
        return agent, tool_list
    except Exception as e:
        st.error(f"Failed to create agent: {e}")
        return None, None

async def handle_user_message(
    message_content: str,
    agent: FunctionAgent,
    agent_context: Context,
    verbose: bool = False,
):
    """Handle user message and return response"""
    tool_calls = []
    tool_results = []
    
    handler = agent.run(message_content, ctx=agent_context)
    
    async for event in handler.stream_events():
        if verbose and type(event) == ToolCall:
            tool_calls.append({
                'tool_name': event.tool_name,
                'tool_kwargs': event.tool_kwargs
            })
        elif verbose and type(event) == ToolCallResult:
            tool_results.append({
                'tool_name': event.tool_name,
                'tool_output': event.tool_output
            })

    response = await handler
    return str(response), tool_calls, tool_results

def run_async_function(coro):
    """Helper function to run async functions in Streamlit"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Initialize components
llm = initialize_llm()
mcp_tools = initialize_mcp_client()

if mcp_tools is None:
    st.error("Cannot proceed without MCP connection. Please ensure your MCP server is running on http://127.0.0.1:8000/sse")
    st.stop()

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = None
    st.session_state.agent_context = None
    st.session_state.chat_history = []
    st.session_state.tools_info = []

# Initialize agent if not already done
if st.session_state.agent is None:
    with st.spinner("Initializing agent and loading tools..."):
        try:
            agent, tool_list = run_async_function(create_agent(mcp_tools))
            if agent is not None:
                st.session_state.agent = agent
                st.session_state.agent_context = Context(agent)
                st.session_state.tools_info = [
                    {'name': tool.metadata.name, 'description': tool.metadata.description}
                    for tool in tool_list
                ]
                st.success("Agent initialized successfully!")
            else:
                st.error("Failed to initialize agent")
                st.stop()
        except Exception as e:
            st.error(f"Error initializing agent: {e}")
            st.stop()

# Sidebar with tool information
with st.sidebar:
    st.header("Available Tools")
    if st.session_state.tools_info:
        for tool in st.session_state.tools_info:
            with st.expander(tool['name']):
                st.write(tool['description'])
    else:
        st.write("No tools available")
    
    st.header("Options")
    verbose = st.checkbox("Show tool calls", value=True)
    
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# Main chat interface
st.header("Chat with Assistant")

# Display chat history
if st.session_state.chat_history:
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(chat['user_message'])
        
        with st.chat_message("assistant"):
            st.write(chat['response'])
            
            if verbose and chat.get('tool_calls'):
                with st.expander("Tool Calls"):
                    for tool_call in chat['tool_calls']:
                        st.code(f"Called: {tool_call['tool_name']}")
                        st.json(tool_call['tool_kwargs'])
            
            if verbose and chat.get('tool_results'):
                with st.expander("Tool Results"):
                    for tool_result in chat['tool_results']:
                        st.code(f"Result from: {tool_result['tool_name']}")
                        st.text(str(tool_result['tool_output']))

# Alternative input methods for better visibility
st.subheader("💬 Send a Message")

# Method 1: Text input with button (more visible)
col1, col2 = st.columns([4, 1])
with col1:
    user_input_text = st.text_input("Type your message:", placeholder="Ask me anything about the database...", key="user_input")
with col2:
    send_button = st.button("Send", type="primary")

# Method 2: Chat input (as fallback)
user_input_chat = st.chat_input("Or use this chat input...")

# Determine which input to use
user_input = None
if send_button and user_input_text:
    user_input = user_input_text
elif user_input_chat:
    user_input = user_input_chat

if user_input:
    if st.session_state.agent is None:
        st.error("Agent not initialized. Please refresh the page.")
    else:
        # Add user message to chat
        with st.chat_message("user"):
            st.write(user_input)
        
        # Process message
        with st.chat_message("assistant"):
            with st.spinner("Processing your request..."):
                try:
                    response, tool_calls, tool_results = run_async_function(
                        handle_user_message(
                            user_input, 
                            st.session_state.agent, 
                            st.session_state.agent_context, 
                            verbose=verbose
                        )
                    )
                    
                    st.write(response)
                    
                    # Show tool calls if verbose mode is on
                    if verbose and tool_calls:
                        with st.expander("Tool Calls"):
                            for tool_call in tool_calls:
                                st.code(f"Called: {tool_call['tool_name']}")
                                st.json(tool_call['tool_kwargs'])
                    
                    if verbose and tool_results:
                        with st.expander("Tool Results"):
                            for tool_result in tool_results:
                                st.code(f"Result from: {tool_result['tool_name']}")
                                st.text(str(tool_result['tool_output']))
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'user_message': user_input,
                        'response': response,
                        'tool_calls': tool_calls,
                        'tool_results': tool_results
                    })
                    
                    # Clear the text input after sending
                    if 'user_input' in st.session_state:
                        del st.session_state.user_input
                    
                except Exception as e:
                    st.error(f"Error processing message: {e}")

# Footer
st.markdown("---")
st.markdown("💡 **Tip**: Use the sidebar to view available tools and toggle verbose mode to see tool calls.")

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Agent Status:**", "✅ Initialized" if st.session_state.agent is not None else "❌ Not initialized")
    st.write("**Tools Count:**", len(st.session_state.tools_info))
    st.write("**Chat History:**", len(st.session_state.chat_history), "messages")
    
    if st.button("Test Connection"):
        try:
            test_tools = initialize_mcp_client()
            if test_tools:
                st.success("✅ MCP connection working!")
            else:
                st.error("❌ MCP connection failed!")
        except Exception as e:
            st.error(f"❌ Connection test failed: {e}")
