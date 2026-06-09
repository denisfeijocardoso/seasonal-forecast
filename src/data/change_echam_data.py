import xarray as xr 
from pathlib import Path

class EchamScanner:
    """Responsável por localizar arquivos NetCDF do Echam."""

    def __init__(
            self, 
            base_path, 
        ) -> None:

        self.base_path = Path(base_path)

    def get_files_path_year(
            self, 
            year: int,
            pattern: str | None = None,
        ) -> list[Path]:

        """Retorna os caminhos dos arquivos encontrados para o ano."""

        year_path = self.base_path / str(year)

        if pattern is None:
            pattern = str(f"*{year}.nc")

        return sorted(year_path.glob(pattern))


class NetCDFReader:
    """Responsável por abrir datasets NetCDF."""    

    def open_datasets(
        self, 
        paths: list[Path],
    ) -> dict[Path, xr.Dataset]:
        """Abre os arquivos NetCDF e retorna um dicionário path -> dataset."""

        return {
            path: xr.open_dataset(
                path,
                decode_times=False
            )
            for path in paths
        }

class DatasetModifier:
    """Responsável por modificar formato dos datasets."""   

    def replicate_along_time(
        self,
        datasets: dict[Path, xr.Dataset],
    ) -> dict[Path, xr.Dataset]:
        """Replica os dados ao longo da dimensão 'tempo' """
        
        ds_dict = {}

        for path, ds in datasets.items():
            
            if "time" not in ds.dims:
                ds = ds.expand_dims("time").copy(deep=True)

            ds_dict[path] = xr.concat([ds] * 5, dim="time")
        
        return(ds_dict)

class NetCDFWriter:
    """Responsável por escrever os datasets em arquivos NetCDF"""

    def _season_to_init_month(
            self,
            season_target: str,
    ) -> int:
        dict_seasons = {
            "DJF": 11,
            "JFM": 12, 
            "FMA": 1, 
            "MAM": 2, 
            "AMJ": 3, 
            "MJJ": 4, 
            "JJA": 5, 
            "JAS": 6, 
            "ASO": 7, 
            "SON": 8,
            "OND": 9,
            "NDJ":10,
            }
        
        return dict_seasons[season_target]

        
    def _create_new_fname(
            self,
            path_fname: Path,
    ) -> str:
            
            year_fname = (path_fname.stem).split("_")[-1]
            season_fname = (path_fname.stem).split("_")[-2]
            month_fname = self._season_to_init_month(season_fname)
            split_fname = (path_fname.stem).split("_")[:-2]
            base_fname = "_".join(split_fname)

            return(f"{base_fname}_{year_fname}{month_fname:02d}01{path_fname.suffix}")

    def write(
            self,
            ds_dict: dict[Path, xr.Dataset],
            output_dir: Path | None = None,
    ) -> None:
        
        for path, ds in ds_dict.items():
            
            new_file = self._create_new_fname(path)
            
            print(new_file)

            if output_dir is None:
                base_dir = path.parent
            else:
                base_dir = output_dir 

            base_dir.mkdir(parents=True, exist_ok=True)

            new_path = base_dir / new_file

            print("Arquivo gerado:", new_path)
            
            ds.to_netcdf(new_path)


def main() -> None:

    echam_hcst_path = (
        "/dados/mmclima/multimodelo/seasonal/forecast/echam46/"
    )

    scanner = EchamScanner(
        echam_hcst_path, 
    )

    reader = NetCDFReader()

    modifier = DatasetModifier()

    writer = NetCDFWriter()

    years = [2016, 2025]

    for year in years:

        #scaneia arquivos na pasta year de base_path
        paths = scanner.get_files_path_year(year)

        #lê arquivos netcdf
        original_datasets = reader.open_datasets(paths)

        #replica dimensões e escreve novo arquivo
        new_datasets = modifier.replicate_along_time(original_datasets)
        writer.write(new_datasets)

if __name__ == "__main__":

    main()