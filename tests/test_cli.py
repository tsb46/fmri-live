import pytest
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

from findviz.cli import parse_args, process_cli_inputs, find_free_port, validate_files
from findviz.viz.io.upload import FileUpload
from findviz.viz import exception

# Test data paths
TEST_DATA = Path(__file__).parent / "data"
NIFTI_FUNC = TEST_DATA / "test_func.nii.gz"
NIFTI_ANAT = TEST_DATA / "test_anat.nii.gz"
NIFTI_MASK = TEST_DATA / "test_mask.nii.gz"
GIFTI_LEFT_FUNC = TEST_DATA / "test_left.func.gii"
GIFTI_RIGHT_FUNC = TEST_DATA / "test_right.func.gii"
GIFTI_LEFT_MESH = TEST_DATA / "test_left.surf.gii"
GIFTI_RIGHT_MESH = TEST_DATA / "test_right.surf.gii"
TIMESERIES = TEST_DATA / "test_timeseries.csv"
TASK_DESIGN = TEST_DATA / "test_task.tsv"

@pytest.fixture
def mock_cache():
    """Mock Cache class"""
    with patch('findviz.viz.io.cache.Cache') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_file_upload():
    """Mock FileUpload class"""
    with patch('findviz.cli.FileUpload', autospec=True) as mock:
        instance = mock.return_value
        instance.upload.return_value = {
            'file_type': 'mock_type',
            'data': 'mock_data'
        }
        yield instance

@pytest.fixture
def mock_file_exists():
    """Mock os.path.exists to always return True for test files"""
    with patch('os.path.exists') as mock:
        def side_effect(path):
            # Return True for our test paths, False otherwise
            test_paths = [
                str(NIFTI_FUNC), str(NIFTI_ANAT), str(NIFTI_MASK),
                str(GIFTI_LEFT_FUNC), str(GIFTI_RIGHT_FUNC),
                str(GIFTI_LEFT_MESH), str(GIFTI_RIGHT_MESH),
                str(TIMESERIES), str(TASK_DESIGN)
            ]
            return path in test_paths
        mock.side_effect = side_effect
        yield mock

def test_process_cli_inputs_nifti(mock_file_upload, mock_cache, mock_file_exists):
    """Test processing NIFTI inputs"""
    with patch('findviz.cli.FileUpload') as mock_class:
        mock_class.return_value = mock_file_upload
        
        args = argparse.Namespace(
            nifti_func=str(NIFTI_FUNC),
            nifti_anat=str(NIFTI_ANAT),
            nifti_mask=str(NIFTI_MASK),
            gifti_left_func=None,
            gifti_right_func=None,
            gifti_left_mesh=None,
            gifti_right_mesh=None,
            timeseries=None,
            ts_labels=None,
            ts_headers=None,
            task_design=None,
            tr=2.0,
            slicetime_ref=0.5
        )
        
        process_cli_inputs(args)
        
        # Verify FileUpload was called correctly
        mock_file_upload.upload.assert_called_once()
        call_args = mock_file_upload.upload.call_args[1]

        assert call_args['fmri_files']['nii_func'] == str(NIFTI_FUNC)
        assert call_args['fmri_files']['nii_anat'] == str(NIFTI_ANAT)
        assert call_args['fmri_files']['nii_mask'] == str(NIFTI_MASK)

def test_process_cli_inputs_gifti(mock_file_upload, mock_cache, mock_file_exists):
    """Test processing GIFTI inputs"""
    with patch('findviz.cli.FileUpload') as mock_class:
        mock_class.return_value = mock_file_upload
        
        args = argparse.Namespace(
            nifti_func=None,
            nifti_anat=None,
            nifti_mask=None,
            gifti_left_func=str(GIFTI_LEFT_FUNC),
            gifti_right_func=str(GIFTI_RIGHT_FUNC),
            gifti_left_mesh=str(GIFTI_LEFT_MESH),
            gifti_right_mesh=str(GIFTI_RIGHT_MESH),
            timeseries=None,
            ts_labels=None,
            ts_headers=None,
            task_design=None,
            tr=None,
            slicetime_ref=0.5
        )
        
        process_cli_inputs(args)
        
        # Verify FileUpload was called correctly
        mock_file_upload.upload.assert_called_once()
        call_args = mock_file_upload.upload.call_args[1]
        assert call_args['fmri_files']['left_gii_func'] == str(GIFTI_LEFT_FUNC)
        assert call_args['fmri_files']['right_gii_func'] == str(GIFTI_RIGHT_FUNC)

