import xarray as xr 
import numpy as np 
from pathlib import Path

class EchamScanner:
    """Responsável por localizar arquivos NetCDF do Echam."""

    def __init__(self, base_path, year) -> None:
        self.base_path = Path(base_path)
        self.year = year

    def get_files_paths(self, pattern: str = "*.nc") -> list[Path]:
        """Retorna os caminhos dos arquivos encontrados para o ano."""

        year_path = self.base_path / str(self.year)

        return sorted(year_path.glob(pattern))

class NetCDFReader:
    """Responsável por abrir datasets NetCDF."""    

    def open_datasets(
        self, 
        paths: list[Path]
        ) -> dict[Path, xr.Dataset]:
        """Abre os arquivos NetCDF e retorna um dicionário path -> dataset."""

        return {
            path: xr.open_dataset(
                path,
                decode_times=False
            )
            for path in paths
        }

def main() -> None:

    echam_hcst_path = (
        "/dados/mmclima/multimodelo/seasonal/hindcast/echam46/"
    )

    scanner = EchamScanner(
        echam_hcst_path, 
        1999,
        )
    
    paths = scanner.get_files_paths()

    reader = NetCDFReader()

    datasets = reader.open_datasets(paths)

    for path, ds in datasets.items():

        print(path)
        print(ds)

if __name__ == "__main__":
    main()