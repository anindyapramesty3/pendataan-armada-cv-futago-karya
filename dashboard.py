import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = "PENDATAAN ARMADA - CLEAN.xlsx"

COLOR_BLUE = "#2a78d6"
COLOR_GOOD = "#0ca30c"
COLOR_WARNING = "#fab219"
COLOR_CRITICAL = "#d03b3b"
GRID_COLOR = "#e1e0d9"
MUTED = "#898781"

st.set_page_config(page_title="KPI Armada - CV. Futago Karya", layout="wide")


@st.cache_data
def load_data():
    xls = pd.ExcelFile(DATA_PATH)
    return {
        "dim_armada": pd.read_excel(xls, "dim_armada"),
        "kpi_summary": pd.read_excel(xls, "KPI_SUMMARY"),
        "kpi_compliance": pd.read_excel(xls, "kpi_compliance"),
        "kpi_maintenance": pd.read_excel(xls, "kpi_maintenance"),
        "kpi_utilisasi": pd.read_excel(xls, "kpi_utilisasi"),
        "kpi_inventaris": pd.read_excel(xls, "kpi_inventaris"),
        "dim_sparepart": pd.read_excel(xls, "dim_sparepart"),
        "fact_jadwal_driver": pd.read_excel(xls, "fact_jadwal_driver"),
    }


def status_color(status):
    return {"MATI": COLOR_CRITICAL, "URGENT": COLOR_WARNING, "AKTIF": COLOR_GOOD}.get(status, MUTED)


def skor_color(v):
    if v < 50:
        return COLOR_CRITICAL
    if v < 75:
        return COLOR_WARNING
    return COLOR_GOOD


def style_fig(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#0b0b0b"), x=0),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color="#52514e"),
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False)
    return fig


def confidence_note(level, text):
    st.caption(f"**Confidence: {level}** -- {text}")


data = load_data()
dim_armada = data["dim_armada"]

st.sidebar.header("Filter")
all_armada = sorted(dim_armada["nama_armada"].dropna().unique())
selected = st.sidebar.multiselect("Pilih armada", all_armada, default=all_armada)
if not selected:
    selected = all_armada

st.title("Dashboard KPI Armada -- CV. Futago Karya")
st.caption(
    "Sumber: `PENDATAAN ARMADA - CLEAN.xlsx` (hasil cleaning + analisa KPI). "
    "File sumber asli tidak diubah. Data ini snapshot per 2 Juli 2026."
)

kpi_summary = data["kpi_summary"][data["kpi_summary"]["nama_armada"].isin(selected)]
kpi_compliance = data["kpi_compliance"][data["kpi_compliance"]["nama_armada"].isin(selected)]
kpi_maintenance = data["kpi_maintenance"][data["kpi_maintenance"]["nama_armada"].isin(selected)]
kpi_utilisasi = data["kpi_utilisasi"][data["kpi_utilisasi"]["nama_armada"].isin(selected)]
kpi_inventaris = data["kpi_inventaris"][data["kpi_inventaris"]["nama_armada"].isin(selected)]

# ---- headline metrics ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total armada terpilih", len(kpi_summary))
c2.metric("Skor kesehatan < 50 (butuh perhatian)", int((kpi_summary["skor_kesehatan"] < 50).sum()))
c3.metric("Keluhan belum selesai (backlog)", int(kpi_summary["jumlah_belum_selesai"].sum()))
c4.metric("Dokumen legal MATI", int((kpi_compliance["status_pajak_terdekat"] == "MATI").sum()))

tab_ringkasan, tab_legal, tab_maintenance, tab_utilisasi, tab_inventaris = st.tabs(
    ["Ringkasan (Point 3)", "Kepatuhan Legal", "Maintenance", "Utilisasi", "Inventaris"]
)

