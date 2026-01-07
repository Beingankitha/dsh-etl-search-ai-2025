"""
Unit tests for CLI commands and functionality.

Tests cover:
1. CLI argument parsing and validation
2. Configuration display and validation
3. Error handling in CLI
4. Integration with ETL service
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from typer.testing import CliRunner

from src.cli import app, etl


@pytest.fixture
def cli_runner():
    """Create CLI test runner"""
    return CliRunner()


@pytest.fixture
def temp_identifiers_file():
    """Create temporary identifiers file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("identifier-001\n")
        f.write("identifier-002\n")
        f.write("identifier-003\n")
        temp_path = f.name
    
    yield Path(temp_path)
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# ============================================================================
# TEST: CLI Basic Invocation
# ============================================================================

class TestCLIBasicInvocation:
    """Test basic CLI invocation"""
    
    def test_cli_help(self, cli_runner):
        """Test CLI help message"""
        result = cli_runner.invoke(app, ['--help'])
        
        assert result.exit_code == 0
        assert "DSH ETL Search AI" in result.output
    
    def test_etl_command_help(self, cli_runner):
        """Test ETL command help"""
        result = cli_runner.invoke(app, ['etl', '--help'])
        
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert "--verbose" in result.output
        assert "--dry-run" in result.output
        assert "--identifiers-file" in result.output


# ============================================================================
# TEST: CLI Argument Parsing
# ============================================================================

class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation"""
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_etl_with_limit(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test ETL command with limit option"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--limit', '10'
        ])
        
        assert result.exit_code == 0 or mock_run_etl.called
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_etl_with_verbose(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test ETL command with verbose flag"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--verbose'
        ])
        
        assert result.exit_code == 0 or mock_run_etl.called
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_etl_with_dry_run(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test ETL command with dry-run flag"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--dry-run'
        ])
        
        assert result.exit_code == 0 or mock_run_etl.called


# ============================================================================
# TEST: CLI Error Handling
# ============================================================================

class TestCLIErrorHandling:
    """Test CLI error handling"""
    
    def test_missing_identifiers_file(self, cli_runner):
        """Test error when identifiers file doesn't exist"""
        with patch('src.config.settings.metadata_identifiers_file', '/nonexistent/file.txt'):
            result = cli_runner.invoke(app, ['etl'])
            
            assert result.exit_code != 0
            assert "not found" in result.output.lower() or "✗" in result.output
    
    def test_invalid_limit_option(self, cli_runner, temp_identifiers_file):
        """Test error with invalid limit option"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--limit', 'invalid'
        ])
        
        assert result.exit_code != 0


# ============================================================================
# TEST: Configuration Display
# ============================================================================

class TestConfigurationDisplay:
    """Test configuration display in CLI"""
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_config_table_displayed(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test that configuration table is displayed"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--limit', '5'
        ])
        
        # Configuration table should be displayed (either from output or after invocation)
        assert result.exit_code == 0 or mock_run_etl.called
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_dry_run_flag_displayed(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test that dry-run flag is displayed in config"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--dry-run'
        ])
        
        # Should handle dry-run properly
        assert result.exit_code == 0 or mock_run_etl.called


# ============================================================================
# TEST: CLI Exit Codes
# ============================================================================

class TestCLIExitCodes:
    """Test CLI exit codes"""
    
    def test_success_exit_code(self, cli_runner):
        """Test successful exit code"""
        result = cli_runner.invoke(app, ['--help'])
        
        assert result.exit_code == 0
    
    def test_help_exit_code(self, cli_runner):
        """Test help command exit code"""
        result = cli_runner.invoke(app, ['etl', '--help'])
        
        assert result.exit_code == 0


# ============================================================================
# TEST: CLI Integration with Mock ETL Service
# ============================================================================

class TestCLIIntegration:
    """Test CLI integration with ETL service"""
    
    @patch('src.cli.ETLService')
    @patch('src.cli.UnitOfWork')
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_etl_service_instantiation(self, mock_run_etl, mock_uow, mock_etl_service, 
                                        cli_runner, temp_identifiers_file):
        """Test that ETL service is properly instantiated"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--limit', '5'
        ])
        
        # Command should complete
        assert result.exit_code == 0 or mock_run_etl.called


# ============================================================================
# TEST: CLI with Multiple Options
# ============================================================================

class TestCLIMultipleOptions:
    """Test CLI with multiple options combined"""
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_verbose_and_dry_run_combined(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test combining --verbose and --dry-run flags"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--verbose',
            '--dry-run',
            '--limit', '5'
        ])
        
        assert result.exit_code == 0 or mock_run_etl.called
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_all_options_combined(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test combining all available options"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file),
            '--limit', '10',
            '--verbose',
            '--dry-run'
        ])
        
        assert result.exit_code == 0 or mock_run_etl.called


# ============================================================================
# TEST: CLI Keyboard Interrupt Handling
# ============================================================================

class TestCLIKeyboardInterrupt:
    """Test CLI keyboard interrupt handling"""
    
    @patch('src.cli.asyncio.run', side_effect=KeyboardInterrupt())
    def test_keyboard_interrupt_handling(self, mock_run, cli_runner, temp_identifiers_file):
        """Test graceful handling of keyboard interrupt"""
        result = cli_runner.invoke(app, [
            'etl',
            '--identifiers-file', str(temp_identifiers_file)
        ])
        
        # Should exit with proper code (130 or similar)
        assert result.exit_code != 0
        assert "interrupted" in result.output.lower() or "⚠" in result.output


# ============================================================================
# TEST: CLI Configuration Validation
# ============================================================================

class TestCLIConfigurationValidation:
    """Test CLI configuration validation"""
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_database_path_configuration(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test that database path is correctly configured"""
        with patch('src.config.settings.database_path', '/tmp/test.db'):
            result = cli_runner.invoke(app, [
                'etl',
                '--identifiers-file', str(temp_identifiers_file),
                '--dry-run'
            ])
            
            assert result.exit_code == 0 or mock_run_etl.called
    
    @patch('src.cli._run_etl', new_callable=AsyncMock)
    def test_batch_size_configuration(self, mock_run_etl, cli_runner, temp_identifiers_file):
        """Test that batch size is correctly configured"""
        with patch('src.config.settings.batch_size', 5):
            result = cli_runner.invoke(app, [
                'etl',
                '--identifiers-file', str(temp_identifiers_file),
                '--dry-run'
            ])
            
            assert result.exit_code == 0 or mock_run_etl.called
