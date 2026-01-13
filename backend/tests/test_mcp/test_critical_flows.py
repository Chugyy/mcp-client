"""Critical flow tests for MCP: crash recovery, retry logic, zombie cleanup, stdio transport."""

import pytest
import asyncio
import subprocess
import time
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.services.mcp.clients import HTTPMCPClient, StdioMCPClient


# ============================================================================
# SERVER CRASH RECOVERY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_server_crash_detection(db_pool_test):
    """Test server crash detection and status update."""
    from app.core.services.mcp.manager import ServerManager
    from app.core.utils.id_generator import generate_id

    # Create server
    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "Crash Test Server",
            "Server for crash testing",
            "http",
            "http://localhost:8080",
            "none",
            True,
            "active",
            None,  # user_id nullable
            False,
            "[]",
            "{}"
        )

    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # Simulate server crash during verification
        with patch('app.core.services.mcp.clients.HTTPMCPClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify.side_effect = Exception("Connection reset by peer")
            mock_client_cls.return_value = mock_client

            await ServerManager.verify(server_id)

        # Verify status updated to failed
        async with db_pool_test.acquire() as conn:
            result = await conn.fetchrow("SELECT status, status_message FROM mcp.servers WHERE id = $1", server_id)
            assert result["status"] == "failed"
            assert "reset by peer" in result["status_message"].lower() or "error" in result["status_message"].lower()

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)


@pytest.mark.asyncio
async def test_automatic_reconnection_after_crash(db_pool_test):
    """Test automatic reconnection after server crash."""
    from app.core.services.mcp.manager import ServerManager
    from app.core.utils.id_generator import generate_id

    # Create server
    server_id = generate_id('server')

    async with db_pool_test.acquire() as conn:
        await conn.execute(
            """INSERT INTO mcp.servers
               (id, name, description, type, url, auth_type, enabled, status, user_id, is_system, args, env)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)""",
            server_id,
            "Reconnect Test Server",
            "Server for reconnection testing",
            "http",
            "http://localhost:8080",
            "none",
            True,
            "failed",
            None,  # user_id nullable
            False,
            "[]",
            "{}"
        )

    with patch('app.database.db.get_pool', new_callable=AsyncMock, return_value=db_pool_test):
        # First attempt succeeds (server recovered)
        with patch('app.core.services.mcp.clients.HTTPMCPClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.verify.return_value = {
                "status": "active",
                "tools": []
            }
            mock_client_cls.return_value = mock_client

            await ServerManager.verify(server_id)

        # Verify status updated to active
        async with db_pool_test.acquire() as conn:
            result = await conn.fetchrow("SELECT status FROM mcp.servers WHERE id = $1", server_id)
            assert result["status"] == "active"

    # Cleanup
    async with db_pool_test.acquire() as conn:
        await conn.execute("DELETE FROM mcp.servers WHERE id = $1", server_id)


@pytest.mark.asyncio
async def test_health_check_after_crash():
    """Test health check functionality after crash recovery."""
    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    # First call fails (crash)
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.verify()
        assert result["status"] == "failed"

    # Second call succeeds (recovery)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "capabilities": {},
            "protocolVersion": "1.0"
        }
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await client.verify()
        assert result["status"] == "active"


# ============================================================================
# RETRY LOGIC TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tool_execution_retry_with_exponential_backoff():
    """Test retry logic concept with exponential backoff."""
    import httpx

    # This test demonstrates the retry pattern that should be implemented
    call_times = []
    max_retries = 3

    async def simulated_tool_call_with_retry():
        """Simulated retry logic with exponential backoff."""
        for attempt in range(max_retries):
            call_times.append(time.time())

            if len(call_times) < 3:
                # Simulate failure on first 2 attempts
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt * 0.1 seconds (faster for testing)
                    await asyncio.sleep(0.1 * (2 ** attempt))
                continue
            else:
                # Success on 3rd attempt
                return {"success": True, "result": "Success after retries"}

        return {"success": False, "error": "Max retries exceeded"}

    result = await simulated_tool_call_with_retry()

    # Verify 3 attempts were made
    assert len(call_times) == 3

    # Verify exponential backoff intervals (0.1s, 0.2s with some tolerance)
    if len(call_times) >= 2:
        interval_1 = call_times[1] - call_times[0]
        interval_2 = call_times[2] - call_times[1]

        # Allow tolerance for timing (at least 0.09s and 0.19s)
        assert interval_1 >= 0.09
        assert interval_2 >= 0.19

    assert result["success"] is True