# ================= TAB RINGKASAN (point 3) =================
with tab_ringkasan:
    st.subheader("Skor Kesehatan Armada")
    plot_df = kpi_summary.sort_values("skor_kesehatan", ascending=True)
    colors = plot_df["skor_kesehatan"].apply(skor_color)
    fig = go.Figure(go.Bar(
        x=plot_df["skor_kesehatan"], y=plot_df["nama_armada"], orientation="h",
        marker_color=colors, text=plot_df["skor_kesehatan"], textposition="outside",
    ))
    fig.update_xaxes(range=[0, 110])
    style_fig(fig, "Skor Kesehatan (0-100) -- makin rendah makin butuh perhatian")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Tabel Ringkasan KPI per Armada")
    st.dataframe(
        kpi_summary.style.background_gradient(
            subset=["skor_kesehatan"], cmap="RdYlGn", vmin=0, vmax=100
        ),
        width="stretch",
        hide_index=True,
    )
    confidence_note(
        "Sedang",
        "Gabungan dari semua area KPI di bawah -- confidence-nya mengikuti komponen dengan confidence terendah "
        "(biaya sparepart & utilisasi masih dari sample kecil / cakupan waktu terbatas).",
    )

# ================= TAB KEPATUHAN LEGAL (point 2) =================
with tab_legal:
    st.subheader("Status Kepatuhan Pajak / KIR")
    plot_df = kpi_compliance.copy()
    max_val = plot_df["hari_menuju_jatuh_tempo_terdekat"].max()
    stub = max_val * 0.05 if pd.notna(max_val) and max_val > 0 else 10
    plot_df["hari_plot"] = plot_df["hari_menuju_jatuh_tempo_terdekat"].fillna(stub)
    plot_df = plot_df.sort_values("hari_plot")
    colors = plot_df["status_pajak_terdekat"].apply(status_color)
    labels = plot_df.apply(
        lambda r: r["status_pajak_terdekat"] if pd.isna(r["hari_menuju_jatuh_tempo_terdekat"])
        else f'{int(r["hari_menuju_jatuh_tempo_terdekat"])} hari', axis=1
    )
    fig = go.Figure(go.Bar(
        x=plot_df["hari_plot"], y=plot_df["nama_armada"], orientation="h",
        marker_color=colors, text=labels, textposition="outside",
    ))
    style_fig(fig, "Hari menuju jatuh tempo terdekat (merah = MATI, kuning = <=30 hari)")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(kpi_compliance, width="stretch", hide_index=True)
    confidence_note("Tinggi", "Sumbernya 1 sheet resmi monitoring pajak/KIR, terstruktur dan lengkap.")

# ================= TAB MAINTENANCE (point 2) =================
with tab_maintenance:
    st.subheader("Estimasi Biaya Perbaikan Reaktif per Armada")
    plot_df = kpi_maintenance[kpi_maintenance["jumlah_keluhan"] > 0].sort_values("total_estimasi_biaya")
    fig = go.Figure(go.Bar(
        x=plot_df["total_estimasi_biaya"], y=plot_df["nama_armada"], orientation="h",
        marker_color=COLOR_BLUE, text=plot_df["total_estimasi_biaya"].map(lambda v: f"Rp{v:,.0f}"),
        textposition="outside",
    ))
    style_fig(fig, "Total estimasi biaya perbaikan (Rp)")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Status Penyelesaian Keluhan")
    plot_df2 = kpi_maintenance[kpi_maintenance["jumlah_keluhan"] > 0].sort_values("jumlah_keluhan")
    fig2 = go.Figure()
    fig2.add_bar(x=plot_df2["jumlah_selesai"], y=plot_df2["nama_armada"], orientation="h",
                 name="Selesai", marker_color=COLOR_GOOD)
    fig2.add_bar(x=plot_df2["jumlah_belum_selesai"], y=plot_df2["nama_armada"], orientation="h",
                 name="Belum Selesai", marker_color=COLOR_CRITICAL)
    fig2.update_layout(barmode="stack")
    style_fig(fig2, "Jumlah keluhan: selesai vs belum selesai")
    fig2.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig2, width="stretch")
    st.dataframe(kpi_maintenance, width="stretch", hide_index=True)
    confidence_note(
        "Sedang",
        "Biaya masih berupa \"estimasi\" (bukan nilai final tertagih); sebagian baris keluhan tidak punya tanggal.",
    )

