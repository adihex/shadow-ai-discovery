import os
from unittest.mock import MagicMock, patch
import pytest
from app.services.scanner import GCPScanner


def test_scanner_gcp_creds_set_via_env():
    # If GOOGLE_APPLICATION_CREDENTIALS is set, gcp_creds_set should be True
    with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/key.json"}):
        scanner = GCPScanner(project_id="test-project", db_session=MagicMock())
        with patch("app.services.scanner.GCP_SDK_AVAILABLE", True):
            # We don't want to run the actual scan, just mock the scan sub-methods
            with patch.object(scanner, "_scan_cloud_run", return_value=[]) as mock_run, \
                 patch.object(scanner, "_scan_cloud_functions", return_value=[]) as mock_fn, \
                 patch.object(scanner, "_scan_gke", return_value=[]) as mock_gke, \
                 patch.object(scanner, "_scan_vertex_ai", return_value=[]) as mock_vertex:
                
                res = scanner.run_scan()
                assert mock_run.called
                assert mock_fn.called
                assert mock_gke.called
                assert mock_vertex.called


def test_scanner_gcp_creds_set_via_adc_probing():
    # Clear env but mock google.auth.default to succeed.
    # We clear env so GOOGLE_APPLICATION_CREDENTIALS is not set.
    # We patch "PYTEST_CURRENT_TEST" out of os.environ inside scanner's check to test the probe.
    scanner = GCPScanner(project_id="test-project", db_session=MagicMock())
    
    with patch("app.services.scanner.GCP_SDK_AVAILABLE", True), \
         patch("google.auth.default", return_value=(MagicMock(), "test-project")) as mock_default, \
         patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": ""}), \
         patch.object(scanner, "_scan_cloud_run", return_value=[]), \
         patch.object(scanner, "_scan_cloud_functions", return_value=[]), \
         patch.object(scanner, "_scan_gke", return_value=[]), \
         patch.object(scanner, "_scan_vertex_ai", return_value=[]):
        
        # We patch dict to remove PYTEST_CURRENT_TEST and GOOGLE_APPLICATION_CREDENTIALS
        env_mock = {"GCP_PROJECT_ID": "test-project"}
        with patch("os.environ", env_mock):
            res = scanner.run_scan()
            assert mock_default.called


def test_scan_cloud_run_regions():
    scanner = GCPScanner(project_id="test-project", db_session=MagicMock())
    
    mock_client = MagicMock()
    mock_client.list_services.return_value = []
    
    with patch("google.cloud.run_v2.ServicesClient", return_value=mock_client), \
         patch.dict(os.environ, {"SHADOW_AI_GCP_REGIONS": "us-central1,europe-west1"}):
        
        assets = scanner._scan_cloud_run()
        
        assert mock_client.list_services.call_count == 2
        
        # Verify first call
        first_call_kwargs = mock_client.list_services.call_args_list[0].kwargs
        assert first_call_kwargs['request'].parent == "projects/test-project/locations/us-central1"
        
        # Verify second call
        second_call_kwargs = mock_client.list_services.call_args_list[1].kwargs
        assert second_call_kwargs['request'].parent == "projects/test-project/locations/europe-west1"


def test_scan_vertex_ai_regions():
    scanner = GCPScanner(project_id="test-project", db_session=MagicMock())
    
    mock_endpoint = MagicMock()
    mock_endpoint.list.return_value = []
    
    with patch("app.services.scanner.aiplatform.Endpoint", mock_endpoint), \
         patch.dict(os.environ, {"SHADOW_AI_GCP_REGIONS": "us-central1,europe-west1"}):
        
        assets = scanner._scan_vertex_ai()
        
        assert mock_endpoint.list.call_count == 2
        mock_endpoint.list.assert_any_call(project="test-project", location="us-central1")
        mock_endpoint.list.assert_any_call(project="test-project", location="europe-west1")
