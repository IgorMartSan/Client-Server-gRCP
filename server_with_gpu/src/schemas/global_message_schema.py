
from schemas.cam_module_schema import CamModuleMetadata
from schemas.fast_process_module_schema import FastProcessMetadata
from schemas.collect_data_module_schema import CollectDataModuleMetadata

from typing import Any, Optional



class MessageGlobal:
    def __init__(self) -> None:
        self._cam_module: Optional[CamModuleMetadata] = None
        self._fast_process_module: Optional[FastProcessMetadata] = None
        self._slow_process_module: Optional[CamModuleMetadata] = None
        self._collect_data_module: Optional[CollectDataModuleMetadata] = None

        self._metadata_show_live: dict[str, Any] = {}
        self._metadata_show_live_technical: dict[str, Any] = {}
        self._metadata_save_frame: dict[str, Any] = {}
        self._metadata_save_frame_technical: dict[str, Any] = {}

    # ============ cam_module ============
    @property
    def cam_module(self) -> Optional["CamModuleMetadata"]:
        return self._cam_module

    @cam_module.setter
    def cam_module(self, value: Optional["CamModuleMetadata"]) -> None:
        if value is not None and not isinstance(value, CamModuleMetadata):
            raise TypeError(f"cam_module must be CamModuleMetadata or None, got {type(value)}")
        self._cam_module = value

    # ============ fast_process_module ============
    @property
    def fast_process_module(self) -> Optional["FastProcessMetadata"]:
        return self._fast_process_module

    @fast_process_module.setter
    def fast_process_module(self, value: Optional["FastProcessMetadata"]) -> None:
        if value is not None and not isinstance(value, FastProcessMetadata):
            raise TypeError(f"fast_process_module must be FastProcessMetadata or None, got {type(value)}")
        self._fast_process_module = value

    # ============ slow_process_module ============
    @property
    def slow_process_module(self) -> Optional["CamModuleMetadata"]:
        return self._slow_process_module

    @slow_process_module.setter
    def slow_process_module(self, value: Optional["CamModuleMetadata"]) -> None:
        if value is not None and not isinstance(value, CamModuleMetadata):
            raise TypeError(f"slow_process_module must be CamModuleMetadata or None, got {type(value)}")
        self._slow_process_module = value

    # ============ collect_data_module ============
    @property
    def collect_data_module(self) -> Optional["CollectDataModuleMetadata"]:
        return self._collect_data_module

    @collect_data_module.setter
    def collect_data_module(self, value: Optional["CollectDataModuleMetadata"]) -> None:
        if value is not None and not isinstance(value, CollectDataModuleMetadata):
            raise TypeError(f"collect_data_module must be CollectDataModuleMetadata or None, got {type(value)}")
        self._collect_data_module = value
