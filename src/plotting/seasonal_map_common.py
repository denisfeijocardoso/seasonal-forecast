from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import numpy as np

from src.config.paths import PATH_FIG, PATH_POSPROC

logger = logging.getLogger(__name__)

TOOLS_FORECAST = Path("/scripts/clima/produtos/site_forecast/tools")
TOOLS_VERIFICATION = Path("/scripts/subsaz/tools")
BRAZIL_UF_SHAPE = Path(__file__).parent / "shapes" / "BR_UF_2022.shp"
HORIZONTAL_COLORBAR_REGIONS = {"gl", "ne", "pa", "se", "tr"}


@dataclass(frozen=True)
class MapStyle:
    title: str
    levels: tuple[float, ...]
    color_ids: tuple[int, ...]
    factor: float = 1.0
    draw_contours: bool = False
    tercile_colorbar_labels: bool = False
    colorbar_extend: str = "both"
    palette_files: tuple[str, ...] = ()
    compact_colorbar_ticks: bool = False


@dataclass(frozen=True)
class Region:
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    x_tick: float
    y_tick: float


REGIONS: tuple[Region, ...] = (
    Region("af", -40, 40, -30, 60, 15, 15),
    Region("aa", -10, 80, 65, 180, 15, 15),
    Region("au", -50, 25, 110, 190, 15, 15),
    Region("eu", 30, 80, -30, 60, 15, 15),
    Region("an", -10, 70, -170, -50, 15, 15),
    Region("pa", -30, 30, -260, -70, 15, 15),
    Region("ne", 20, 80, 0, 360, 45, 15),
    Region("se", -80, -20, 0, 360, 45, 15),
    Region("tr", -20, 20, 0, 360, 45, 15),
    Region("gl", -70, 70, 0, 360, 30, 30),
    Region("am", -22, 6, -82, -47, 5, 5),
    Region("as", -60, 15, -90, -30, 10, 10),
)

BASE_PREFIX = {
    "nmme": "nmme",
    "copernicus": "c3s",
}

MULTIMODEL_BASE_PREFIX = {
    "nmme": "nmme",
    "copernicus": "c3s",
}

CLIMATOLOGY_LABELS = {
    "nmme": "1991 - 2020",
    "copernicus": "1993 - 2016",
}


def require_plotting_dependencies() -> None:
    missing = []

    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        missing.append("matplotlib")

    try:
        import xarray  # noqa: F401
    except ModuleNotFoundError:
        missing.append("xarray")

    if missing:
        deps = ", ".join(missing)
        raise RuntimeError(
            f"Dependencias de plotagem ausentes: {deps}. "
            "Instale o requirements.txt antes de gerar mapas em Python."
        )


def normalize_version(base: str) -> str:
    from src.config.config_models import get_multimodel_version

    version = get_multimodel_version(base)
    return version if version.startswith("v") else f"v{version}"


def calibration_file_suffix(calibration: str) -> str:
    if calibration == "nocalib":
        return "nocalib"
    return f"calibrated_{calibration}"


def calibration_output_suffix(calibration: str) -> str:
    return "nocalib" if calibration == "nocalib" else calibration


def forecast_date(year: int, month: int) -> str:
    return f"{year}{month:02d}0100"


def input_dir(
    base: str,
    product_type: str,
    calibration: str,
    model_dir: str,
    year: int | None = None,
    month: int | None = None,
) -> Path:
    path = (
        PATH_POSPROC
        / base
        / normalize_version(base)
        / product_type
        / calibration
        / model_dir
    )
    if year is not None and month is not None:
        path = path / str(year) / forecast_date(year, month)
    return path


def output_dir(
    base: str,
    product_type: str,
    calibration: str,
    model_dir: str,
    year: int | None = None,
    month: int | None = None,
) -> Path:
    path = (
        PATH_FIG
        / base
        / normalize_version(base)
        / product_type
        / calibration
        / model_dir
    )
    if year is not None and month is not None:
        path = path / str(year) / forecast_date(year, month)
    return path


