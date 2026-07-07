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


DEFAULT_VERIFICATION_ROOT = PATH_FIG
KNOWN_CALIBRATIONS = {"nocalib", "regr", "cox"}
KNOWN_REGIONS = {"br", "ne", "matopiba", "se", "south", "amazon"}
KNOWN_PRODUCTS = {
    "corskill",
    "mssskill",
    "msssfase",
    "msssamplitude",
    "bias",
    "arocmed",
    "aroctinf",
    "aroctsup",
}


@dataclass(frozen=True)
class VerificationFigure:
    path: Path
    relative_path: str
    base: str
    version: str
    calibration: str
    model: str
    variable: str
    product: str
    period: str
    month: str
    region: str


def main() -> None:
    st.set_page_config(page_title="Seasonal Verification Maps", layout="wide")
    st.title("Seasonal Verification Maps")

    root = sidebar_root()
    figures = load_verification_figures(root)

    if not root.exists():
        st.warning(f"Pasta nao encontrada: {root}")
        return
    if not figures:
        st.warning(f"Nenhuma figura PNG de verificacao encontrada em: {root}")
        return

    filtered = sidebar_filters(figures)
    render_gallery(filtered)


def sidebar_root() -> Path:
    st.sidebar.header("Fonte")
    root_text = st.sidebar.text_input(
        "Pasta das figuras",
        value=str(DEFAULT_VERIFICATION_ROOT),
    )
    root = Path(root_text).expanduser()

    if st.sidebar.button("Atualizar lista"):
        load_verification_figures.clear()

    return root


@st.cache_data(show_spinner="Lendo mapas de verificacao...")
def load_verification_figures(root: Path) -> list[VerificationFigure]:
    if not root.exists():
        return []

    figures: list[VerificationFigure] = []
    for path in sorted(iter_verification_pngs(root), key=lambda item: str(item).lower()):
        parsed = parse_verification_figure(path, root)
        if parsed is not None:
            figures.append(parsed)
    return figures


def iter_verification_pngs(root: Path):
    if root.name == "verification":
        yield from root.rglob("*.png")
        return

    verification_dirs = [
        path
        for path in root.glob("*/*/verification")
        if path.is_dir()
    ]
    if verification_dirs:
        for verification_dir in verification_dirs:
            yield from verification_dir.rglob("*.png")
        return

    for path in root.rglob("*.png"):
        if "verification" in path.parts:
            yield path


def parse_verification_figure(path: Path, root: Path) -> VerificationFigure | None:
    parts = path.parts
    if "verification" not in parts:
        return None

    verification_index = parts.index("verification")
    if verification_index < 2 or len(parts) <= verification_index + 2:
        return None

    base = parts[verification_index - 2]
    version = parts[verification_index - 1]
    calibration = parts[verification_index + 1]
    model = parts[verification_index + 2]

    variable, product, period, month, region = parse_verification_name(
        path.stem.split("_"),
        calibration,
    )

    return VerificationFigure(
        path=path,
        relative_path=str(path.relative_to(root)),
        base=base,
        version=version,
        calibration=calibration,
        model=model,
        variable=variable,
        product=product,
        period=period,
        month=month,
        region=region,
    )


def parse_verification_name(
    parts: list[str],
    calibration: str,
) -> tuple[str, str, str, str, str]:
    variable = next((part for part in parts if part in {"prec", "t2mt"}), "")
    period = next((part for part in parts if re.fullmatch(r"(mnth|seas)\d{2}", part)), "")
    month = next((part for part in parts if re.fullmatch(r"[A-Z]{3}", part)), "")

    region = ""
    if parts:
        region = parts[-1]
        if region not in KNOWN_REGIONS and not re.fullmatch(r"[a-z]+", region):
            region = ""

    product = next((part for part in parts if part in KNOWN_PRODUCTS), "")
    if not product and variable and period:
        product = product_between_calibration_and_variable(
            parts,
            calibration,
            variable,
        )

    return variable, product, period, month, region


def product_between_calibration_and_variable(
    parts: list[str],
    calibration: str,
    variable: str,
) -> str:
    try:
        variable_index = parts.index(variable)
    except ValueError:
        return ""

    calibration_indexes = [
        index
        for index, part in enumerate(parts[:variable_index])
        if part in KNOWN_CALIBRATIONS or part == f"calibrated_{calibration}"
    ]
    if calibration_indexes:
        start = calibration_indexes[-1] + 1
    else:
        start = max(0, variable_index - 1)

    product_parts = parts[start:variable_index]
    return "_".join(product_parts)


def sidebar_filters(figures: list[VerificationFigure]) -> list[VerificationFigure]:
    st.sidebar.header("Filtros")

    fields = (
        ("base", "Base"),
        ("version", "Versao"),
        ("calibration", "Calibracao"),
        ("model", "Modelo"),
        ("variable", "Variavel"),
        ("product", "Metrica"),
        ("period", "Periodo"),
        ("month", "Mes"),
        ("region", "Regiao"),
    )

    filtered = figures
    for attr, label in fields:
        options = unique_values(filtered, attr)
        choice = st.sidebar.selectbox(label, ["Todos", *options], key=f"verification_{attr}")
        if choice != "Todos":
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


def unique_values(figures: list[VerificationFigure], attr: str) -> list[str]:
    return sorted({getattr(figure, attr) for figure in figures if getattr(figure, attr)})


def render_gallery(figures: list[VerificationFigure]) -> None:
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
