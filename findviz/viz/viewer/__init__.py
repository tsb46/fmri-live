"""
FINDVIZ Viewer Module

This module provides functionality for managing and visualizing neuroimaging data.
It includes components for handling both NIFTI and GIFTI data formats, as well as
supporting time series and task design data visualization.

Components:
    - data_manager: Singleton class for managing visualization state
    - types: Type definitions for visualization states and data structures
    - utils: Utility functions for data processing and metadata extraction

Example:
    >>> from findviz.viz.viewer import data_manager
    >>> dm = data_manager.DataManager()
    >>> dm.create_nifti_state(func_img=nifti_img)
"""

from findviz.viz.viewer.utils import (
    get_minmax,
    package_gii_metadata,
    package_nii_metadata
)

from findviz.viz.viewer.types import (
    ViewerMetadataNiftiDict,
    ViewerMetadataGiftiDict,
    ViewerDataNiftiDict,
    ViewerDataGiftiDict
)

from findviz.viz.viewer.data_manager import DataManager

__all__ = [
    # Data Manager
    'DataManager',
    
    # Type Definitions
    'ViewerMetadataNiftiDict',
    'ViewerMetadataGiftiDict',
    'ViewerDataNiftiDict',
    'ViewerDataGiftiDict',
    
    # Utility Functions
    'get_minmax',
    'package_gii_metadata',
    'package_nii_metadata'
] 