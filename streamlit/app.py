from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from src.config.paths import PATH_FIG
except Exception:
    PATH_FIG = Path("/dados/mmclima/multimodelo/seasonal/figures")


@dataclass(frozen=True)
class FigureInfo:
    path: Path
    relative_path: str
    base: str
    version: str
    product_type: str
    calibration: str
    model: str
    year: str
    issued: str
    variable: str
    product: str
    period: str
    region: str


def main() -> None:
    st.set_page_config(page_title="Seasonal Maps", layout="wide")
    st.title("Seasonal Maps")

    root = sidebar_root()
    figures = load_figures(root)

    if not root.exists():
        st.warning(f"Pasta nao encontrada: {root}")
        return
    if not figures:
        st.warning(f"Nenhuma figura PNG encontrada em: {root}")
        return

    filtered = sidebar_filters(figures)
    render_gallery(filtered)


def sidebar_root() -> Path:
    st.sidebar.header("Fonte")
    root_text = st.sidebar.text_input("Pasta das figuras", value=str(PATH_FIG))
    root = Path(root_text).expanduser()

    if st.sidebar.button("Atualizar lista"):
        load_figures.clear()

    return root


@st.cache_data(show_spinner="Lendo figuras...")
def load_figures(root: Path) -> list[FigureInfo]:
    if not root.exists():
        return []

    files = sorted(root.rglob("*.png"), key=lambda path: str(path).lower())
    return [parse_figure(path, root) for path in files]


def parse_figure(path: Path, root: Path) -> FigureInfo:
    rel_parts = path.relative_to(root).parts
    name_parts = path.stem.split("_")

    base = rel_parts[0] if len(rel_parts) > 0 else ""
    version = rel_parts[1] if len(rel_parts) > 1 else ""
    product_type = rel_parts[2] if len(rel_parts) > 2 else ""
    calibration = rel_parts[3] if len(rel_parts) > 3 else ""
    model = rel_parts[4] if len(rel_parts) > 4 else ""
    year = rel_parts[5] if len(rel_parts) > 5 else ""
    issued = rel_parts[6] if len(rel_parts) > 6 else ""

    variable, product, period, region = parse_name_fields(name_parts)

    return FigureInfo(
        path=path,
        relative_path=str(path.relative_to(root)),
        base=base,
        version=version,
        product_type=product_type,
        calibration=calibration,
        model=model,
        year=year,
        issued=issued,
        variable=variable,
        product=product,
        period=period,
        region=region,
    )


def parse_name_fields(parts: list[str]) -> tuple[str, str, str, str]:
    variable = next((part for part in parts if part in {"prec", "t2mt"}), "")
    period = next((part for part in parts if re.fullmatch(r"(mnth|seas)\d{2}", part)), "")
    region = parts[-1] if parts else ""

    product = ""
    if variable and period:
        var_index = parts.index(variable)
        period_index = parts.index(period)
        date_index = next(
            (
                index
                for index in range(var_index + 1, period_index)
                if re.fullmatch(r"\d{10}", parts[index])
            ),
            period_index,
        )
        if date_index > var_index + 1:
            product = "_".join(parts[var_index + 1 : date_index])

    return variable, product, period, region


def sidebar_filters(figures: list[FigureInfo]) -> list[FigureInfo]:
    st.sidebar.header("Filtros")

    fields = (
        ("base", "Base"),
        ("version", "Versao"),
        ("product_type", "Tipo"),
        ("calibration", "Calibracao"),
        ("model", "Modelo"),
        ("year", "Ano"),
        ("issued", "Emissao"),
        ("variable", "Variavel"),
        ("product", "Produto"),
        ("period", "Periodo"),
        ("region", "Regiao"),
    )

    selected: dict[str, str] = {}
    filtered = figures
    for attr, label in fields:
        options = unique_values(filtered, attr)
        choice = st.sidebar.selectbox(label, ["Todos", *options], key=attr)
        if choice != "Todos":
            selected[attr] = choice
            filtered = [figure for figure in filtered if getattr(figure, attr) == choice]

    search = st.sidebar.text_input("Buscar no nome/caminho").strip().lower()
    if search:
        filtered = [
            figure
            for figure in filtered
            if search in figure.relative_path.lower() or search in figure.path.name.lower()
        ]

    st.sidebar.caption(f"{len(filtered)} de {len(figures)} figuras")
    return filtered


def unique_values(figures: list[FigureInfo], attr: str) -> list[str]:
    return sorted({getattr(figure, attr) for figure in figures if getattr(figure, attr)})


def render_gallery(figures: list[FigureInfo]) -> None:
    st.caption(f"{len(figures)} figura(s)")

    if not figures:
        st.info("Nenhuma figura combina com os filtros selecionados.")
        return

    view = st.radio("Visualizacao", ["Galeria", "Imagem unica"], horizontal=True)

    if view == "Imagem unica":
        selected = st.selectbox(
            "Figura",
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
