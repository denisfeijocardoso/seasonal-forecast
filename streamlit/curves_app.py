from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from src.config.paths import PATH_FIG
except Exception:
    PATH_FIG = Path("/dados/mmclima/multimodelo/seasonal/figures")


DEFAULT_CURVES_ROOT = PATH_FIG
POINTS_FILE = REPO_ROOT / "src" / "curves" / "coords_points_curves.txt"


@dataclass(frozen=True)
class CurveFigure:
    path: Path
    relative_path: str
    base: str
    version: str
    calibration: str
    model: str
    year: str
    issued: str
    variable: str
    curve_type: str
    period: str
    point_id: str
    lat: float | None
    lon: float | None


def main() -> None:
    st.set_page_config(page_title="Seasonal Curves", layout="wide")
    st.title("Seasonal Curves")

    root = sidebar_root()
    points = load_points(POINTS_FILE)
    figures = load_curve_figures(root, points)

    if not root.exists():
        st.warning(f"Pasta nao encontrada: {root}")
        return
    if not figures:
        st.warning(f"Nenhuma figura PNG de curva encontrada em: {root}")
        return

    filtered = sidebar_filters(figures)
    filtered = point_selector(filtered, points)
    render_gallery(filtered)


def sidebar_root() -> Path:
    st.sidebar.header("Fonte")
    root_text = st.sidebar.text_input(
        "Pasta das figuras",
        value=str(DEFAULT_CURVES_ROOT),
    )
    root = Path(root_text).expanduser()

    if st.sidebar.button("Atualizar lista"):
        load_curve_figures.clear()
        load_points.clear()

    return root


@st.cache_data(show_spinner="Lendo pontos das curvas...")
def load_points(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["point_id", "lat", "lon", "label"])

    points = pd.read_csv(path, sep=r"\s+")
    points = points.rename(columns={"ID": "point_id"})
    points["point_id"] = points["point_id"].astype(str)
    points["label"] = points.apply(
        lambda row: f"{row.point_id} | lat {row.lat:.2f} lon {row.lon:.2f}",
        axis=1,
    )
    return points[["point_id", "lat", "lon", "label"]]


@st.cache_data(show_spinner="Lendo curvas...")
def load_curve_figures(root: Path, points: pd.DataFrame) -> list[CurveFigure]:
    if not root.exists():
        return []

    point_lookup = {
        row.point_id: (float(row.lat), float(row.lon))
        for row in points.itertuples(index=False)
    }

    figures: list[CurveFigure] = []
    for path in sorted(iter_curve_pngs(root), key=lambda item: str(item).lower()):
        parsed = parse_curve_figure(path, root, point_lookup)
        if parsed is not None:
            figures.append(parsed)
    return figures


def iter_curve_pngs(root: Path):
    if root.name == "curves":
        yield from root.rglob("*.png")
        return

    curve_dirs = [
        path
        for path in root.glob("*/*/curves")
        if path.is_dir()
    ]
    if curve_dirs:
        for curve_dir in curve_dirs:
            yield from curve_dir.rglob("*.png")
        return

    for path in root.rglob("*.png"):
        if "curves" in path.parts:
            yield path


def parse_curve_figure(
    path: Path,
    root: Path,
    point_lookup: dict[str, tuple[float, float]],
) -> CurveFigure | None:
    parts = path.parts
    if "curves" not in parts:
        return None

    curves_index = parts.index("curves")
    if curves_index < 2 or len(parts) <= curves_index + 5:
        return None

    base = parts[curves_index - 2]
    version = parts[curves_index - 1]
    calibration = parts[curves_index + 1]
    model = parts[curves_index + 2]
    year = parts[curves_index + 3]
    issued = parts[curves_index + 4]

    variable, curve_type, period, point_id = parse_curve_name(path.stem)
    lat, lon = point_lookup.get(point_id, (None, None))

    return CurveFigure(
        path=path,
        relative_path=str(path.relative_to(root)),
        base=base,
        version=version,
        calibration=calibration,
        model=model,
        year=year,
        issued=issued,
        variable=variable,
        curve_type=curve_type,
        period=period,
        point_id=point_id,
        lat=lat,
        lon=lon,
    )


def parse_curve_name(stem: str) -> tuple[str, str, str, str]:
    parts = stem.split("_")
    period = next((part for part in parts if re.fullmatch(r"(mnth|seas)\d{2}", part)), "")
    point_id = parts[-1] if parts and parts[-1].isdigit() else ""
    variable = next((part for part in parts if part in {"prec", "t2mt"}), "")

    curve_type = ""
    if variable and period:
        var_index = parts.index(variable)
        period_index = parts.index(period)
        if period_index > var_index + 1:
            curve_type = "_".join(parts[var_index + 1 : period_index])
        elif var_index > 1:
            curve_type = "_".join(parts[1:var_index])
    elif period:
        period_index = parts.index(period)
        if period_index > 1:
            curve_type = "_".join(parts[1:period_index])

    return variable, curve_type, period, point_id