def test_mutually_exclusive_inputs():
    """Test that NIFTI and GIFTI inputs are mutually exclusive"""
    test_args = [
        '--nifti-func', str(NIFTI_FUNC),
        '--gifti-left-func', str(GIFTI_LEFT_FUNC)
    ]
    
    with patch('sys.argv', ['findviz'] + test_args):
        with pytest.raises(exception.FileInputError) as exc_info:
            parse_args()

def test_process_cli_inputs_validation_error(mock_file_upload, mock_cache, mock_file_exists):
    """Test handling of validation errors"""
    with patch('findviz.cli.FileUpload') as mock_class:
        mock_class.return_value = mock_file_upload
        mock_file_upload.upload.side_effect = exception.FileValidationError(
            "Invalid file", "test_validation", "nifti", ["field"]
        )
        
        args = argparse.Namespace(
            nifti_func=str(NIFTI_FUNC),
            nifti_anat=None,
            nifti_mask=None,
            gifti_left_func=None,
            gifti_right_func=None,
            gifti_left_mesh=None,
            gifti_right_mesh=None,
            timeseries=None,
            ts_labels=None,
            ts_headers=None,
            task_design=None,
            tr=None,
            slicetime_ref=0.5
        )

        with pytest.raises(exception.FileValidationError):
            process_cli_inputs(args)

def test_parse_args_nifti():
    """Test parsing NIFTI command line arguments"""
    test_args = [
        '--nifti-func', str(NIFTI_FUNC),
        '--nifti-anat', str(NIFTI_ANAT),
        '--nifti-mask', str(NIFTI_MASK),
        '--tr', '2.0',
        '--slicetime-ref', '0.5'
    ]
    
    with patch('sys.argv', ['findviz'] + test_args):
        args = parse_args()
        
    assert args.nifti_func == str(NIFTI_FUNC)
    assert args.nifti_anat == str(NIFTI_ANAT)
    assert args.nifti_mask == str(NIFTI_MASK)
    assert args.tr == 2.0
    assert args.slicetime_ref == 0.5

def test_parse_args_gifti():
    """Test parsing GIFTI command line arguments"""
    test_args = [
        '--gifti-left-func', str(GIFTI_LEFT_FUNC),
        '--gifti-right-func', str(GIFTI_RIGHT_FUNC),
        '--gifti-left-mesh', str(GIFTI_LEFT_MESH),
        '--gifti-right-mesh', str(GIFTI_RIGHT_MESH)
    ]
    
    with patch('sys.argv', ['findviz'] + test_args):
        args = parse_args()
        
    assert args.gifti_left_func == str(GIFTI_LEFT_FUNC)
    assert args.gifti_right_func == str(GIFTI_RIGHT_FUNC)
    assert args.gifti_left_mesh == str(GIFTI_LEFT_MESH)
    assert args.gifti_right_mesh == str(GIFTI_RIGHT_MESH)

def test_parse_args_timeseries():
    """Test parsing timeseries arguments"""
    test_args = [
        '--nifti-func', str(NIFTI_FUNC),
        '--timeseries', str(TIMESERIES), str(TIMESERIES),
        '--ts-labels', 'ts1', 'ts2',
        '--ts-headers', 'true', 'false'
    ]
    
    with patch('sys.argv', ['findviz'] + test_args):
        args = parse_args()
        
    assert args.timeseries == [str(TIMESERIES), str(TIMESERIES)]
    assert args.ts_labels == ['ts1', 'ts2']
    assert args.ts_headers == ['true', 'false']


def test_validate_files():
    """Test validation of file existence"""
    with patch('os.path.exists') as mock_exists:
        # Test when all files exist
        mock_exists.return_value = True
        files = {
            'file1': '/path/to/file1',
            'file2': '/path/to/file2'
        }
        validate_files(files)  # Should not raise any exception

        # Test when some files don't exist
        mock_exists.side_effect = lambda x: x == '/path/to/file1'
        files = {
            'file1': '/path/to/file1',
            'file2': '/path/to/file2'
        }
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_files(files)
        assert '/path/to/file2' in str(exc_info.value)

        # Test with None values in dictionary
        mock_exists.return_value = True
        files = {
            'file1': '/path/to/file1',
            'file2': None
        }
        validate_files(files)  # Should not raise any exception

        # Test with empty dictionary
        files = {}
        validate_files(files)  # Should not raise any exception

        # Test with all None values
        files = {
            'file1': None,
            'file2': None
        }
        validate_files(files)  # Should not raise any exception

        # Test multiple missing files
        mock_exists.return_value = False
        files = {
            'file1': '/path/to/file1',
            'file2': '/path/to/file2',
            'file3': '/path/to/file3'
        }
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_files(files)

def test_find_free_port():
    """Test finding an available port"""
    port = find_free_port()
    assert isinstance(port, int)
    assert port > 0