def build_model_labels(model: str) -> tuple[str, str]:
    from src.config.config_models import build_model_dir_name, build_model_title

    return build_model_dir_name(model), build_model_title(model)


def parse_grads_rgb(
    tool_dir: Path,
    file_names: Iterable[str] | None = None,
) -> dict[int, tuple[float, float, float]]:
    rgb: dict[int, tuple[float, float, float]] = {
        0: (1.0, 1.0, 1.0),
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (0.0, 0.86, 0.0),
        4: (0.0, 0.0, 1.0),
        5: (0.0, 1.0, 1.0),
        6: (1.0, 0.0, 1.0),
        7: (1.0, 1.0, 0.0),
        8: (1.0, 0.65, 0.0),
        9: (0.63, 0.13, 0.94),
        10: (0.6, 0.8, 0.2),
        11: (0.0, 0.0, 0.8),
        12: (0.8, 0.6, 0.0),
        13: (0.0, 0.8, 0.8),
        14: (0.55, 0.0, 0.55),
        15: (0.8, 0.8, 0.8),
    }

    names = tuple(file_names) if file_names is not None else ("ccrgb.gs",)
    for name in names:
        path = tool_dir / name
        if not path.exists():
            continue

        for line in path.read_text(errors="ignore").splitlines():
            if line.lstrip().startswith("*"):
                continue
            match = re.search(
                r"set\s+rgb\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
                line,
                re.IGNORECASE,
            )
            if not match:
                continue
            color_id, red, green, blue = (int(value) for value in match.groups())
            rgb[color_id] = (red / 255.0, green / 255.0, blue / 255.0)

    return rgb


