import argparse
import os
import socket
import sys
import webbrowser

from threading import Timer

from findviz import create_app
from findviz.logger_config import setup_logger
from findviz.routes.shared import data_manager
from findviz.viz.io import gifti
from findviz.viz.io import nifti
from findviz.viz import exception
from findviz.viz.io.cache import Cache
from findviz.viz.io.upload import FileUpload

logger = setup_logger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='FIND Viewer')
    
    # FMRI file inputs (mutually exclusive group for NIFTI vs GIFTI)
    fmri_group = parser.add_mutually_exclusive_group()
    
    # NIFTI inputs
    nifti_group = fmri_group.add_argument_group('NIFTI inputs')
    nifti_group.add_argument('--nifti-func', help='Functional NIFTI file')
    nifti_group.add_argument('--nifti-anat', help='Anatomical NIFTI file')
    nifti_group.add_argument('--nifti-mask', help='Brain mask NIFTI file')
    
    # GIFTI inputs
    gifti_group = fmri_group.add_argument_group('GIFTI inputs')
    gifti_group.add_argument('--gifti-left-func', help='Left hemisphere functional GIFTI')
    gifti_group.add_argument('--gifti-right-func', help='Right hemisphere functional GIFTI')
    gifti_group.add_argument('--gifti-left-mesh', help='Left hemisphere mesh GIFTI')
    gifti_group.add_argument('--gifti-right-mesh', help='Right hemisphere mesh GIFTI')
    
    # Add a required argument to each group in the mutually exclusive group
    fmri_group.add_argument('--use-nifti', action='store_true', 
                           help=argparse.SUPPRESS)
    fmri_group.add_argument('--use-gifti', action='store_true',
                           help=argparse.SUPPRESS)
    
    # Optional inputs
    parser.add_argument('--timeseries', nargs='+', help='Time series files')
    parser.add_argument('--ts-labels', nargs='+', help='Labels for time series files')
    parser.add_argument('--ts-headers', nargs='+', 
                       help='Whether time series files have headers (true/false)')
    
    parser.add_argument('--task-design', help='Task design file')
    parser.add_argument('--tr', type=float, help='TR value')
    parser.add_argument('--slicetime-ref', type=float, 
                       help='Slice timing reference (0-1)', default=0.5)
    
    args = parser.parse_args()

    # raise FileInputError if both gifti and nifti files are present
    nifti_input = any([args.nifti_func, args.nifti_anat, args.nifti_mask])
    gifti_input = any([
        args.gifti_left_func, args.gifti_right_func, 
        args.gifti_left_mesh, args.gifti_right_mesh
    ])
    if nifti_input & gifti_input:
        raise exception.FileInputError(
            "Nifti and Gifti file uploads are mutually exclusive."
             "Please upload one file type.",
             file_type=exception.ExceptionFileTypes.NIFTI_GIFTI,
             method='cli'
        )
    # Set the appropriate group flag based on which arguments are present
    if nifti_input:
        args.use_nifti = True
    if gifti_input:
        args.use_gifti = True
    return args


def process_cli_inputs(args) -> None:
    """Process and validate CLI inputs using existing validation logic."""
    logger.info("Processing CLI inputs")
    # Determine file type and create FileUpload instance
    if args.nifti_func:
        fmri_type = 'nifti'
        logger.info("Nifti file type detected")
        fmri_files = {
            nifti.NiftiFiles.FUNC.value: args.nifti_func,
            nifti.NiftiFiles.ANAT.value: args.nifti_anat,
            nifti.NiftiFiles.MASK.value: args.nifti_mask
        }
    else:
        fmri_type = 'gifti'
        logger.info("Gifti file type detected")
        fmri_files = {
            gifti.GiftiFiles.LEFT_FUNC.value: args.gifti_left_func,
            gifti.GiftiFiles.RIGHT_FUNC.value: args.gifti_right_func,
            gifti.GiftiFiles.LEFT_MESH.value: args.gifti_left_mesh,
            gifti.GiftiFiles.RIGHT_MESH.value: args.gifti_right_mesh
        }
    
    # Validate that all files exist
    validate_files(fmri_files)
    logger.info("FMRI files validated successfully")

    # Create additional files dict for validation
    additional_files = {}
    if args.timeseries:
        for i, ts_file in enumerate(args.timeseries):
            additional_files[f'timeseries_{i}'] = ts_file
    if args.task_design:
        additional_files['task_design'] = args.task_design
    
    # Validate additional files
    validate_files(additional_files)
    logger.info("Additional files validated successfully")

    # Create FileUpload instance
    file_upload = FileUpload(
        fmri_type,
        ts_status=bool(args.timeseries),
        task_status=bool(args.task_design),
        method='cli'
    )
    logger.info("FileUpload instance initialized")

    # Process files using existing validation logic
    uploads = file_upload.upload(
        fmri_files=fmri_files,
        ts_files=args.timeseries,
        ts_labels=args.ts_labels,
        ts_headers=args.ts_headers,
        task_file=args.task_design,
        tr=args.tr,
        slicetime_ref=args.slicetime_ref
    )

    # pass fmri data to data manager and get viewer data
    if fmri_type == 'nifti':
        data_manager.create_nifti_state(
            func_img = uploads['nifti'][file_upload.Nifti.FUNC.value],
            anat_img = uploads['nifti'][file_upload.Nifti.ANAT.value],
            mask_img = uploads['nifti'][file_upload.Nifti.MASK.value]
        )
        logger.info("Nifti data manager state created successfully")
    else:
        data_manager.create_gifti_state(
            left_func=uploads['gifti'][file_upload.Gifti.LEFT_FUNC.value],
            right_func=uploads['gifti'][file_upload.Gifti.RIGHT_FUNC.value],
            left_mesh=uploads['gifti'][file_upload.Gifti.LEFT_MESH.value],
            right_mesh=uploads['gifti'][file_upload.Gifti.RIGHT_MESH.value]
        )
        logger.info("Gifti data manager state created successfully")
    # if timecourse data, add to viewer data
    if file_upload.ts_status:
        data_manager.add_timeseries(uploads['ts'])
        logger.info("Time series data added to viewer data")

    # if task data, add to viewer data
    if file_upload.task_status:
        data_manager.add_task_design(uploads['task'])
        logger.info("Task design data added to viewer data")

    # get viewer metadata
    viewer_metadata = data_manager.get_viewer_metadata()
    logger.info("Viewer metadata retrieved successfully")

    # Create and save cache
    cache = Cache()
    cache.save(viewer_metadata)


def main():
    args = parse_args()
    # If arguments were provided, process them
    # This doesn't seem robust; might need refactoring
    if len(sys.argv) > 1:
        try:
            process_cli_inputs(args)
        except Exception as e:
            print(f"Error processing inputs: {str(e)}")
            return

    app = create_app()
    port = find_free_port()
    Timer(1, open_browser, args=(port,)).start()
    app.run(debug=False, port=port)


def find_free_port():
    """Find an available port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))  # Bind to any available port
        return s.getsockname()[1]  # Return the port number


def open_browser(port):
    """Open the web browser to the Flask app."""
    webbrowser.open_new(f"http://127.0.0.1:{port}")


def validate_files(files_dict: dict):
    """Validate that all provided files exist.
    
    Arguments:
    ----------
    files_dict (dict): Dictionary of file paths to check
        
    Raises:
    -------
        FileNotFoundError: If any specified file doesn't exist
    """
    missing_files = []
    for name, filepath in files_dict.items():
        if filepath and not os.path.exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        raise FileNotFoundError(
            f"The following files were not found: {', '.join(missing_files)}"
        )