import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from main2 import DatabaseService, MQTTGateway, CameraMonitor
from database import get_unique_ping_periods, get_cameras_by_ping_period

@pytest.fixture
def mock_db_service():
    db_service = DatabaseService()
    db_service.cameras_map = {10: {1: MagicMock(name="Camera1", ip="192.168.1.1")}}
    db_service.coroutines_map = {}
    return db_service

@pytest.fixture
def mock_gateway():
    gateway = MagicMock()
    gateway.client = MagicMock()
    return gateway

@pytest.mark.asyncio
async def test_ping_camera(mock_gateway, mock_db_service):
    monitor = CameraMonitor(mock_gateway, mock_db_service)
    
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subproc:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_subproc.return_value = mock_proc
        
        status, ip = await monitor.ping_camera("Camera1", "192.168.1.1", asyncio.get_event_loop().time())
        
        assert status == 1
        assert ip == "192.168.1.1"
        mock_gateway.client.gw_send_telemetry.assert_called()

@pytest.mark.asyncio
async def test_ping_cameras_list(mock_gateway, mock_db_service):
    monitor = CameraMonitor(mock_gateway, mock_db_service)
    
    with patch.object(monitor, "ping_camera", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = (1, "192.168.1.1")
        
        task = asyncio.create_task(monitor.ping_cameras_list(10))
        await asyncio.sleep(0.1)
        task.cancel()
        
        mock_ping.assert_called()

@pytest.mark.asyncio
async def test_check_db(mock_gateway, mock_db_service):
    monitor = CameraMonitor(mock_gateway, mock_db_service)
    
    with patch("config.db_modified", new=True), patch.object(mock_db_service, "update_camera_pool") as mock_update:
        task = asyncio.create_task(monitor.check_db())
        await asyncio.sleep(0.1)
        task.cancel()
        
        mock_update.assert_called()