def colors_from_ids(
    color_ids: Iterable[int],
    palette: dict[int, tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    return [palette.get(color_id, (1.0, 1.0, 1.0)) for color_id in color_ids]


def history_title(ds: xr.Dataset, forecast: bool) -> str:
    history = str(ds.attrs.get("history", "")).replace(":", "")
    parts = history.split()

    if len(parts) >= 6 and parts[0].upper() == "ISSUED":
        issued = " ".join(parts[1:3])
        valid = " ".join(parts[4:6])
    else:
        issued = ""
        valid = ""

    if forecast:
        return f"FORECAST ISSUED {issued} FOR {valid}".strip()
    return f"ISSUED: {issued} VALID FOR {valid}".strip()


def open_product_data(path: Path, variable_name: str) -> tuple[xr.Dataset, xr.DataArray]:
    import xarray as xr

    ds = xr.open_dataset(path, decode_times=False)
    if variable_name in ds.data_vars:
        da = ds[variable_name]
    elif len(ds.data_vars) == 1:
        da = ds[next(iter(ds.data_vars))]
    else:
        ds.close()
        raise ValueError(f"Variavel {variable_name!r} nao encontrada em {path}")

    da = da.squeeze(drop=True)
    for dim in list(da.dims):
        if dim not in {"lat", "lon"}:
            da = da.isel({dim: 0}, drop=True)

    return ds, da


def prepare_region_data(da: xr.DataArray, region: Region) -> xr.DataArray:
    import xarray as xr

    if "lat" not in da.coords or "lon" not in da.coords:
        raise ValueError("DataArray precisa ter coordenadas lat e lon")

    data = da
    lon_min, lon_max = _region_lon_bounds(region)

    lon = data["lon"]
    if _covers_full_longitude(region):
        data = data.assign_coords(lon=(lon % 360))
        lon_min, lon_max = 0.0, 360.0
    elif _use_minus_180_to_180(region):
        data = data.assign_coords(lon=(((lon + 180) % 360) - 180))
        lon_min, lon_max = region.lon_min, region.lon_max
    else:
        data = data.assign_coords(lon=(lon % 360))

    data = data.sortby("lon")
    data = _drop_duplicate_coord(data, "lon")
    if float(data["lat"][0]) > float(data["lat"][-1]):
        data = data.sortby("lat")
    data = _drop_duplicate_coord(data, "lat")

    lat_slice = slice(region.lat_min, region.lat_max)
    if lon_min <= lon_max:
        selected = data.sel(lat=lat_slice, lon=slice(lon_min, lon_max))
        if _covers_full_longitude(region):
            return _add_cyclic_longitude(selected)
        return selected

    left = data.sel(lat=lat_slice, lon=slice(lon_min, 360))
    right = data.sel(lat=lat_slice, lon=slice(0, lon_max))
    selected = xr.concat([left, right], dim="lon")
    if _covers_full_longitude(region):
        return _add_cyclic_longitude(selected)
    return selected


def _region_lon_bounds(region: Region) -> tuple[float, float]:
    lon_min = region.lon_min % 360
    lon_max = region.lon_max % 360
    if region.lon_min == 0 and region.lon_max == 360:
        return 0.0, 360.0
    return lon_min, lon_max


def _use_minus_180_to_180(region: Region) -> bool:
    if region.lon_min < -180 or region.lon_max > 180:
        return False
    if region.lon_min == 0 and region.lon_max == 360:
        return False
    return region.lon_min < 0


def _covers_full_longitude(region: Region) -> bool:
    return math.isclose(region.lon_max - region.lon_min, 360.0)


def _drop_duplicate_coord(da: xr.DataArray, coord: str) -> xr.DataArray:
    values = np.asarray(da[coord].values)
    _, indices = np.unique(values, return_index=True)
    if len(indices) == len(values):
        return da
    return da.isel({coord: np.sort(indices)})


def _add_cyclic_longitude(da: xr.DataArray) -> xr.DataArray:
    import xarray as xr

    if da.sizes.get("lon", 0) < 2:
        return da

    lon = np.asarray(da["lon"].values, dtype=float)
    target_end = float(lon[0] + 360.0)
    if lon[-1] >= target_end or math.isclose(lon[-1], target_end):
        return da

    cyclic = da.isel(lon=[0]).assign_coords(lon=[target_end])
    return xr.concat([da, cyclic], dim="lon")


def render_map(
    da: xr.DataArray,
    region: Region,
    style: MapStyle,
    output_file: Path,
    title_lines: tuple[str, str, str],
    palette: dict[int, tuple[float, float, float]],
    skip_existing: bool = True,
) -> bool:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    require_plotting_dependencies()

    if skip_existing and output_file.exists():
        logger.info("Arquivo ja existe, pulando: %s", output_file)
        return False

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.ticker import FuncFormatter

    plot_da = prepare_region_data(da, region) * style.factor
    x_min, x_max = _plot_extent(region)
    plot_da = _interpolate_for_display(plot_da, region, x_min, x_max)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    colors = colors_from_ids(style.color_ids, palette)
    bounds = [float(value) for value in style.levels]
    regular_colors, under_color, over_color = _colorbar_colors(style, colors)
    cmap = ListedColormap(regular_colors)
    if under_color is not None:
        cmap.set_under(under_color)
    if over_color is not None:
        cmap.set_over(over_color)
    norm = BoundaryNorm(bounds, cmap.N)
    colorbar_orientation = _colorbar_orientation(region)

    projection = None
    transform = None
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        projection = ccrs.PlateCarree(central_longitude=_central_longitude(region))
        transform = ccrs.PlateCarree()
    except ModuleNotFoundError:
        ccrs = None
        cfeature = None

    fig = plt.figure(figsize=(10.5, 8.0), dpi=150)
    ax = fig.add_subplot(1, 1, 1, projection=projection) if projection else fig.add_subplot(1, 1, 1)

    lon = plot_da["lon"].values
    lat = plot_da["lat"].values
    values = np.ma.masked_invalid(np.asarray(plot_da.values))

    mesh_kwargs = {
        "levels": bounds,
        "cmap": cmap,
        "norm": norm,
        "extend": style.colorbar_extend,
        "antialiased": True,
    }
    if transform:
        mesh_kwargs["transform"] = transform

    mesh = ax.contourf(lon, lat, values, **mesh_kwargs)

    if style.draw_contours:
        contour_kwargs = {"levels": style.levels, "colors": "black", "linewidths": 0.45}
        if transform:
            contour_kwargs["transform"] = transform
        ax.contour(lon, lat, values, **contour_kwargs)

    if projection:
        ax.set_extent([x_min, x_max, region.lat_min, region.lat_max], crs=transform)
        ax.coastlines(linewidth=1.1, color="0.18")
        if cfeature is not None:
            ax.add_feature(cfeature.BORDERS, linewidth=1.1, edgecolor="0.18")
        _add_brazil_states(ax, region, transform)
    else:
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(region.lat_min, region.lat_max)

    x_ticks = _longitude_ticks(region, x_min, x_max)
    y_ticks = _ticks(region.lat_min, region.lat_max, region.y_tick)
    if projection and transform:
        ax.set_xticks(x_ticks, crs=transform)
        ax.set_yticks(y_ticks, crs=transform)
    else:
        ax.set_xticks(x_ticks)
        ax.set_yticks(y_ticks)
    ax.xaxis.set_major_formatter(FuncFormatter(_longitude_formatter(region)))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_latitude))
    ax.grid(True, linewidth=0.4, color="0.62", alpha=0.6)
    ax.tick_params(labelsize=10)

    if colorbar_orientation == "horizontal":
        bottom = 0.22 if style.tercile_colorbar_labels else 0.18
        pad = 0.16 if style.tercile_colorbar_labels else 0.12
        fraction = 0.052 if style.tercile_colorbar_labels else 0.045
        fig.subplots_adjust(left=0.07, right=0.96, bottom=bottom, top=0.91)
        colorbar_kwargs = {
            "orientation": "horizontal",
            "fraction": fraction,
            "pad": pad,
            "aspect": 42,
        }
    elif style.tercile_colorbar_labels:
        fig.subplots_adjust(left=0.07, right=0.88, bottom=0.08, top=0.91)
        colorbar_kwargs = {
            "orientation": "vertical",
            "cax": _add_vertical_tercile_colorbar_axis(fig, ax),
        }
    else:
        fig.subplots_adjust(left=0.07, right=0.88, bottom=0.08, top=0.91)
        colorbar_kwargs = {
            "orientation": "vertical",
            "fraction": 0.035,
            "pad": 0.025,
        }

    colorbar = fig.colorbar(
        mesh,
        ax=ax,
        **colorbar_kwargs,
        ticks=style.levels,
        extend=style.colorbar_extend,
        boundaries=bounds,
        spacing="uniform",
    )
    tick_size = 10 if style.tercile_colorbar_labels else 9
    colorbar.ax.tick_params(labelsize=tick_size)
    colorbar.set_ticklabels(
        [_format_compact_number(value) for value in style.levels]
    )
    if style.tercile_colorbar_labels:
        _add_tercile_colorbar_labels(fig, ax, colorbar, colorbar_orientation)

    _draw_titles_above_map(fig, ax, title_lines)

    fig.savefig(output_file, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    logger.info("Figura gerada: %s", output_file)
    return True


def _plot_extent(region: Region) -> tuple[float, float]:
    if _covers_full_longitude(region):
        return 0.0, 360.0
    if _use_minus_180_to_180(region):
        return region.lon_min, region.lon_max
    return _region_lon_bounds(region)


def _central_longitude(region: Region) -> float:
    if _use_minus_180_to_180(region):
        return 0.0

    lon_min, lon_max = _region_lon_bounds(region)
    if _covers_full_longitude(region) or lon_min > 180 or lon_max > 180:
        return 180.0
    return 0.0


def _colorbar_orientation(region: Region) -> str:
    if region.name in HORIZONTAL_COLORBAR_REGIONS:
        return "horizontal"
    return "vertical"


def _format_compact_number(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return str(int(round(value)))

    return f"{value:.2f}".rstrip("0").rstrip(".")


def _ticks(start: float, end: float, interval: float) -> list[float]:
    first = math.ceil(start / interval) * interval
    values = []
    value = first
    while value <= end:
        values.append(value)
        value += interval
    return values


def _longitude_ticks(region: Region, x_min: float, x_max: float) -> list[float]:
    if not _covers_full_longitude(region):
        return _ticks(x_min, x_max, region.x_tick)

    ticks = _ticks(x_min, x_max, region.x_tick)
    if ticks and math.isclose(ticks[-1], x_max):
        ticks[-1] = np.nextafter(x_max, x_min)
    return ticks


def _longitude_formatter(region: Region):
    def formatter(value: float, position: int | None = None) -> str:
        return _format_full_longitude(value, position) if _covers_full_longitude(region) else _format_longitude(value, position)

    return formatter


def _colorbar_colors(
    style: MapStyle,
    colors: list[tuple[float, float, float]],
) -> tuple[
    list[tuple[float, float, float]],
    tuple[float, float, float] | None,
    tuple[float, float, float] | None,
]:
    regular_count = max(len(style.levels) - 1, 1)
    under_color = colors[0] if style.colorbar_extend in {"min", "both"} else None
    over_color = colors[-1] if style.colorbar_extend in {"max", "both"} else None

    start = 1 if under_color is not None and len(colors) > regular_count else 0
    end = len(colors) - 1 if over_color is not None and len(colors) - start > regular_count else len(colors)
    regular_colors = colors[start:end]

    if len(regular_colors) < regular_count:
        regular_colors = [*regular_colors, *([regular_colors[-1]] * (regular_count - len(regular_colors)))]
    elif len(regular_colors) > regular_count:
        regular_colors = regular_colors[:regular_count]

    return regular_colors, under_color, over_color


def _interpolate_for_display(
    da: xr.DataArray,
    region: Region,
    x_min: float,
    x_max: float,
) -> xr.DataArray:
    lon_size = da.sizes.get("lon", 0)
    lat_size = da.sizes.get("lat", 0)
    if lon_size < 2 or lat_size < 2:
        return da

    target_lon_size = min(max(lon_size * 4, 360), 1200)
    target_lat_size = min(max(lat_size * 4, 180), 600)
    new_lon = np.linspace(x_min, x_max, target_lon_size)
    new_lat = np.linspace(region.lat_min, region.lat_max, target_lat_size)

    try:
        return da.interp(
            lon=new_lon,
            lat=new_lat,
            kwargs={"fill_value": "extrapolate"},
        )
    except (ImportError, ValueError):
        linear = da.interp(lon=new_lon, lat=new_lat)
        nearest = da.interp(lon=new_lon, lat=new_lat, method="nearest")
        return linear.combine_first(nearest)


def _format_longitude(value: float, _position: int | None = None) -> str:
    lon = ((float(value) + 180.0) % 360.0) - 180.0
    if math.isclose(abs(lon), 180.0, abs_tol=1e-6):
        return f"180\N{DEGREE SIGN}"
    if math.isclose(lon, 0.0, abs_tol=1e-6):
        return f"0\N{DEGREE SIGN}"
    suffix = "E" if lon > 0 else "W"
    return f"{_format_degree_value(abs(lon))}\N{DEGREE SIGN}{suffix}"


def _format_full_longitude(value: float, _position: int | None = None) -> str:
    lon = float(value) % 360.0
    if math.isclose(lon, 360.0, abs_tol=1e-6) or lon > 360.0 - 1e-6:
        lon = 360.0

    if math.isclose(lon, 0.0, abs_tol=1e-6):
        return f"0\N{DEGREE SIGN}"
    if math.isclose(lon, 180.0, abs_tol=1e-6):
        return f"180\N{DEGREE SIGN}"
    if math.isclose(lon, 360.0, abs_tol=1e-6):
        return f"180\N{DEGREE SIGN}"
    if lon < 180.0:
        return f"{_format_degree_value(lon)}\N{DEGREE SIGN}E"
    return f"{_format_degree_value(360.0 - lon)}\N{DEGREE SIGN}W"


def _format_latitude(value: float, _position: int | None = None) -> str:
    lat = float(value)
    if math.isclose(lat, 0.0):
        return "EQ"
    suffix = "N" if lat > 0 else "S"
    return f"{_format_degree_value(abs(lat))}\N{DEGREE SIGN}{suffix}"


def _format_degree_value(value: float) -> str:
    if math.isclose(value, round(value)):
        return str(int(round(value)))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _add_brazil_states(ax, region: Region, transform) -> None:
    if region.name not in {"am", "as"} or transform is None or not BRAZIL_UF_SHAPE.exists():
        return

    try:
        import cartopy.io.shapereader as shpreader
    except ModuleNotFoundError:
        return

    try:
        geometries = shpreader.Reader(str(BRAZIL_UF_SHAPE)).geometries()
        ax.add_geometries(
            geometries,
            crs=transform,
            facecolor="none",
            edgecolor="0.18",
            linewidth=0.8,
            zorder=5,
        )
    except Exception as exc:
        logger.warning("Nao foi possivel desenhar UFs do Brasil: %s", exc)


def _add_vertical_tercile_colorbar_axis(fig, ax):
    bbox = ax.get_position()
    block_shift = 0.018
    cbar_width = 0.020
    cbar_left = min(0.968, bbox.x1 + 0.065 + block_shift)
    return fig.add_axes([cbar_left, bbox.y0, cbar_width, bbox.height])


def _add_tercile_colorbar_labels(fig, ax, colorbar, orientation: str) -> None:
    label_fontsize = 13

    if orientation == "horizontal":
        colorbar.ax.text(
            0.5,
            1.78,
            "White: equal probability for all categories",
            transform=colorbar.ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=label_fontsize,
        )
        colorbar.ax.text(
            0.25,
            1.05,
            "Lower Tercile",
            transform=colorbar.ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=label_fontsize,
        )
        colorbar.ax.text(
            0.75,
            1.05,
            "Upper Tercile",
            transform=colorbar.ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=label_fontsize,
        )
        return

    map_bbox = ax.get_position()
    cbar_bbox = colorbar.ax.get_position()
    block_shift = 0.018
    white_x = map_bbox.x1 + 0.014 + block_shift
    tercile_x = white_x + 0.029

    fig.text(
        white_x,
        cbar_bbox.y0 + cbar_bbox.height / 2.0,
        "White: equal probability for all categories",
        ha="center",
        va="center",
        fontsize=label_fontsize,
        rotation=90,
    )
    fig.text(
        tercile_x,
        cbar_bbox.y0 + cbar_bbox.height * 0.84,
        "Upper Tercile",
        ha="center",
        va="center",
        fontsize=label_fontsize,
        rotation=90,
    )
    fig.text(
        tercile_x,
        cbar_bbox.y0 + cbar_bbox.height * 0.16,
        "Lower Tercile",
        ha="center",
        va="center",
        fontsize=label_fontsize,
        rotation=90,
    )


def _draw_titles_above_map(fig, ax, title_lines: tuple[str, str, str]) -> None:
    bbox = ax.get_position()
    x_center = bbox.x0 + bbox.width / 2.0
    y_top = bbox.y1 + 0.012
    line_spacing = 0.028

    for index, line in enumerate(title_lines):
        fig.text(
            x_center,
            y_top + (2 - index) * line_spacing,
            line,
            ha="center",
            va="bottom",
            fontsize=13,
        )
