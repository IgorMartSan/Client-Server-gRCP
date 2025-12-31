import numpy as np
from datetime import datetime, timezone
from typing import Tuple, Optional

class CamModuleMetadata:
    """
    Stores grayscale camera data internally as a 1D vector,
    but exposes a 2D matrix for the user.
    """

    def __init__(self, mode: str):
        """
        Initialize the CamMetadata object.

        Args:
            mode (str): Image mode, one of {"Mono8", "Mono12", "Mono12Packed"}.
                Determines dtype/range (e.g., Mono8 → uint8; Mono12 → uint16 [0..4095]).
        """
        self._ALLOWED_MODES = ("Mono8", "Mono12", "Mono12Packed")
        if mode not in self._ALLOWED_MODES:
            raise ValueError(f"mode must be one of {self._ALLOWED_MODES}")

        self._mode: str = mode
        self._vector: Optional[np.ndarray] = None  # always stored as 1D vector
        self._height: Optional[int] = None
        self._width: Optional[int] = None
        self._timestamp: datetime = datetime.now(timezone.utc)

    # ============= SETTER (input: matrix) =============
    def set_image_matrix(self, image_matrix: np.ndarray) -> None:
        """
        Accepts a 2D matrix and stores it internally as a 1D vector.
        """
        if not isinstance(image_matrix, np.ndarray):
            raise TypeError(f"image_matrix must be numpy.ndarray, got {type(image_matrix)}")

        if image_matrix.ndim != 2:
            raise ValueError(f"image_matrix must be 2D, got shape={image_matrix.shape}")

        # ---- Validation based on mode ----
        if self._mode == "Mono8":
            if image_matrix.dtype != np.uint8:
                raise TypeError(f"For Mono8, dtype must be uint8, got {image_matrix.dtype}")

        elif self._mode == "Mono12":
            if image_matrix.dtype != np.uint16:
                raise TypeError(f"For Mono12, dtype must be uint16, got {image_matrix.dtype}")
            if image_matrix.size:
                vmin, vmax = int(image_matrix.min()), int(image_matrix.max())
                if vmin < 0 or vmax > 4095:
                    raise ValueError(
                        f"Mono12 values must be in [0, 4095], got min={vmin}, max={vmax}"
                    )

        elif self._mode == "Mono12Packed":
            raise ValueError("Mono12Packed is not implemented yet.")

        # ---- Store as 1D vector ----
        self._height, self._width = image_matrix.shape
        self._vector = image_matrix.reshape(-1)  # always 1D
        self._timestamp = datetime.now(timezone.utc)

    # ============= GETTER (output: matrix) =============
    @property
    def image_matrix(self) -> np.ndarray:
        """
        Reconstructs the 2D matrix from the stored 1D vector.
        """
        if self._vector is None or self._height is None or self._width is None:
            raise ValueError("No image has been set. Use set_image_matrix(...) first.")
        return self._vector.reshape((self._height, self._width))

    # ============= METADATA =============
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def height(self) -> Optional[int]:
        return self._height

    @property
    def width(self) -> Optional[int]:
        return self._width

    @property
    def vector(self) -> np.ndarray:
        """
        Returns the internal 1D vector directly (useful for transport/storage).
        """
        if self._vector is None:
            raise ValueError("No image has been set.")
        return self._vector

    # ------------ helpers ------------
    def _dtype(self) -> Optional[np.dtype]:
        return None if self._vector is None else self._vector.dtype

    def _size(self) -> int:
        return 0 if self._vector is None else int(self._vector.size)

    def _preview_vector(self, n: int = 8) -> str:
        if self._vector is None or self._vector.size == 0:
            return "[]"
        arr = self._vector
        if arr.size <= n:
            return np.array2string(arr, threshold=n)
        head = np.array2string(arr[:n], threshold=n)
        return head[:-1] + ", ...]"

    def __repr__(self) -> str:
        return (
            f"CamModuleMetadata(mode={self._mode!r}, "
            f"height={self._height}, width={self._width}, "
            f"dtype={self._dtype()}, size={self._size()}, "
            f"timestamp={self._timestamp.isoformat()})"
        )

    def __str__(self) -> str:
        return (
            "CamModuleMetadata\n"
            f"  mode:       {self._mode}\n"
            f"  height:     {self._height}\n"
            f"  width:      {self._width}\n"
            f"  dtype:      {self._dtype()}\n"
            f"  size:       {self._size()} px\n"
            f"  timestamp:  {self._timestamp.isoformat()}\n"
            f"  vector[0..]: {self._preview_vector(8)}"
        )