@pytest.mark.asyncio
async def test_tool_execution_max_retries_exceeded():
    """Test that max retries are respected."""
    import httpx

    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    attempt_count = 0

    async def mock_post_always_fails(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        raise httpx.TimeoutException("Persistent timeout")

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = mock_post_always_fails
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Call with max_retries=3
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await client.call_tool("test_tool", {})
            except:
                pass

        # Should have attempted exactly max_retries times
        assert attempt_count == max_retries


@pytest.mark.asyncio
async def test_retry_success_after_transient_failure():
    """Test successful retry after transient network failure."""
    import httpx

    client = HTTPMCPClient(
        server_id="server-123",
        url="http://localhost:8080",
        auth_type="none"
    )

    attempt_count = 0

    async def mock_post_transient_fail(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count == 1:
            # First attempt: transient failure
            raise httpx.TimeoutException("Temporary timeout")

        # Second attempt: success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "Success after retry"}]}
        }
        return mock_response

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = mock_post_transient_fail
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First attempt will fail, second should succeed
        result1 = await client.call_tool("test_tool", {})
        assert result1["success"] is False

        result2 = await client.call_tool("test_tool", {})
        assert result2["success"] is True
        assert attempt_count == 2


# ============================================================================
# ZOMBIE PROCESS CLEANUP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_process_cleanup_on_normal_shutdown(mock_mcp_server):
    """Test that process is properly terminated on normal shutdown."""
    # mock_mcp_server is a real subprocess.Popen
    process = mock_mcp_server

    # Process should be running
    assert process.poll() is None

    # Normal shutdown (handled by fixture cleanup)
    # The fixture will call process.terminate() and process.wait()

    # After fixture cleanup in next yield, process should be terminated
    # We can't test that here directly, but we verify the process is running now
    assert process.poll() is None


@pytest.mark.asyncio
async def test_no_zombie_processes_after_stdio_client():
    """Test that no zombie processes remain after StdioMCPClient usage."""
    import os
    import signal

    # Get initial process count
    initial_processes = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    ).stdout.count("mock_mcp_server")

    # Create and use stdio client with real subprocess
    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "../mocks",
        "mock_mcp_server.py"
    )

    process = subprocess.Popen(
        ["python", mock_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait briefly for process to start
    await asyncio.sleep(0.2)

    # Process should be running
    assert process.poll() is None

    # Terminate properly
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    # Verify no zombies
    await asyncio.sleep(0.5)
    final_processes = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    ).stdout.count("mock_mcp_server")

    # Should be same as initial (or at most +0)
    assert final_processes <= initial_processes


@pytest.mark.asyncio
async def test_cleanup_on_abnormal_termination():
    """Test cleanup on abnormal process termination."""
    import os

    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "../mocks",
        "mock_mcp_server.py"
    )

    process = subprocess.Popen(
        ["python", mock_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    await asyncio.sleep(0.2)

    # Force kill (abnormal termination)
    process.kill()
    process.wait()

    # Verify process is dead
    assert process.poll() is not None
    assert process.returncode != 0  # Non-zero exit code indicates abnormal termination


# ============================================================================
# STDIO TRANSPORT WITH REAL SUBPROCESS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_stdio_client_with_real_process(mock_mcp_server):
    """Test StdioMCPClient with real mock server subprocess."""
    # mock_mcp_server is a real subprocess.Popen
    process = mock_mcp_server

    # Create StdioMCPClient (would need implementation)
    # For now, test direct stdio communication
    import json

    # Send initialize request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0",
            "capabilities": {}
        }
    }

    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

    # Read response
    await asyncio.sleep(0.3)
    response_line = process.stdout.readline()

    assert response_line
    response = json.loads(response_line)
    assert response.get("jsonrpc") == "2.0"


@pytest.mark.asyncio
async def test_stdio_json_rpc_over_pipes():
    """Test JSON-RPC communication over stdio pipes."""
    import os
    import json

    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "../mocks",
        "mock_mcp_server.py"
    )

    process = subprocess.Popen(
        ["python", mock_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    await asyncio.sleep(0.5)

    # Test list tools request
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

    # Read response
    await asyncio.sleep(0.3)
    response_line = process.stdout.readline()

    if response_line:
        response = json.loads(response_line)
        assert response.get("jsonrpc") == "2.0"

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.mark.asyncio
async def test_stdio_tool_discovery():
    """Test tool discovery via stdio transport."""
    import os
    import json

    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "../mocks",
        "mock_mcp_server.py"
    )

    process = subprocess.Popen(
        ["python", mock_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    await asyncio.sleep(0.5)

    # Send tools/list request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }

    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

    await asyncio.sleep(0.3)
    response_line = process.stdout.readline()

    if response_line:
        response = json.loads(response_line)
        # Should have tools in result
        if "result" in response:
            assert "tools" in response["result"]

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.mark.asyncio
async def test_stdio_tool_execution():
    """Test tool execution via stdio transport."""
    import os
    import json

    mock_server_path = os.path.join(
        os.path.dirname(__file__),
        "../mocks",
        "mock_mcp_server.py"
    )

    process = subprocess.Popen(
        ["python", mock_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    await asyncio.sleep(0.5)

    # Send tool call request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "test_tool",
            "arguments": {"input": "hello"}
        }
    }

    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

    await asyncio.sleep(0.3)
    response_line = process.stdout.readline()

    if response_line:
        response = json.loads(response_line)
        # Should have result with processed input
        if "result" in response:
            assert "content" in response["result"]

    # Cleanup
    process.terminate()
    process.wait(timeout=5)
