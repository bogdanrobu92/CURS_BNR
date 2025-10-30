"""
Performance tests for BNR Exchange Rate Monitor.
"""
import pytest
import time
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_bnr_api_rate, job, create_secure_session


class TestPerformance:
    """Test performance characteristics."""
    
    def test_api_response_time(self, mock_bnr_xml_response):
        """Test API response time is within acceptable limits."""
        with patch('main.create_secure_session') as mock_create_session:
            # Setup mock session
            mock_session = Mock()
            mock_response = Mock()
            mock_response.content = mock_bnr_xml_response.encode('utf-8')
            mock_response.raise_for_status.return_value = None
            mock_session.get.return_value = mock_response
            mock_create_session.return_value = mock_session
            
            # Measure response time
            start_time = time.time()
            rate = get_bnr_api_rate('EUR')
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Should complete within 1 second (mocked)
            assert response_time < 1.0
            assert rate == 4.9500
            assert isinstance(rate, float)
    
    def test_job_execution_time(self, sample_rates_data):
        """Test job execution time is within acceptable limits."""
        with patch('main.get_bnr_api_rate') as mock_get_rate, \
             patch('main.send_email') as mock_send_email:
            
            # Setup mocks
            mock_get_rate.side_effect = lambda currency: sample_rates_data.get(currency)
            mock_send_email.return_value = True
            
            # Measure execution time
            start_time = time.time()
            result = job()
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Should complete within 5 seconds (mocked)
            assert execution_time < 5.0
            assert result is True
    
    def test_memory_usage(self, mock_bnr_xml_response):
        """Test memory usage is reasonable."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        with patch('main.create_secure_session') as mock_create_session:
            # Setup mock session
            mock_session = Mock()
            mock_response = Mock()
            mock_response.content = mock_bnr_xml_response.encode('utf-8')
            mock_response.raise_for_status.return_value = None
            mock_session.get.return_value = mock_response
            mock_create_session.return_value = mock_session
            
            # Execute multiple API calls
            for _ in range(10):
                get_bnr_api_rate('EUR')
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be less than 10MB
            assert memory_increase < 10 * 1024 * 1024
    
    def test_concurrent_requests(self, mock_bnr_xml_response):
        """Test handling of concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker():
            with patch('main.create_secure_session') as mock_create_session:
                # Setup mock session
                mock_session = Mock()
                mock_response = Mock()
                mock_response.content = mock_bnr_xml_response.encode('utf-8')
                mock_response.raise_for_status.return_value = None
                mock_session.get.return_value = mock_response
                mock_create_session.return_value = mock_session
                
                rate = get_bnr_api_rate('EUR')
                results.put(rate)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert results.qsize() == 5
        while not results.empty():
            assert results.get() == '4.9500'
    
    def test_session_reuse_efficiency(self):
        """Test that session creation is efficient."""
        start_time = time.time()
        
        # Create multiple sessions
        sessions = []
        for _ in range(10):
            session = create_secure_session()
            sessions.append(session)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Session creation should be fast
        assert creation_time < 1.0
        assert len(sessions) == 10
        
        # Clean up sessions
        for session in sessions:
            session.close()
    
    @pytest.mark.slow
    def test_load_testing(self, sample_rates_data):
        """Load test the job function."""
        with patch('main.get_bnr_api_rate') as mock_get_rate, \
             patch('main.send_email') as mock_send_email:
            
            # Setup mocks
            mock_get_rate.side_effect = lambda currency: sample_rates_data.get(currency)
            mock_send_email.return_value = True
            
            # Execute job multiple times
            start_time = time.time()
            success_count = 0
            
            for _ in range(50):  # Run 50 iterations
                result = job()
                if result:
                    success_count += 1
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Should complete within reasonable time
            assert total_time < 30.0  # 30 seconds for 50 iterations
            assert success_count == 50  # All should succeed
            assert mock_send_email.call_count == 50