def sidebar_filters(figures: list[CurveFigure]) -> list[CurveFigure]:
    st.sidebar.header("Filtros")

    fields = (
        ("base", "Base"),
        ("version", "Versao"),
        ("calibration", "Calibracao"),
        ("model", "Modelo"),
        ("year", "Ano"),
        ("issued", "Emissao"),
        ("variable", "Variavel"),
        ("curve_type", "Tipo de curva"),
        ("period", "Periodo"),
    )

    filtered = figures
    for attr, label in fields:
        options = unique_values(filtered, attr)
        choice = st.sidebar.selectbox(label, ["Todos", *options], key=f"curves_{attr}")
        if choice != "Todos":
            filtered = [figure for figure in filtered if getattr(figure, attr) == choice]

    search = st.sidebar.text_input("Buscar no nome/caminho").strip().lower()
    if search:
        filtered = [
            figure
            for figure in filtered
            if search in figure.relative_path.lower() or search in figure.path.name.lower()
        ]

    st.sidebar.caption(f"{len(filtered)} de {len(figures)} figuras antes do filtro de ponto")
    return filtered


def point_selector(figures: list[CurveFigure], points: pd.DataFrame) -> list[CurveFigure]:
    available_ids = sorted(
        {figure.point_id for figure in figures if figure.point_id},
        key=lambda value: int(value) if value.isdigit() else value,
    )
    if not available_ids:
        return figures

    selected_from_map = render_point_map(points, available_ids)
    if selected_from_map in available_ids:
        st.session_state["curves_selected_point_id"] = selected_from_map

    labels = {
        row.point_id: row.label
        for row in points[points["point_id"].isin(available_ids)].itertuples(index=False)
    }

    default_index = 0
    selected_state = st.session_state.get("curves_selected_point_id")
    if selected_state in available_ids:
        default_index = available_ids.index(selected_state)

    selected_id = st.selectbox(
        "Ponto",
        available_ids,
        index=default_index,
        key="curves_point_selectbox",
        format_func=lambda point_id: labels.get(point_id, point_id),
    )
    st.session_state["curves_selected_point_id"] = selected_id

    selected_figures = [figure for figure in figures if figure.point_id == selected_id]
    selected_point = points[points["point_id"] == selected_id]
    if not selected_point.empty:
        row = selected_point.iloc[0]
        st.caption(f"Ponto {selected_id}: lat {row.lat:.2f}, lon {row.lon:.2f}")

    return selected_figures


def render_point_map(points: pd.DataFrame, available_ids: list[str]) -> str | None:
    map_points = points[points["point_id"].isin(available_ids)].copy()
    if map_points.empty:
        return None

    with st.expander("Mapa de pontos", expanded=True):
        try:
            import pydeck as pdk
        except Exception:
            st.map(map_points.rename(columns={"lat": "latitude", "lon": "longitude"}))
            return None

        selected_id = st.session_state.get("curves_selected_point_id")
        map_points["selected"] = map_points["point_id"] == selected_id
        map_points["fill_color"] = map_points["selected"].map(
            {
                True: [220, 45, 45, 230],
                False: [30, 105, 190, 170],
            }
        )

        view_state = pdk.ViewState(
            latitude=float(map_points["lat"].mean()),
            longitude=float(map_points["lon"].mean()),
            zoom=1,
            pitch=0,
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_points,
            get_position="[lon, lat]",
            get_fill_color="fill_color",
            get_radius=45000,
            radius_min_pixels=3,
            radius_max_pixels=9,
            pickable=True,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "Ponto {point_id}\\nLat {lat}\\nLon {lon}"},
            map_style=None,
        )

        try:
            event = st.pydeck_chart(
                deck,
                use_container_width=True,
                height=430,
                key="curves_point_map",
                on_select="rerun",
                selection_mode="single-object",
            )
        except TypeError:
            st.pydeck_chart(deck, use_container_width=True)
            return None

        return selected_point_from_pydeck_event(event)

    return None


def selected_point_from_pydeck_event(event) -> str | None:
    selection = event.get("selection", {}) if isinstance(event, dict) else getattr(event, "selection", {})
    if not selection:
        return None

    objects = selection.get("objects", {}) if isinstance(selection, dict) else getattr(selection, "objects", {})
    if isinstance(objects, dict):
        for selected_objects in objects.values():
            if selected_objects:
                first = selected_objects[0]
                point_id = first.get("point_id") if isinstance(first, dict) else getattr(first, "point_id", None)
                if point_id is not None:
                    return str(point_id)

    indices = selection.get("indices", {}) if isinstance(selection, dict) else getattr(selection, "indices", {})
    if isinstance(indices, dict):
        for selected_indices in indices.values():
            if selected_indices:
                index = selected_indices[0]
                if isinstance(index, dict) and "point_id" in index:
                    return str(index["point_id"])

    return None


def unique_values(figures: list[CurveFigure], attr: str) -> list[str]:
    return sorted({getattr(figure, attr) for figure in figures if getattr(figure, attr)})


def render_gallery(figures: list[CurveFigure]) -> None:
    st.caption(f"{len(figures)} curva(s)")

    if not figures:
        st.info("Nenhuma curva combina com os filtros selecionados.")
        return

    view = st.radio("Visualizacao", ["Galeria", "Imagem unica"], horizontal=True)

    if view == "Imagem unica":
        selected = st.selectbox(
            "Curva",
            figures,
            format_func=lambda figure: figure.relative_path,
        )
        st.image(str(selected.path), caption=selected.relative_path, use_container_width=True)
        st.code(str(selected.path), language="text")
        return

    columns_count = st.slider("Colunas", min_value=1, max_value=4, value=2)
    columns = st.columns(columns_count)
    for index, figure in enumerate(figures):
        with columns[index % columns_count]:
            st.image(str(figure.path), caption=figure.relative_path, use_container_width=True)


if __name__ == "__main__":
    main()
