from typing import Optional,Any


class ExternalMetadataAdapterSchema:
    def __init__(self, tracking = None, um_name = None, um_name_rollover_threshold = 0, use_model_to_detect_weld = False) -> None:
        self.tracking: int | None = tracking
        self.um_name: str | None = um_name
        self.um_name_rollover_threshold: int = 0
        self.use_model_to_detect_weld: bool = use_model_to_detect_weld
       
        if self.tracking is not None and not isinstance(self.tracking, int):
            raise TypeError("tracking must be int | None")
        if self.um_name is not None and not isinstance(self.um_name, str):
            raise TypeError("um_name must be str | None")
        if not isinstance(self.um_name_rollover_threshold, int):
            raise TypeError("um_name_rollover_threshold must be int")
        if not isinstance(self.use_model_to_detect_weld, bool):
            raise TypeError("um_name_rollover_threshold must be bool")
        
        self.show_live_metadata: dict[str, Any] = {}
        self.show_live_technical_metadata: dict[str, Any] = {}
        self.save_frame_metadata: dict[str, Any] = {}
        self.save_frame_technical_metadata: dict[str, Any] = {}

        
    # === Propriedades com validação ===
    @property
    def show_live_metadata(self) -> dict[str, Any]:
        return self._show_live_metadata

    @show_live_metadata.setter
    def show_live_metadata(self, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise TypeError("show_live_metadata must be a dict")
        self._show_live_metadata = value

    @property
    def show_live_technical_metadata(self) -> dict[str, Any]:
        return self._show_live_technical_metadata

    @show_live_technical_metadata.setter
    def show_live_technical_metadata(self, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise TypeError("show_live_technical_metadata must be a dict")
        self._show_live_technical_metadata = value

    @property
    def save_frame_metadata(self) -> dict[str, Any]:
        return self._save_frame_metadata

    @save_frame_metadata.setter
    def save_frame_metadata(self, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise TypeError("save_frame_metadata must be a dict")
        self._save_frame_metadata = value

    @property
    def save_frame_technical_metadata(self) -> dict[str, Any]:
        return self._save_frame_technical_metadata

    @save_frame_technical_metadata.setter
    def save_frame_technical_metadata(self, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise TypeError("save_frame_technical_metadata must be a dict")
        self._save_frame_technical_metadata = value

    def __str__(self):
        return (
            f"ExternalMetadataAdapterSchema(\n"
            f"  tracking={self.tracking},\n"
            f"  um_name={self.um_name},\n"
            f"  um_name_rollover_threshold={self.um_name_rollover_threshold},\n"
            f"  use_model_to_detect_weld={self.use_model_to_detect_weld},\n"
            f"  show_live_metadata={self.show_live_metadata},\n"
            f"  show_live_technical_metadata={self.show_live_technical_metadata},\n"
            f"  save_frame_metadata={self.save_frame_metadata},\n"
            f"  save_frame_technical_metadata={self.save_frame_technical_metadata}\n"
            f")"
        )