# ================= TAB UTILISASI (point 2) =================
with tab_utilisasi:
    st.warning(
        "**Peringatan cakupan data:** sheet jadwal driver sumbernya hanya berisi Januari, Februari, Mei, "
        "dan Juni 2026 -- Maret & April tidak tercatat sama sekali. Angka di bawah ini dari 4 bulan yang "
        "tersedia, bukan representasi periode penuh."
    )
    st.subheader("Jumlah Penugasan per Armada")
    plot_df = kpi_utilisasi.sort_values("jumlah_penugasan").copy()
    colors = plot_df["jumlah_penugasan"].apply(lambda v: COLOR_CRITICAL if v == 0 else COLOR_BLUE)
    max_val = plot_df["jumlah_penugasan"].max()
    stub = max_val * 0.03 if pd.notna(max_val) and max_val > 0 else 1
    plot_df["plot_val"] = plot_df["jumlah_penugasan"].apply(lambda v: stub if v == 0 else v)
    fig = go.Figure(go.Bar(
        x=plot_df["plot_val"], y=plot_df["nama_armada"], orientation="h",
        marker_color=colors, text=plot_df["jumlah_penugasan"], textposition="outside",
    ))
    style_fig(fig, "Jumlah penugasan tercatat (Jan, Feb, Mei, Jun 2026)")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Top 10 Driver Berdasarkan Jumlah Penugasan")
    driver_workload = (
        data["fact_jadwal_driver"]["driver"].dropna().astype(str).str.strip().str.title()
        .value_counts().head(10).reset_index()
    )
    driver_workload.columns = ["driver", "jumlah_penugasan"]
    fig3 = go.Figure(go.Bar(
        x=driver_workload["jumlah_penugasan"], y=driver_workload["driver"], orientation="h",
        marker_color=COLOR_BLUE,
    ))
    style_fig(fig3, "Top 10 driver")
    fig3.update_yaxes(autorange="reversed")
    st.plotly_chart(fig3, width="stretch")
    st.dataframe(kpi_utilisasi, width="stretch", hide_index=True)
    confidence_note("Sedang-Rendah", "Ada celah 2 bulan (Maret-April) yang datanya hilang total dari sumber.")

# ================= TAB INVENTARIS (point 2) =================
with tab_inventaris:
    dim_sparepart = data["dim_sparepart"]
    st.subheader("Stock Sparepart Kritis")
    kritis = dim_sparepart[dim_sparepart["flag_stock_kritis"]]
    st.dataframe(kritis[["nama", "jumlah_stock", "satuan", "nilai_stock"]], width="stretch", hide_index=True)
    st.metric("Total nilai stock sparepart saat ini", f"Rp{dim_sparepart['nilai_stock'].sum():,.0f}")

    st.subheader("Biaya Sparepart per Armada")
    plot_df = kpi_inventaris.sort_values("total_biaya_sparepart")
    fig = go.Figure(go.Bar(
        x=plot_df["total_biaya_sparepart"], y=plot_df["nama_armada"], orientation="h",
        marker_color=COLOR_BLUE, text=plot_df["total_biaya_sparepart"].map(lambda v: f"Rp{v:,.0f}"),
        textposition="outside",
    ))
    style_fig(fig, "Total biaya sparepart tertaut ke armada (Rp)")
    st.plotly_chart(fig, width="stretch")
    confidence_note(
        "Rendah",
        "Hanya sebagian kecil transaksi keluar sparepart yang tertaut ke armada tertentu -- angka ini indikatif, bukan total biaya sebenarnya.",
    )
